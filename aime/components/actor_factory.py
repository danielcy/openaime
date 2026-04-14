"""
Actor Factory Component - Dynamic Actor instantiation for AIME framework.

According to the AIME paper, the Actor Factory:
- Receives a subtask from the dynamic planner
- Analyzes the task requirements
- Selects the appropriate tool bundle based on capability needs
- Composes a customized system prompt with role, tools, knowledge, environment
- Instantiates a specialized DynamicActor for this specific task
"""
import logging
from typing import Optional, List, Any, Callable

from aime.base.types import Task, ActorRecord
from aime.base.llm import BaseLLM
from aime.base.tool import BaseTool, Toolkit, ToolBundle
from aime.base.config import ActorConfig
from aime.base.knowledge import BaseKnowledge
from aime.base.events import EventType
from aime.components.planner import Planner
from aime.components.progress_module import ProgressModule
from aime.components.actor import DynamicActor
from aime.base.skill import SkillRegistry, Skill

logger = logging.getLogger(__name__)


class ActorFactory:
    """
    Actor Factory that dynamically instantiates specialized DynamicActors
    according to subtask requirements.

    According to AIME paper, this enables:
    - On-demand assembly of actors instead of fixed pre-defined roles
    - Each actor gets exactly the tools and knowledge it needs
    - Better focus and reduced cognitive load on LLM
    """

    def __init__(
        self,
        base_llm: BaseLLM,
        actor_config: ActorConfig,
        tool_bundles: Optional[List[ToolBundle]] = None,
        skill_registry: Optional[SkillRegistry] = None,
        store_full_actor_history: bool = False,
    ):
        """
        Initialize the Actor Factory.

        Args:
            base_llm: Base LLM instance to use for actors
            actor_config: Default configuration for created actors
            tool_bundles: List of available tool bundles (pre-organized by capability)
            skill_registry: Optional skill registry for matching skills
            store_full_actor_history: Whether to store full actor history in chat history
        """
        self.base_llm = base_llm
        self.actor_config = actor_config
        self._tool_bundles: dict[str, ToolBundle] = {}
        self.store_full_actor_history = store_full_actor_history

        # Register provided tool bundles
        if tool_bundles:
            for bundle in tool_bundles:
                self.register_tool_bundle(bundle)

        self._actor_counter = 0
        # Registry of created actors for reuse
        self._actors: dict[str, tuple[DynamicActor, ActorRecord]] = {}
        self._skill_registry = skill_registry

    def register_tool_bundle(self, bundle: ToolBundle) -> None:
        """
        Register a tool bundle with the factory.

        Args:
            bundle: ToolBundle to register
        """
        self._tool_bundles[bundle.name] = bundle
        logger.debug(f"Registered tool bundle: {bundle.name}")

    def get_available_tool_bundles(self) -> List[str]:
        """
        Get list of available tool bundle names.

        Returns:
            List of bundle names
        """
        return list(self._tool_bundles.keys())

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
            f"- Actor Name: {record.name}\n  Actor ID: {record.actor_id}\n  Role: {record.role}\n  Description: {record.description}\n  Tool Bundles: {', '.join(record.tool_bundles)}\n  Last used: {record.last_used_at.strftime('%Y-%m-%d %H:%M')}"
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
- **Prioritize reusing existing actors when capabilities are ROUGHLY matching** — you do NOT need an exact match.
- **Reuse is more efficient than creating new actors** — only create new when no existing actor is even close.
- If one existing actor is clearly suitable, output ONLY its actor_id in JSON format.
- If no existing actor is suitable (need to create new), output null.

"Roughly matching" examples:
- If existing actor is "Python Developer" and new task is modifying Python code → REUSE
- If existing actor is "fiction Writer" and new task is writing a blog post → REUSE
- Only create new when the capability is completely different

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
                if actor is not None:
                    logger.info(f"ActorFactory reusing existing actor: {selected_id}")
                    return actor
                else:
                    logger.debug(f"ActorFactory: Actor {selected_id} exists as metadata only, will recreate")
                    return None
            else:
                logger.warning(f"LLM selected non-existent actor_id: {selected_id}, creating new")
                return None
        except Exception as e:
            logger.warning(f"Failed to parse LLM actor selection: {e}, creating new")
            return None

    async def create_actor(
        self,
        task: Task,
        planner: Planner,
        progress: ProgressModule,
        knowledge: BaseKnowledge,
        emit_event: None | Callable[[EventType, dict[str, Any]], None] = None,
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
            emit_event: Optional callback to emit events for real-time streaming

        Returns:
            Instantiated DynamicActor ready to run
        """
        # Check if we can reuse an existing actor
        existing_actor = await self._select_actor_for_task(task)
        if existing_actor is not None:
            # Update the task on the reused actor and reset state
            existing_actor.task = task
            existing_actor.planner = planner
            existing_actor.progress = progress
            async with existing_actor._lock:
                existing_actor._running = False
            existing_actor._history.clear()
            logger.info(f"ActorFactory reusing existing actor: {existing_actor.actor_id}")
            # Re-match skills for the new task
            if self._skill_registry is not None:
                matched_skills = await self._skill_registry.match(
                    llm=self.base_llm,
                    task_description=task.description,
                    top_k=3,
                )
                existing_actor._matched_skills = matched_skills
            return existing_actor

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
            matched_skills = await self._skill_registry.match(
                llm=self.base_llm,
                task_description=task.description,
                top_k=3,
            )
            if matched_skills:
                logger.info(f"Actor {actor_id} matched skills: {[s.metadata.name for s in matched_skills]}")

        # Build toolkit from selected bundles
        toolkit = Toolkit()
        for bundle in selected_bundles:
            toolkit.add_bundle(bundle)

        # Get selected bundle names
        selected_bundle_names = [b.name for b in selected_bundles]

        # Retrieve relevant knowledge
        # TODO: knowledge retrieval based on task description

        # Generate actor role based on task
        role = await self._generate_role(task)
        logger.debug(f"Actor {actor_id} role: {role}")

        # Generate actor description
        description = await self._generate_description(task, role)

        # Generate short name for the actor
        from aime.base.llm import Message
        name_prompt = f"""Given the role description and selected tool bundles below, generate a short 2-6 word name for this actor that clearly describes its specialization.
Output ONLY the name, no extra text, explanation, or punctuation.

Role: {role}
Tool Bundles: {', '.join(selected_bundle_names)}
"""
        name_messages = [Message(role="user", content=name_prompt)]
        name_response = await self.base_llm.complete(name_messages, temperature=0.3)
        name = name_response.content.strip()
        name = name.strip('"\'')
        # Truncate to keep it compact
        if len(name) > 30:
            name = name[:27] + "..."

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
            store_full_actor_history=self.store_full_actor_history,
            name=name,
        )

        # Store in registry for future reuse
        record = ActorRecord(
            actor_id=actor_id,
            name=name,
            role=role,
            description=description,
            tool_bundles=selected_bundle_names,
        )
        self._actors[actor_id] = (actor, record)

        logger.info(f"Actor {actor_id} created and stored for future reuse")
        return actor

    async def _select_tool_bundles(self, task: Task) -> List[ToolBundle]:
        """
        Use LLM to select appropriate tool bundles for the task.

        Args:
            task: The task to analyze

        Returns:
            List of selected ToolBundles
        """
        if not self._tool_bundles:
            logger.warning("No tool bundles registered, returning empty")
            return []

        # If only one bundle, just return it
        if len(self._tool_bundles) == 1:
            return list(self._tool_bundles.values())

        # TODO: Use LLM to select based on task description
        # For now, include all bundles - this will be improved later
        return list(self._tool_bundles.values())

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
        # if len(self._tool_bundles) <= 1:
        #     # Simple heuristic when there's only one bundle
        #     return f"You are a specialized expert for completing this task: {task.description}"

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

    def list_actors(self) -> List[ActorRecord]:
        """List all created actors available for reuse."""
        return [record for _, record in self._actors.values()]

    def clear_actors(self) -> None:
        """Clear all cached actors."""
        self._actors.clear()
        logger.debug("Actor registry cleared")

    def get_actor_registry(self) -> List[ActorRecord]:
        """Get the current actor registry (all ActorRecord metadata).

        Returns:
            List of ActorRecord for all cached actors
        """
        return self.list_actors()

    def load_actor_registry(self, records: List[ActorRecord]) -> None:
        """Load actor registry from persisted records.

        This loads the ActorRecord metadata into the registry.
        Note: Full DynamicActor instances cannot be persisted because they contain
        references to current session components (planner, progress). Only the
        registry metadata is restored, and actors will be recreated when needed.

        Args:
            records: List of ActorRecord to load
        """
        # Clear existing actors
        self._actors.clear()
        # Add all loaded records - we store None as the actor instance temporarily,
        # the actual actor will be created when it's selected for reuse
        for record in records:
            # Backward compatibility: if record has no name, generate fallback from role
            if not record.name:
                if len(record.role) > 50:
                    record.name = record.role[:50] + "..."
                else:
                    record.name = record.role
            self._actors[record.actor_id] = (None, record)
        # Update actor counter to avoid ID collisions
        if records:
            # Find max actor counter from existing actor IDs (format: actor-N-...)
            max_counter = 0
            for record in records:
                import re
                match = re.match(r'actor-(\d+)-', record.actor_id)
                if match:
                    counter = int(match.group(1))
                    if counter > max_counter:
                        max_counter = counter
            self._actor_counter = max_counter + 1

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ActorFactory(bundles={list(self._tool_bundles.keys())})"
