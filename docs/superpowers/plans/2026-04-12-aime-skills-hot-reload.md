# AIME Skills System with Hot-Reload Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a Claude Code compatible Skills system for AIME framework with progressive disclosure and automatic hot-reload. Skills are modular capability extensions that package instructions, metadata, and resources, automatically loaded when matched to tasks.

**Architecture:** Follow the progressive disclosure principle: Level 1 (metadata only) loaded on check, Level 2 (full instructions) loaded only after matching, Level 3 (resources) loaded on-demand via tools. Hot-reload checks file modification timestamps on every match to pick up changes without restart. Skills are discovered from three search paths by default: `~/.openaime/skills`, `{workspace}/skills`, and user-provided extra paths. Integrated at the ActorFactory level - matched skills are injected into the Actor's system prompt before execution.

**Tech Stack:** Python 3.13, PyYAML for YAML frontmatter parsing, existing AIME components with minimal changes.

---

## Files to Create/Modify

| File | Responsibility |
|------|----------------|
| `aime/base/skill.py` | New: Core data structures (SkillMetadata, Skill, SkillRegistry) with hot-reload logic |
| `aime/aime.py` | Modify: Add skills parameters to OpenAime constructor, initialize SkillRegistry |
| `aime/components/actor_factory.py` | Modify: Add skill_registry integration, match skills on actor creation |
| `aime/components/actor.py` | Modify: Add matched_skills parameter, inject instructions into system prompt |
| `pyproject.toml` | Modify: Add PyYAML dependency |
| `tests/base/test_skill.py` | New: Unit tests for skill parsing, scanning, hot-reload |
| `tests/fixtures/skills/test-skill-1/SKILL.md` | New: Test fixture skill |
| `tests/fixtures/skills/test-skill-2/SKILL.md` | New: Second test fixture |
| `CLAUDE.md` | Modify: Update project documentation with skills feature |

---

### Task 1: Add PyYAML dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add PyYAML to dependencies**

```toml
dependencies = [
    "pydantic>=2.0",
    "openai>=1.0",
    "anthropic>=0.40",
    "rich>=13.0",
    "aiofiles>=23.0",
    "mcp>=1.0",
    "volcengine-python-sdk[ark]>=5.0.23",
    "pyyaml>=6.0",  # <- Add this line for YAML frontmatter parsing
]
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "feat(skills): add pyyaml dependency for yaml frontmatter parsing"
```

---

### Task 2: Create core skill module `aime/base/skill.py`

**Files:**
- Create: `aime/base/skill.py`
- Test: `tests/base/test_skill.py` (created later)

- [ ] **Step 1: Write imports and SkillMetadata dataclass**

```python
"""
Skill Registry - Progressive disclosure skills system with hot-reload.

Supports Claude Code compatible skill format:
- Each skill is a directory containing a SKILL.md file
- SKILL.md has YAML frontmatter with metadata
- Progressive disclosure: metadata only scanned by default, full content loaded on match
- Hot-reload: automatically detects file changes and reloads
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional, List
import yaml

from aime.base.llm import BaseLLM, Message


FRONTMATTER_PATTERN = re.compile(
    r'^---\s*\n(.*?)\n---\s*\n',
    re.DOTALL
)


@dataclass
class SkillMetadata:
    """Level 1: Metadata loaded at scan time (progressive disclosure)."""
    name: str
    description: str
    path: str  # Absolute path to skill directory
    skill_file_path: str  # Absolute path to SKILL.md
    mtime: float  # Last modified time of SKILL.md for hot-reload detection

    # Optional frontmatter fields
    argument_hint: Optional[str] = None
    disable_model_invocation: bool = False
    user_invocable: bool = False
    allowed_tools: Optional[List[str]] = None
    model: Optional[str] = None
    context: Optional[str] = None
    agent: Optional[str] = None
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Skill:
    """Full skill after loading (Level 2)."""
    metadata: SkillMetadata
    instructions: str  # Full SKILL.md content after frontmatter
    loaded_mtime: float  # mtime when loaded, for cache invalidation
```

- [ ] **Step 2: Write SkillRegistry class with hot-reload**

```python
class SkillRegistry:
    """Registry for managing skills with progressive disclosure and hot-reload.

    Discovery paths (default):
    1. ~/.openaime/skills - User global skills
    2. {workspace}/skills - Workspace specific skills
    3. User-provided additional paths
    """

    def __init__(self, search_paths: List[str]):
        """Initialize registry with search paths.

        Args:
            search_paths: List of directories to search for skills.
                Each directory contains subdirectories which are skills.
        """
        self._search_paths = self._expand_paths(search_paths)
        self._metadata_cache: dict[str, SkillMetadata] = {}
        self._loaded_cache: dict[str, Skill] = {}

    def _expand_paths(self, paths: List[str]) -> List[str]:
        """Expand user ~ in paths."""
        expanded = []
        for path in paths:
            expanded.append(os.path.abspath(os.path.expanduser(path)))
        return expanded

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from SKILL.md content.

        Returns:
            (frontmatter_dict, content_after_frontmatter)
        """
        match = FRONTMATTER_PATTERN.match(content)
        if match:
            try:
                fm = yaml.safe_load(match.group(1))
                content = content[match.end():]
                return fm or {}, content
            except yaml.YAMLError:
                return {}, content
        return {}, content

    def _parse_metadata(self, skill_dir: str, skill_file: str) -> SkillMetadata:
        """Parse metadata from SKILL.md file."""
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        fm, _ = self._parse_frontmatter(content)

        mtime = os.path.getmtime(skill_file)

        return SkillMetadata(
            name=fm.get('name', os.path.basename(skill_dir)),
            description=fm.get('description', ''),
            path=os.path.abspath(skill_dir),
            skill_file_path=os.path.abspath(skill_file),
            mtime=mtime,
            argument_hint=fm.get('argument-hint'),
            disable_model_invocation=fm.get('disable-model-invocation', False),
            user_invocable=fm.get('user-invocable', False),
            allowed_tools=fm.get('allowed-tools'),
            model=fm.get('model'),
            context=fm.get('context'),
            agent=fm.get('agent'),
            license=fm.get('license'),
            compatibility=fm.get('compatibility'),
            metadata=fm.get('metadata', {}),
        )

    def _load_full(self, metadata: SkillMetadata) -> Skill:
        """Load full skill content from disk (Level 2)."""
        with open(metadata.skill_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        _, instructions = self._parse_frontmatter(content)
        instructions = instructions.strip()

        return Skill(
            metadata=metadata,
            instructions=instructions,
            loaded_mtime=metadata.mtime,
        )

    def _rescan_if_changed(self) -> None:
        """Rescan all search paths and reload metadata for modified skills.

        This is called before every match to enable hot-reload.
        """
        for base_path in self._search_paths:
            if not os.path.exists(base_path):
                continue

            if not os.path.isdir(base_path):
                continue

            # Iterate over each subdirectory - each is a skill
            for entry in os.listdir(base_path):
                skill_dir = os.path.join(base_path, entry)
                if not os.path.isdir(skill_dir):
                    continue

                skill_file = os.path.join(skill_dir, "SKILL.md")
                if not os.path.exists(skill_file):
                    continue

                current_mtime = os.path.getmtime(skill_file)

                # Check if we need to reload
                need_reload = False
                if entry not in self._metadata_cache:
                    need_reload = True
                else:
                    cached = self._metadata_cache[entry]
                    if cached.mtime != current_mtime:
                        need_reload = True

                if need_reload:
                    metadata = self._parse_metadata(skill_dir, skill_file)
                    # Use metadata.name as key, not directory name (allows name != dir name)
                    self._metadata_cache[metadata.name] = metadata
                    # Clear from loaded cache if it was loaded
                    if metadata.name in self._loaded_cache:
                        del self._loaded_cache[metadata.name]

    def get_all_metadata(self) -> List[SkillMetadata]:
        """Get all skill metadata."""
        self._rescan_if_changed()
        return list(self._metadata_cache.values())

    def load_skill(self, name: str) -> Skill:
        """Load a full skill by name (manual loading or after matching)."""
        self._rescan_if_changed()

        if name not in self._metadata_cache:
            raise ValueError(f"Skill '{name}' not found in any search path")

        metadata = self._metadata_cache[name]
        current_mtime = metadata.mtime

        # Check cache
        if name in self._loaded_cache:
            loaded = self._loaded_cache[name]
            if loaded.loaded_mtime == current_mtime:
                return loaded

        # Load from disk
        skill = self._load_full(metadata)
        self._loaded_cache[name] = skill
        return skill

    def match(self, llm: BaseLLM, task_description: str, top_k: int = 3) -> List[Skill]:
        """Match skills to task description using LLM.

        Args:
            llm: LLM instance to use for matching
            task_description: Description of the current task
            top_k: Maximum number of skills to return

        Returns:
            List of loaded Skill objects ready for injection into prompt
        """
        self._rescan_if_changed()

        all_metadata = self.get_all_metadata()
        if not all_metadata:
            return []

        # Build prompt for matching
        metadata_list = "\n".join([
            f"- **{meta.name}**: {meta.description}"
            for meta in all_metadata
        ])

        prompt = f"""Given a task description, select the {top_k} most relevant skills that should be activated to help complete the task.

Task Description: {task_description}

Available Skills:
{metadata_list}

Instructions:
- Analyze the task requirements
- Select up to {top_k} skills that are most relevant
- Output ONLY a JSON array of skill names that should be activated
- If no skills are relevant, output an empty array []

Example Output:
["python-code-review", "git-commit-guide"]
"""
        messages = [Message(role="user", content=prompt)]
        response = llm.complete(messages, temperature=0.0)
        content = response.content.strip() if response.content else "[]"

        # Extract JSON from response
        import json
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        try:
            selected_names = json.loads(content)
        except json.JSONDecodeError:
            # Failed to parse, return empty
            return []

        if not isinstance(selected_names, list):
            return []

        # Load selected skills
        matched = []
        for name in selected_names[:top_k]:
            try:
                skill = self.load_skill(name)
                matched.append(skill)
            except ValueError:
                # Skill not found, skip
                continue

        return matched

    def count_cached_metadata(self) -> int:
        """Get number of cached metadata entries."""
        return len(self._metadata_cache)

    def count_loaded(self) -> int:
        """Get number of fully loaded skills."""
        return len(self._loaded_cache)

    def clear_cache(self) -> None:
        """Clear all caches, force full rescan on next match."""
        self._metadata_cache.clear()
        self._loaded_cache.clear()
```

- [ ] **Step 3: Commit**

```bash
git add aime/base/skill.py
git commit -m "feat(skills): add core skill module with SkillRegistry and hot-reload"
```

---

### Task 3: Add tests with fixture skills

**Files:**
- Create: `tests/fixtures/skills/test-skill-1/SKILL.md`
- Create: `tests/fixtures/skills/test-skill-2/SKILL.md`
- Create: `tests/base/test_skill.py`

- [ ] **Step 1: Create test fixture 1**

```markdown
---
name: test-skill-1
description: A test skill for unit testing. Use when testing the skill loading system.
argument-hint: []
user-invocable: true
model: sonnet
allowed-tools:
  - Read
  - Grep
---

# Test Skill 1

This is a test skill for unit testing.

## Instructions
1. Do the first step
2. Do the second step
3. Verify the result

Always follow these steps when this skill is activated.
```

- [ ] **Step 2: Create test fixture 2**

```markdown
---
name: test-skill-2
description: Another test skill with different functionality. Use when testing multiple skill matching.
user-invocable: false
---

# Test Skill 2

## Different Instructions
This skill has different instructions.
```

- [ ] **Step 3: Write unit tests**

```python
"""Tests for skill module."""
import os
import tempfile
import time
import pytest
from aime.base.skill import SkillRegistry, SkillMetadata, Skill


def get_test_fixtures_path():
    return os.path.join(os.path.dirname(__file__), "..", "fixtures", "skills")


def test_scan_fixtures():
    """Test scanning skills from fixtures directory."""
    fixtures_path = get_test_fixtures_path()
    registry = SkillRegistry([fixtures_path])

    # First match triggers rescan
    registry._rescan_if_changed()

    assert registry.count_cached_metadata() == 2
    names = [meta.name for meta in registry.get_all_metadata()]
    assert "test-skill-1" in names
    assert "test-skill-2" in names


def test_load_skill():
    """Test loading a full skill."""
    fixtures_path = get_test_fixtures_path()
    registry = SkillRegistry([fixtures_path])
    registry._rescan_if_changed()

    skill = registry.load_skill("test-skill-1")

    assert skill.metadata.name == "test-skill-1"
    assert "A test skill for unit testing" in skill.metadata.description
    assert "Test Skill 1" in skill.instructions
    assert "## Instructions" in skill.instructions
    assert skill.loaded_mtime == skill.metadata.mtime


def test_metadata_fields():
    """Test that frontmatter fields are correctly parsed."""
    fixtures_path = get_test_fixtures_path()
    registry = SkillRegistry([fixtures_path])
    registry._rescan_if_changed()

    meta = registry._metadata_cache["test-skill-1"]
    assert meta.argument_hint == "[]"
    assert meta.user_invocable is True
    assert meta.model == "sonnet"
    assert meta.allowed_tools == ["Read", "Grep"]

    meta2 = registry._metadata_cache["test-skill-2"]
    assert meta2.user_invocable is False


def test_hot_reload_detection():
    """Test that modified files are reloaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a skill
        skill_dir = os.path.join(tmpdir, "hot-reload-test")
        os.mkdir(skill_dir)
        skill_file = os.path.join(skill_dir, "SKILL.md")

        with open(skill_file, 'w') as f:
            f.write("""---
name: hot-reload-test
description: Original description
---
Original instructions
""")

        registry = SkillRegistry([tmpdir])
        registry._rescan_if_changed()
        skill = registry.load_skill("hot-reload-test")
        assert skill.instructions.strip() == "Original instructions"
        assert skill.metadata.description == "Original description"

        # Wait a bit for mtime to change
        time.sleep(0.1)

        # Modify the file
        with open(skill_file, 'w') as f:
            f.write("""---
name: hot-reload-test
description: Updated description
---
Updated instructions
""")

        # Next match should reload
        registry._rescan_if_changed()
        skill2 = registry.load_skill("hot-reload-test")
        assert skill2.instructions.strip() == "Updated instructions"
        assert skill2.metadata.description == "Updated description"


def test_expand_user_path():
    """Test that ~ is expanded in search paths."""
    registry = SkillRegistry(["~/.openaime/skills"])
    # ~ should be expanded
    assert registry._search_paths[0].startswith(os.path.expanduser("~"))
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
python -m pytest tests/base/test_skill.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/skills tests/base/test_skill.py
git commit -m "test(skills): add unit tests for skill module"
```

---

### Task 4: Modify `aime/aime.py` to add skills support

**Files:**
- Modify: `aime/aime.py`

- [ ] **Step 1: Add import**

Around line 40 add:
```python
from aime.base.skill import SkillRegistry
```

- [ ] **Step 2: Modify `__init__` signature to add skills parameters**

In `__init__` method parameters:

```python
    def __init__(
        self,
        config: AimeConfig,
        llm: BaseLLM,
        workspace: str,
        log_level: None | Literal["verbose", "debug"] = "verbose",
        debug: Optional[bool] = None,  # Backward compatibility
        toolkit: Optional[Toolkit] = None,
        tool_bundles: Optional[list[ToolBundle]] = None,
        knowledge: Optional[BaseKnowledge] = None,
        event_callback: Optional[EventCallback] = None,
        # New skills parameters
        skills_path: Optional[list[str]] = None,
        auto_discover_skills: bool = True,
    ):
```

Inside `__init__` after workspace validation:

```python
        # Setup skills - build search paths
        if auto_discover_skills:
            # Default search paths
            default_paths = [
                "~/.openaime/skills",
                os.path.join(self.workspace, "skills"),
            ]
            # Add user-provided paths
            if skills_path:
                default_paths.extend(skills_path)
            self.skill_registry = SkillRegistry(default_paths)
        else:
            self.skill_registry = None
```

- [ ] **Step 3: Update ActorFactory creation to pass skill_registry**

Around line 264-269:

```python
            self.actor_factory = ActorFactory(
                base_llm=self.llm,
                actor_config=self.config.actor,
                tool_bundles=self.tool_bundles,
                skill_registry=self.skill_registry,
            )
```

- [ ] **Step 4: Run existing tests to make sure nothing broke**

```bash
python -m pytest tests/test_aime.py -v
```

Expected: All existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add aime/aime.py
git commit -m "feat(skills): add skills support to OpenAime constructor"
```

---

### Task 5: Modify `aime/components/actor_factory.py` to integrate skills

**Files:**
- Modify: `aime/components/actor_factory.py`

- [ ] **Step 1: Add import**

Top of file:
```python
from aime.base.skill import SkillRegistry, Skill
```

- [ ] **Step 2: Add skill_registry parameter to `__init__`**

```python
    def __init__(
        self,
        base_llm: BaseLLM,
        actor_config: ActorConfig,
        tool_bundles: Optional[List[ToolBundle]] = None,
        skill_registry: Optional[SkillRegistry] = None,
    ):
        """
        Initialize the Actor Factory.

        Args:
            base_llm: Base LLM instance to use for actors
            actor_config: Default configuration for created actors
            tool_bundles: List of available tool bundles (pre-organized by capability)
            skill_registry: Optional skill registry for matching skills
        """
        self.base_llm = base_llm
        self.actor_config = actor_config
        self._tool_bundles: dict[str, ToolBundle] = {}

        # Register provided tool bundles
        if tool_bundles:
            for bundle in tool_bundles:
                self.register_tool_bundle(bundle)

        self._actor_counter = 0
        # Registry of created actors for reuse
        self._actors: dict[str, tuple[DynamicActor, ActorRecord]] = {}
        self._skill_registry = skill_registry
```

- [ ] **Step 3: Modify `create_actor` to match skills and pass to DynamicActor**

After `existing_actor` check, before creating new actor:

```python
        # Need to create new actor
        actor_id = f"actor-{self._actor_counter}-{task.id}"
        self._actor_counter += 1

        logger.info(f"ActorFactory creating new actor {actor_id} for task: {task.description}")

        # Select tool bundles based on task analysis
        # Use LLM to select which bundles to include
        selected_bundles = await self._select_tool_bundles(task)
        logger.debug(f"Actor {actor_id} selected bundles: {[b.name for b in selected_bundles]}")

        # Match skills for this task (if skill registry available)
        matched_skills: list[Skill] = []
        if self._skill_registry is not None:
            matched_skills = self._skill_registry.match(
                llm=self.base_llm,
                task_description=task.description,
                top_k=3,
            )
            if matched_skills:
                logger.info(f"Actor {actor_id} matched skills: {[s.metadata.name for s in matched_skills]}")
```

Then when creating `DynamicActor`:

```python
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
            emit_event=emit_event,
            matched_skills=matched_skills,
        )
```

And for the reused existing actor path too:

```python
        if existing_actor is not None:
            # Update the task on the reused actor and reset state
            existing_actor.task = task
            async with existing_actor._lock:
                existing_actor._running = False
            existing_actor._history.clear()
            logger.info(f"ActorFactory reusing existing actor: {existing_actor.actor_id}")
            # Re-match skills for the new task
            if self._skill_registry is not None:
                matched_skills = self._skill_registry.match(
                    llm=self.base_llm,
                    task_description=task.description,
                    top_k=3,
                )
                existing_actor._matched_skills = matched_skills
            return existing_actor
```

- [ ] **Step 4: Run existing tests to verify nothing broke**

```bash
python -m pytest tests/components/test_actor_factory.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add aime/components/actor_factory.py
git commit -m "feat(skills): integrate skill registry into ActorFactory"
```

---

### Task 6: Modify `aime/components/actor.py` to inject skills into system prompt

**Files:**
- Modify: `aime/components/actor.py`

- [ ] **Step 1: Add import**

Top of file add:
```python
from aime.base.skill import Skill
```

- [ ] **Step 2: Add matched_skills parameter to `__init__`**

```python
    def __init__(
        self,
        actor_id: str,
        role: str,
        task: Task,
        llm: BaseLLM,
        planner: Planner,
        progress: ProgressModule,
        toolkit: Toolkit,
        knowledge: BaseKnowledge,
        config: ActorConfig,
        emit_event: None | Callable[[EventType, dict[str, Any]], None] = None,
        matched_skills: list[Skill] = [],
    ):
        """
        Initialize the DynamicActor for a specific subtask.

        Args:
            actor_id: Unique identifier for this actor
            role: Specialized role description for this task
            task: The subtask to execute
            llm: LLM instance to use for this actor
            planner: The planner coordinating overall execution
            progress: Progress module for updating status
            toolkit: Customized toolkit for this task
            knowledge: Knowledge base for retrieval
            config: Actor configuration
            emit_event: Optional callback to emit events (used for real-time streaming).
            matched_skills: List of matched skills to inject into system prompt
        """
        self.actor_id = actor_id
        self.role = role
        self.task = task
        self.llm = llm
        self.planner = planner
        self.progress = progress
        self.toolkit = toolkit
        self.knowledge = knowledge
        self.config = config
        self._emit_event = emit_event

        self._running = False
        self._lock = asyncio.Lock()

        # Conversation history for ReAct
        self._history: List[Message] = []
        self._matched_skills = matched_skills
```

- [ ] **Step 3: Modify `_build_system_prompt` to inject skills at the end**

At the end of `_build_system_prompt()` method before the return:

```python
        # Inject matched skills instructions if any
        skills_section = ""
        if self._matched_skills:
            skills_section += "\n\n## Activated Skills\n\n"
            for skill in self._matched_skills:
                skills_section += f"### {skill.metadata.name}\n"
                skills_section += f"**Description:** {skill.metadata.description}\n\n"
                # Fix relative resource paths to be absolute
                # This allows actors to correctly read references via tools
                skill_instructions = skill.instructions
                # Replace various forms of quoted relative paths
                skill_instructions = skill_instructions.replace(
                    '"references/',
                    f'"{os.path.join(skill.metadata.path, "references/")}'
                )
                skill_instructions = skill_instructions.replace(
                    "'references/",
                    f"'{os.path.join(skill.metadata.path, "references/")}"
                )
                skill_instructions = skill_instructions.replace(
                    '`references/',
                    f'`{os.path.join(skill.metadata.path, "references/")}'
                )
                skill_instructions = skill_instructions.replace(
                    '"scripts/',
                    f'"{os.path.join(skill.metadata.path, "scripts/")}'
                )
                skill_instructions = skill_instructions.replace(
                    "'scripts/",
                    f"'{os.path.join(skill.metadata.path, "scripts/")}"
                )
                skill_instructions = skill_instructions.replace(
                    '`scripts/',
                    f'`{os.path.join(skill.metadata.path, "scripts/")}'
                )
                skills_section += skill_instructions
                skills_section += "\n\n---\n"
```

Then update the return statement to include it:

```python
        return (
            f"Role: {self.role}\n\n"
            f"Your Task: {self.task.description}\n"
            f"Completion Criteria: {self.task.completion_criteria}\n\n"
            f"{env_info}\n"
            f"{progress_info}\n"
            "Available Tools:\n"
            f"{tools_description}\n\n"
            "ReAct Instructions:\n"
            "You run in a loop of THOUGHT, ACTION, OBSERVATION.\n\n"
            "THOUGHT: Your reasoning about what to do next. Explain your thinking step by step.\n"
            "ACTION: The action to take, in JSON format with 'tool' and 'parameters'.\n"
            "  - To finish the task, use: {\"tool\": \"finish\", \"parameters\": {\"summary\": \"your summary here\"}}\n"
            "  - To use a tool, use: {\"tool\": \"tool_name\", \"parameters\": {\"key\": \"value\"}}\n\n"
            "Output Format:\n"
            "THOUGHT: <your reasoning>\n"
            "ACTION: <json action>\n\n"
            "Example:\n"
            "THOUGHT: I need to read the README file to understand the project structure.\n"
            "ACTION: {\"tool\": \"file_read\", \"parameters\": {\"file_path\": \"README.md\"}}\n"
            + skills_section
        )
```

- [ ] **Step 4: Run existing tests to verify nothing broke**

```bash
python -m pytest tests/components/test_actor.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add aime/components/actor.py
git commit -m "feat(skills): inject matched skills into actor system prompt"
```

---

### Task 7: Run all tests to verify everything works

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: All 193+ tests pass.

- [ ] **Step 2: If any tests fail, fix them**

- [ ] **Step 3: Commit any fixes**

---

### Task 8: Update documentation in `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add "Skills System" section to Implemented Features**

Add after "8. Session Multi-turn Interaction":

```markdown
### 9. Skills System (Claude Code compatible)

Modular capability extension system with progressive disclosure and hot-reload:
- **Progressive Disclosure**: Only metadata loaded at startup (~100 tokens/skill), full instructions loaded on match, resources loaded on-demand
- **Hot-Reload**: Automatically detects changes to skill files, no restart required
- **Default Search Paths**: `~/.openaime/skills` (global user skills) and `{workspace}/skills` (project-specific skills)
- **Automatic Matching**: LLM matches skills to task description automatically
- **Claude Compatible**: Uses same SKILL.md format as Claude Code skills
- **Path Resolution**: Automatically resolves relative paths for references/scripts

Files:
- `aime/base/skill.py` - SkillMetadata, Skill, SkillRegistry with hot-reload
- Modified: `aime/aime.py`, `aime/components/actor_factory.py`, `aime/components/actor.py`
```

- [ ] **Step 2: Update Project Structure section to include `aime/base/skill.py`**

- [ ] **Step 3: Add Skills usage example to Quick Start**

Add after Multi-turn Interaction example:

```python
### With Skills

```python
import asyncio
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.providers.llm.anthropic import AnthropicLLM

llm = AnthropicLLM(api_key="your-api-key")
aime = OpenAime(
    config=AimeConfig(),
    llm=llm,
    workspace="./your-project-directory",
    # Skills are auto-discovered from:
    # - ~/.openaime/skills
    # - ./your-project-directory/skills
    auto_discover_skills=True,
    # Add extra custom skills paths
    # skills_path=["./my-custom-skills"],
)

# When you run a task that matches a skill, it's automatically activated
result = await aime.run("Review the Python code in src/ and check for style issues")
# If you have a "python-code-review" skill, it will be automatically loaded and used
```

```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update documentation for skills feature"
```
