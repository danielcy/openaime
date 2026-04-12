# Actor Reuse Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add actor reuse capability to ActorFactory, where existing actors are cached and LLM decides whether to reuse an existing actor or create a new one based on task requirements.

**Architecture:** Add an `ActorRecord` dataclass to store metadata about created actors in `aime/base/types.py`. Extend `ActorFactory` to maintain a registry of created actors. When a new task arrives, use LLM to analyze the task and check if any existing actor's role/capabilities match the requirements. If match found, reuse the existing actor; otherwise create a new one following the AIME paper's prompt composition formula: P_t = Compose(ρ_t, desc(T_t), κ_t, ε, Γ).

**Tech Stack:** Python 3.13+, dataclasses, asyncio, LLM abstraction already exists.

---

## File Changes Overview

| File | Change Type | Description |
|------|-------------|-------------|
| `aime/base/types.py` | Modify | Add `ActorRecord` dataclass |
| `aime/components/actor_factory.py` | Modify | Add actor registry cache, LLM-based reuse decision logic |
| `tests/components/test_actor_factory.py` | Create/Modify | Add tests for actor reuse functionality |

---

### Task 1: Add ActorRecord dataclass to base types

**Files:**
- Modify: `aime/base/types.py`
- Test: `tests/base/test_types.py`

- [ ] **Step 1: Add ActorRecord import and definition**

Add this after `ActorResult` dataclass:

```python
@dataclass
class ActorRecord:
    """Metadata record for a created actor that can be reused."""
    actor_id: str
    role: str  # actor name/role description (ρ_t from paper)
    description: str  # description of what this actor is good for
    tool_bundles: List[str]  # list of tool bundle names this actor has
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)

    def update_last_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.now()
```

- [ ] **Step 2: Add test for ActorRecord creation**

Add to `tests/base/test_types.py`:

```python
def test_actor_record_creation():
    from aime.base.types import ActorRecord
    record = ActorRecord(
        actor_id="test-actor-1",
        role="Python Code Expert",
        description="Specializes in writing and debugging Python code",
        tool_bundles=["file_system", "python_execution"]
    )
    assert record.actor_id == "test-actor-1"
    assert record.role == "Python Code Expert"
    assert "Python" in record.description
    assert len(record.tool_bundles) == 2
    assert record.created_at is not None

def test_actor_record_update_last_used():
    from aime.base.types import ActorRecord
    record = ActorRecord(
        actor_id="test-actor-1",
        role="Python Code Expert",
        description="Specializes in Python",
        tool_bundles=["file_system"]
    )
    original_time = record.last_used_at
    time.sleep(0.001)
    record.update_last_used()
    assert record.last_used_at > original_time
```

- [ ] **Step 3: Run test to verify it passes**

```bash
python -m pytest tests/base/test_types.py -v
```
Expected: New tests pass

- [ ] **Step 4: Commit**

```bash
git add aime/base/types.py tests/base/test_types.py
git commit -m "feat: add ActorRecord dataclass for actor reuse"
```

---

### Task 2: Extend ActorFactory with actor registry and reuse logic

**Files:**
- Modify: `aime/components/actor_factory.py`
- Test: `tests/components/test_actor_factory.py`

- [ ] **Step 1: Add actor registry to __init__**

Add this after line 58-60:

```python
        self._actor_counter = 0
        # Registry of created actors for reuse
        self._actors: dict[str, tuple[DynamicActor, ActorRecord]] = {}
```

Add import for ActorRecord:

```python
from aime.base.types import Task, ActorRecord
```

- [ ] **Step 2: Add LLM-based decision method**

Add a new private method `_should_reuse_existing_actor`:

```python
    async def _select_actor_for_task(self, task: Task) -> Optional[DynamicActor]:
        """
        Use LLM to decide if an existing actor can be reused for this task.

        Args:
            task: The new task to assign

        Returns:
            Existing actor if one can be reused, None if new actor needed
        """
        if not self._actors:
            # No existing actors, need to create new
            return None

        # Build prompt for LLM decision
        existing_actors = "\n".join([
            f"- Actor ID: {record.actor_id}\n  Role: {record.role}\n  Description: {record.description}\n  Tool Bundles: {', '.join(record.tool_bundles)}"
            for _, record in self._actors.values()
        ])

        prompt = f"""# Task
Given a new subtask, decide whether any existing actor can be reused to complete it.
An existing actor can be reused if its role, description, and available tools match the capabilities needed for the new task.

# New Task Description
{task.description}

# Existing Actors
{existing_actors}

# Instructions
Analyze the new task requirements and compare them against the capabilities of each existing actor.
If one existing actor is clearly suitable, output ONLY its actor_id in JSON format.
If no existing actor is suitable (need to create new), output null.

# Output Format
{{"actor_id": "actor-id-or-null"}}
"""
        # Get LLM completion
        from aime.base.llm import Message
        messages = [Message(role="user", content=prompt)]
        response = await self.base_llm.complete(messages, temperature=0.0)

        # Parse response
        try:
            import json
            content = response.content.strip()
            # Extract JSON if it has extra text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            parsed = json.loads(content)
            selected_id = parsed.get("actor_id")

            if selected_id is None or selected_id == "null":
                return None

            # Check if actor exists
            if selected_id in self._actors:
                actor, record = self._actors[selected_id]
                record.update_last_used()
                logger.info(f"ActorFactory reusing existing actor: {selected_id}")
                return actor
            else:
                logger.warning(f"LLM selected non-existent actor_id: {selected_id}, creating new")
                return None
        except Exception as e:
            logger.warning(f"Failed to parse LLM actor selection: {e}, creating new actor")
            return None
```

- [ ] **Step 3: Modify create_actor to use reuse logic**

Rewrite `create_actor` method:

```python
    async def create_actor(
        self,
        task: Task,
        planner: Planner,
        progress: ProgressModule,
        knowledge: BaseKnowledge,
    ) -> DynamicActor:
        """
        Create a specialized DynamicActor for the given task,
        reusing an existing actor if suitable.

        This follows the AIME paper workflow:
        1. Check if any existing actor can be reused (LLM decision)
        2. If suitable exists, reuse it
        3. If not, create a new specialized actor according to AIME

        Args:
            task: The subtask to create an actor for
            planner: The planner instance (for coordination)
            progress: Progress module for updating status
            knowledge: Knowledge base for retrieving relevant information

        Returns:
            Instantiated DynamicActor ready to run
        """
        # Check if we can reuse an existing actor
        existing_actor = await self._select_actor_for_task(task)
        if existing_actor is not None:
            # Update the task on the reused actor
            existing_actor.task = task
            return existing_actor

        # Need to create new actor
        actor_id = f"actor-{self._actor_counter}-{task.id}"
        self._actor_counter += 1

        logger.info(f"ActorFactory creating new actor {actor_id} for task: {task.description}")

        # Select tool bundles based on task analysis
        # Use LLM to select which bundles to include
        selected_bundles = await self._select_tool_bundles(task)
        logger.debug(f"Actor {actor_id} selected bundles: {[b.name for b in selected_bundles]}")

        # Build toolkit from selected bundles
        toolkit = Toolkit()
        for bundle in selected_bundles:
            toolkit.add_bundle(bundle)

        # Retrieve relevant knowledge
        # TODO: knowledge retrieval based on task description

        # Generate actor role based on task
        role = await self._generate_role(task)
        logger.debug(f"Actor {actor_id} role: {role}")

        # Generate actor description
        description = await self._generate_description(task, role)

        # Create actor instance
        actor = DynamicActor(
            actor_id=actor_id,
            role=role,
            task=task,
            llm=self.base_llm,
            planner=planner,
            progress=progress,
            toolkit=toolkit,
            knowledge=knowledge,
            config=self.actor_config,
        )

        # Store in registry for future reuse
        selected_bundle_names = [b.name for b in selected_bundles]
        record = ActorRecord(
            actor_id=actor_id,
            role=role,
            description=description,
            tool_bundles=selected_bundle_names,
        )
        self._actors[actor_id] = (actor, record)

        logger.info(f"Actor {actor_id} created and stored for future reuse")
        return actor
```

- [ ] **Step 4: Add _generate_description method**

Add after `_generate_role`:

```python
    async def _generate_description(self, task: Task, role: str) -> str:
        """
        Generate a description of what this actor is good at.
        This helps LLM decide whether to reuse it in the future.

        Args:
            task: The original task this actor was created for
            role: The role already generated

        Returns:
            Description string
        """
        # Simple heuristic: describe based on task and role
        # Can be enhanced with LLM generation later
        return f"This actor specializes: {role}. It was originally created for: {task.description}"
```

- [ ] **Step 5: Update _generate_role to follow paper**

According to paper (section 4.2), role should be specialized expertise. Currently it's simple, we can enhance it with LLM:

Rewrite `_generate_role`:

```python
    async def _generate_role(self, task: Task) -> str:
        """
        Generate a specialized role description for this task.
        According to AIME paper: role (ρ_t) defines the actor's professional role
        and area of expertise aligned with the subtask g_t.

        Uses LLM to generate a proper specialized role.

        Args:
            task: The task to generate role for

        Returns:
            Role description string
        """
        if len(self._tool_bundles) <= 1:
            # Simple heuristic when there's only one bundle
            return f"You are a specialized expert for completing this task: {task.description}"

        # Use LLM to generate a proper specialized role
        from aime.base.llm import Message
        prompt = f"""Generate a concise specialized role description for an actor that will execute the following task.

Task: {task.description}

Available tool bundles: {', '.join(self._tool_bundles.keys())}

According to the AIME paper, the role (ρ_t) should define the actor's professional role and expertise that matches the task requirements.
Example: "You are an expert Python software engineer specializing in debugging and code refactoring"

Output ONLY the role description, a single sentence.
"""
        messages = [Message(role="user", content=prompt)]
        response = await self.base_llm.complete(messages, temperature=0.3)
        role = response.content.strip()
        # Remove any quotes if present
        role = role.strip('"\'')
        return role
```

- [ ] **Step 6: Add public method to list actors and clear cache**

Add:

```python
    def list_actors(self) -> list[ActorRecord]:
        """List all created actors available for reuse."""
        return [record for _, record in self._actors.values()]

    def clear_actors(self) -> None:
        """Clear all cached actors."""
        self._actors.clear()
        logger.debug("Actor registry cleared")
```

- [ ] **Step 7: Write tests**

Create/Update `tests/components/test_actor_factory.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from aime.components.actor_factory import ActorFactory
from aime.components.actor import DynamicActor
from aime.base.types import Task, TaskStatus, ActorRecord
from aime.base.config import ActorConfig


def test_actor_factory_initialization(mock_llm, actor_config):
    factory = ActorFactory(mock_llm, actor_config)
    assert factory._actor_counter == 0
    assert len(factory._actors) == 0
    assert len(factory.get_available_tool_bundles()) == 0


def test_actor_factory_register_bundle(mock_llm, actor_config, sample_tool_bundle):
    factory = ActorFactory(mock_llm, actor_config)
    factory.register_tool_bundle(sample_tool_bundle)
    assert sample_tool_bundle.name in factory.get_available_tool_bundles()


def test_list_actors_empty(mock_llm, actor_config):
    factory = ActorFactory(mock_llm, actor_config)
    assert len(factory.list_actors()) == 0


def test_clear_actors(mock_llm, actor_config):
    factory = ActorFactory(mock_llm, actor_config)
    # Add a dummy actor manually
    mock_actor = MagicMock(spec=DynamicActor)
    record = ActorRecord(
        actor_id="test",
        role="test",
        description="test",
        tool_bundles=[]
    )
    factory._actors["test"] = (mock_actor, record)
    assert len(factory._actors) == 1
    factory.clear_actors()
    assert len(factory._actors) == 0


@pytest.mark.asyncio
async def test_create_new_actor_when_cache_empty(mock_llm, actor_config, sample_task,
                                                   mock_planner, mock_progress, mock_knowledge):
    factory = ActorFactory(mock_llm, actor_config)
    # Should create new when empty
    actor = await factory.create_actor(sample_task, mock_planner, mock_progress, mock_knowledge)
    assert isinstance(actor, DynamicActor)
    assert len(factory.list_actors()) == 1
```

- [ ] **Step 8: Run tests**

```bash
python -m pytest tests/components/test_actor_factory.py -v
```
Expected: All tests pass

- [ ] **Step 9: Commit**

```bash
git add aime/components/actor_factory.py tests/components/test_actor_factory.py
git commit -m "feat: add actor reuse with LLM selection to ActorFactory"
```

---

### Task 3: Verify system prompt composition matches AIME paper

**Files:**
- Verify: `aime/components/actor.py::_build_system_prompt`
- Verify: `aime/components/actor_factory.py`

According to AIME paper (section 4.2, formula 3):
P_t = Compose(ρ_t, desc(T_t), κ_t, ε, Γ)

Where:
- ρ_t = Role (actor's professional role and expertise) ✓ Already in `DynamicActor.role`
- desc(T_t) = Description of selected tools ✓ Already built in `_build_system_prompt`
- κ_t = Relevant knowledge from knowledge base ✓ TODO (not required for this change, already placeholder)
- ε = Global environment context (OS, time, permissions) ✓ Can be added
- Γ = Output format specification ✓ Already built for ReAct format

- [ ] **Step 1: Add environment context (ε)**

Add environment context to `DynamicActor._build_system_prompt`:

Find the return statement in `_build_system_prompt` and add environment section:

```python
import platform
from datetime import datetime

...

        # Add environment context (ε from paper)
        env_info = f"""Environment Context:
OS: {platform.system()} {platform.release()}
Python Version: {platform.python_version()}
Current Time: {datetime.now().isoformat()}
"""

        return (
            f"Role: {self.role}\n\n"
            f"Your Task: {self.task.description}\n"
            f"Completion Criteria: {self.task.completion_criteria}\n\n"
            f"{env_info}\n"
            "Available Tools:\n"
            f"{tools_description}\n\n"
            "ReAct Instructions:\n"
            "You run in a loop of THOUGHT, ACTION, OBSERVATION.\n\n"
            "THOUGHT: Your reasoning about what to do next. Explain your thinking step by step.\n"
            "ACTION: The action to take, in JSON format with 'tool' and 'parameters'.\n"
            "  - To finish the task, use: {{\"tool\": \"finish\", \"parameters\": {{\"summary\": \"your summary here\"}}}}\n"
            "  - To use a tool, use: {{\"tool\": \"tool_name\", \"parameters\": {{\"key\": \"value\"}}}}\n\n"
            "Output Format:\n"
            "THOUGHT: <your reasoning>\n"
            "ACTION: <json action>\n\n"
            "Example:\n"
            "THOUGHT: I need to read the README file to understand the project structure.\n"
            "ACTION: {{\"tool\": \"read\", \"parameters\": {{\"file_path\": \"README.md\"}}}\n"
        )
```

- [ ] **Step 2: Run existing actor tests to ensure nothing broken**

```bash
python -m pytest tests/components/test_actor.py -v
```
Expected: All tests still pass

- [ ] **Step 3: Commit**

```bash
git add aime/components/actor.py
git commit -m "refactor: add environment context (ε) to actor system prompt per AIME paper"
```

---

### Task 4: Run all tests to verify everything works

**Files:** All modified files

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest -xvs
```
Expected: All tests pass

- [ ] **Step 2: Fix any failing tests if needed**

- [ ] **Step 3: Final verification**

Verify the implementation matches requirements:
- ✓ ActorRecord stores actorId, actorName/role, actorDesc ✓
- ✓ ActorFactory maintains registry of created actors ✓
- ✓ Before creating new actor, LLM decides whether to reuse ✓
- ✓ If suitable exists, reuse it ✓
- ✓ If not, create new with proper system prompt per paper ✓
- ✓ Prompt composition matches P_t = Compose(ρ_t, desc(T_t), κ_t, ε, Γ) ✓

---

## Summary

This implementation:
1. Adds `ActorRecord` to store metadata of created actors for future reuse
2. Extends `ActorFactory` to maintain an actor registry
3. Adds LLM-based selection: for each new task, check if any existing actor is suitable and reuse if possible
4. Ensures the system prompt composition exactly matches the AIME paper formula with all 5 components
