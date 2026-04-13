"""
OpenAime Main Entry Point - Integrates all components together.

The OpenAime class is the main entry point for the AIME framework. It combines
all components (Planner, ProgressModule, DynamicActor, Toolkit, Knowledge) into
a simple, high-level API for users to run autonomous agents with a given goal.

According to the AIME paper, this class orchestrates:
- Initialization of all components
- Starting/stopping actors
- Running the autonomous agent lifecycle
- Handling goal completion
- Resource cleanup

Features:
- Async API for modern Python applications
- Proper initialization and shutdown
- Simple high-level interface
- Extensible through configuration and components
- Colored logging with different colors per log level
- Configurable debug mode for verbose output
- Real-time event streaming via optional callback
"""
import asyncio
import logging
import os
import inspect
from typing import Optional, Any, Literal

from aime.utils.logging import configure_logging
from aime.base.config import AimeConfig
from aime.base.llm import BaseLLM, Message
from aime.base.tool import Toolkit, ToolBundle
from aime.base.knowledge import BaseKnowledge, SimpleInMemoryKnowledge
from aime.base.events import EventType, AimeEvent, EventCallback
from aime.components.planner import Planner
from aime.components.actor_factory import ActorFactory
from aime.components.actor import DynamicActor
from aime.components.progress_module import ProgressModule
from aime.base.types import PlannerOutput, Task, TaskStatus, ChatMessage
from aime.base.skill import SkillRegistry
from aime.base.session_manager import SessionManager, get_default_session_manager
from aime.base.session import SessionInfo

logger = logging.getLogger(__name__)


class OpenAime:
    """
    Main OpenAime class that integrates all components together.

    Provides a simple high-level API for users to run the autonomous agent
    with a given goal. Handles initialization, starting/stopping, and resource
    management.

    Attributes:
        config: Configuration for the OpenAime instance
        llm: The LLM to use for planning and decision-making
        debug: Whether debug logging is enabled
        toolkit: Toolkit containing available tools
        tool_bundles: List of tool bundles for ActorFactory
        knowledge: Knowledge base for information retrieval
        planner: Planner component for task planning
        progress: Progress module for tracking task status
        actor_factory: ActorFactory for creating dynamic actors
        _running: Flag indicating if the agent is running
        _lock: Lock for thread-safe operations
    """

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
        # Session persistence parameters
        auto_save_session: Optional[bool] = None,
        session_id: Optional[str] = None,
        session_manager: Optional[SessionManager] = None,
        store_full_actor_history: Optional[bool] = None,
    ):
        """
        Initialize the OpenAime instance.

        Args:
            config: Configuration from aime.base.config
            llm: The LLM to use for planning and decision-making
            workspace: The directory where OpenAime will work. Must exist.
            log_level: Logging verbosity:
                - None: completely silent, no logging output at all
                - "verbose": print info/warning/error messages (default)
                - "debug": enable debug logging for AIME package
            debug: Deprecated. Use log_level instead. True maps to "debug", False maps to "verbose".
            toolkit: Optional Toolkit containing available tools. If None, an
                empty toolkit will be used.
            tool_bundles: Optional list of pre-organized tool bundles by capability.
                These are used by ActorFactory to select appropriate tools for each task.
            knowledge: Optional Knowledge base for information retrieval. If
                None, a SimpleInMemoryKnowledge instance will be used.
            event_callback: Optional callback function that receives real-time
                events as execution progresses. Can be sync or async.

        Raises:
            ValueError: If workspace directory does not exist
        """
        # Handle backward compatibility for deprecated debug parameter
        if debug is not None:
            log_level = "debug" if debug else "verbose"

        self.config = config
        self.llm = llm
        self.log_level = log_level
        self.toolkit = toolkit or Toolkit()
        self.tool_bundles = tool_bundles or []
        self.knowledge = knowledge or SimpleInMemoryKnowledge()
        self.event_callback = event_callback
        self.planner: Optional[Planner] = None
        self.progress: Optional[ProgressModule] = None
        self.actor_factory: Optional[ActorFactory] = None
        self._running = False
        self._lock = asyncio.Lock()
        self._chat_history: list[ChatMessage] = []

        # Session persistence
        self.auto_save_session = auto_save_session if auto_save_session is not None else self.config.auto_save_session
        self.store_full_actor_history = store_full_actor_history if store_full_actor_history is not None else self.config.store_full_actor_history
        self.session_manager = session_manager or get_default_session_manager()
        self._current_session_id: Optional[str] = session_id

        if session_id is not None:
            # Load chat history from session if session_id is provided
            self._chat_history = self.session_manager.load_chat_history(session_id)

        # Configure logging
        configure_logging(log_level)

        # Validate and store workspace
        self.workspace = os.path.abspath(workspace)
        if not os.path.exists(self.workspace):
            raise ValueError(f"Workspace directory does not exist: {self.workspace}")
        if not os.path.isdir(self.workspace):
            raise ValueError(f"Workspace must be a directory: {self.workspace}")

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

        # Setup UserQuestionManager with event emitter
        from aime.base.user_question import UserQuestionManager
        user_question_manager = UserQuestionManager.get_instance()
        user_question_manager.set_emit_event_callback(self._emit_event)

    def _emit_event(self, event_type: EventType, data: dict[str, Any]) -> None:
        """
        Emit an event to the registered callback if it exists.

        Handles both synchronous and asynchronous callbacks.
        For async callbacks, creates a background task to avoid blocking.

        Args:
            event_type: Type of the event
            data: Event-specific data
        """
        if self.event_callback is None:
            return

        event = AimeEvent(event_type=event_type, data=data)

        # Check if callback is async
        if inspect.iscoroutinefunction(self.event_callback):
            # Create background task - don't block current execution
            asyncio.create_task(self.event_callback(event))
        else:
            # Sync callback - call directly
            self.event_callback(event)

        # Save event to session if auto_save_session is enabled and we have a current session
        if self.auto_save_session and self._current_session_id is not None:
            event_dict = {
                "event_type": event_type.value,
                "data": data,
            }
            self.session_manager.append_event(self._current_session_id, event_dict)

            # Also update actor registry - after actor creation events we need to save the latest registry
            if self.actor_factory is not None:
                actor_registry = self.actor_factory.get_actor_registry()
                self.session_manager.update_metadata(
                    self._current_session_id,
                    actor_registry=actor_registry
                )

    async def run(self, goal: str) -> str:
        """
        Run the autonomous agent to achieve a specific goal.

        This is the main entry point method that:
        1. Saves original working directory
        2. Changes to workspace directory
        3. Initializes all components (reusing existing if possible)
        4. Waits until the planner decides the goal is complete
        5. Restores original working directory
        6. Returns the final status

        In a multi-goal session:
        - Chat history is always preserved for context across goals
        - Previous progress is archived to history, new empty progress is created
        - Planner always does initial decomposition for each new goal
        - Planner and actor_factory are reused with accumulated context

        Args:
            goal: The overall goal to achieve

        Returns:
            Final status message indicating whether the goal was completed

        Raises:
            Exception: If any error occurs during execution
        """
        logger.info(f"Starting OpenAime to achieve goal: {goal}")
        async with self._lock:
            if self._running:
                raise RuntimeError("OpenAime instance is already running")
            self._running = True

        # Archive existing progress if it exists (always start fresh for new goal)
        # Keep chat history for context, just archive old task list
        if self.progress is not None:
            self.progress.archive_current()

        # Always add current goal to chat history - preserve context across goals
        user_message = ChatMessage(role="user", content=goal)
        self._chat_history.append(user_message)

        # Handle session persistence for user message
        if self.auto_save_session:
            if self._current_session_id is None:
                # Create new session if none exists
                session_info = self.session_manager.get_or_create_current_session()
                self._current_session_id = session_info.session_id
            # Update session metadata
            model_name = getattr(self.llm, 'model_id', 'unknown')
            self.session_manager.update_metadata(
                self._current_session_id,
                title=goal[:50],
                goal_description=goal,
                workspace_path=self.workspace,
                model_name=model_name
            )
            # Append user message to session
            self.session_manager.append_message(self._current_session_id, user_message)

            # Save actor registry if actor factory exists
            if self.actor_factory is not None:
                actor_registry = self.actor_factory.get_actor_registry()
                self.session_manager.update_metadata(
                    self._current_session_id,
                    actor_registry=actor_registry
                )

        original_cwd = os.getcwd()
        try:
            # Change to workspace directory
            logger.debug(f"Changing working directory to: {self.workspace}")
            os.chdir(self.workspace)

            # Initialize all components
            logger.debug("Initializing all components")
            await self._initialize_components(goal)

            # Wait for goal completion
            # In the new architecture, actors are created dynamically for each subtask
            # No pre-started actor needed
            logger.debug("Waiting for goal completion")
            final_status = await self._wait_for_goal_completion()

            # Generate execution summary and add as assistant message
            summary = await self._generate_execution_summary()
            assistant_message = ChatMessage(role="assistant", content=summary)
            self._chat_history.append(assistant_message)

            # Also add to planner for next run
            if self.planner is not None:
                self.planner.add_assistant_message(summary)

            # Handle session persistence for assistant message
            if self.auto_save_session and self._current_session_id is not None:
                self.session_manager.append_message(self._current_session_id, assistant_message)

            # Check if goal succeeded or failed
            success = "completed" in final_status.lower() and "failed" not in final_status.lower()
            self._emit_event(EventType.EXECUTION_FINISHED, {
                "success": success,
                "final_status": final_status,
            })

            logger.info(f"Goal completed: {final_status}")
            return final_status

        finally:
            # Restore original working directory
            try:
                logger.debug(f"Restoring original working directory: {original_cwd}")
                os.chdir(original_cwd)
            except Exception as e:
                logger.error(f"Failed to restore working directory: {e}")

            # Cleanup resources - keep components for session continuity
            logger.debug("Cleaning up resources")
            await self._cleanup()
            logger.info("OpenAime execution stopped")

    async def _initialize_components(self, goal: str) -> None:
        """
        Initialize all components with the given goal.
        Reuses existing components if they already exist for session continuity.

        In the new unified logic:
        - progress is always created fresh (previous was already archived before calling)
        - planner is reused if exists (keeps accumulated chat history)
        - actor factory is reused if exists (keeps cached actors)

        Args:
            goal: The overall goal to achieve
        """
        # Emit goal started event
        self._emit_event(EventType.PLANNER_GOAL_STARTED, {
            "goal": goal,
        })

        # Always create a new progress module - previous progress was already archived
        self.progress = ProgressModule(emit_event=self._emit_event)

        # Create planner if it doesn't exist
        if self.planner is None:
            self.planner = Planner(self.llm, self.config.planner, emit_event=self._emit_event)
            # If we have a loaded session, sync chat history to planner
            if self._current_session_id is not None and self._chat_history:
                self.planner.load_chat_history(self._chat_history)

        # Initialize planner with the goal (will append to chat history if already initialized)
        await self.planner.initialize(goal, self.progress)

        # Create actor factory if it doesn't exist
        if self.actor_factory is None:
            self.actor_factory = ActorFactory(
                base_llm=self.llm,
                actor_config=self.config.actor,
                tool_bundles=self.tool_bundles,
                skill_registry=self.skill_registry,
                store_full_actor_history=self.store_full_actor_history,
            )

            # Register all individual tools from toolkit as a default bundle
            if self.toolkit.get_all_tools() and not self.tool_bundles:
                from aime.base.tool import ToolBundle
                default_bundle = ToolBundle(
                    name="default",
                    description="Default bundle with all available tools",
                    tools=self.toolkit.get_all_tools(),
                )
                self.actor_factory.register_tool_bundle(default_bundle)

            # If we have a loaded session with actor registry, restore it
            if self._current_session_id is not None and self.actor_factory is not None:
                session_info = self.session_manager.get_session_info(self._current_session_id)
                if session_info and session_info.actor_registry is not None:
                    self.actor_factory.load_actor_registry(session_info.actor_registry)

    async def _wait_for_goal_completion(self) -> str:
        """
        Wait until the planner decides the goal is complete.

        According to AIME paper workflow:
        1. Planner decides next action
        2. If dispatch_subtask with subtask_id → get task → ask ActorFactory to create actor → run actor → done
        3. If complete_goal → return
        4. If wait → wait and try again

        Returns:
            Status message indicating goal completion
        """
        assert self.planner is not None, "Planner not initialized"
        assert self.progress is not None, "Progress not initialized"
        assert self.actor_factory is not None, "ActorFactory not initialized"

        iteration_count = 0
        max_iterations = self.config.max_total_iterations

        while iteration_count < max_iterations:
            # Check if we should stop
            async with self._lock:
                if not self._running:
                    return "Agent stopped by user"

            # Get next plan step
            plan_output = await self.planner.plan_step(self.progress)

            if plan_output.action == PlannerOutput.Action.COMPLETE_GOAL:
                logger.info("Planner decided goal is complete")
                return "Goal completed successfully"

            elif plan_output.action == PlannerOutput.Action.WAIT:
                # Wait for something to change
                logger.debug("Planner decided to wait")
                await asyncio.sleep(1.0)

            elif plan_output.action == PlannerOutput.Action.DISPATCH_SUBTASK:
                # Get the subtask to dispatch
                subtask_id = plan_output.subtask_id
                if not subtask_id:
                    logger.warning("Planner output dispatch_subtask but no subtask_id, waiting")
                    await asyncio.sleep(0.5)
                    iteration_count += 1
                    continue

                task = await self.progress.get_task(subtask_id)
                if not task:
                    logger.warning(f"Subtask {subtask_id} not found, waiting")
                    await asyncio.sleep(0.5)
                    iteration_count += 1
                    continue

                logger.info(f"Dispatching subtask {subtask_id} to ActorFactory: {task.description}")

                # Create actor for this subtask and run it
                actor = await self.actor_factory.create_actor(
                    task=task,
                    planner=self.planner,
                    progress=self.progress,
                    knowledge=self.knowledge,
                    emit_event=self._emit_event,
                )

                # Run the actor to completion
                result = await actor.run()

                logger.debug(f"Subtask {subtask_id} completed with status: {result.status.value}")

            iteration_count += 1

        return f"Goal not completed within {max_iterations} iterations"

    async def _cleanup(self) -> None:
        """
        Clean up all resources.
        Keeps planner, progress, and actor_factory for session continuity.
        """
        async with self._lock:
            self._running = False

        # All actors are temporary and finish after running, no need to stop
        # Keep planner, progress, and actor_factory for session continuity

    async def stop(self) -> None:
        """
        Stop the agent gracefully.

        Can be called from another async task to stop the agent while it's running.
        """
        async with self._lock:
            self._running = False

    async def is_running(self) -> bool:
        """
        Check if the agent is currently running.

        Returns:
            True if running, False otherwise
        """
        async with self._lock:
            return self._running

    async def get_progress(self) -> str:
        """
        Get the current progress as markdown.

        Returns:
            Markdown string representing the current progress
        """
        if self.progress:
            return await self.progress.export_markdown()
        return "No progress available"

    async def clear_session(self) -> None:
        """
        Clear the current session context.
        This includes chat history, progress tracking, planner, and actor factory.
        """
        logger.debug("Clearing session context")
        self._chat_history.clear()
        self.planner = None
        self.progress = None
        self.actor_factory = None
        self._current_session_id = None

    def is_session_empty(self) -> bool:
        """
        Check if the session is empty (no chat history).

        Returns:
            True if session is empty, False otherwise
        """
        return len(self._chat_history) == 0

    def get_current_session_id(self) -> Optional[str]:
        """
        Get the current session ID.

        Returns:
            Current session ID if set, None otherwise
        """
        return self._current_session_id

    def load_session(self, session_id: str) -> None:
        """
        Load chat history from a specific session.

        Args:
            session_id: The session ID to load
        """
        logger.debug(f"Loading session: {session_id}")
        self._current_session_id = session_id
        self._chat_history = self.session_manager.load_chat_history(session_id)

        # If planner is already initialized, sync chat history
        if self.planner is not None:
            self.planner.load_chat_history(self._chat_history)

        # Load actor registry if available
        session_info = self.session_manager.get_session_info(session_id)
        if session_info and session_info.actor_registry is not None:
            # Create actor factory if it doesn't exist yet (may happen when loading session before first run)
            if self.actor_factory is None:
                self.actor_factory = ActorFactory(
                    base_llm=self.llm,
                    actor_config=self.config.actor,
                    tool_bundles=self.tool_bundles,
                    skill_registry=self.skill_registry,
                    store_full_actor_history=self.store_full_actor_history,
                )
                # Register all individual tools from toolkit as a default bundle if needed
                if self.toolkit.get_all_tools() and not self.tool_bundles:
                    from aime.base.tool import ToolBundle
                    default_bundle = ToolBundle(
                        name="default",
                        description="Default tools including all builtin tools",
                        tools=self.toolkit.get_all_tools(),
                    )
                    self.actor_factory.register_tool_bundle(default_bundle)
            # Now load the actor registry from the saved session
            self.actor_factory.load_actor_registry(session_info.actor_registry)

    async def _generate_execution_summary(self) -> str:
        """
        Generate an execution summary using LLM based on current task status.

        Returns:
            Summary of the current execution status
        """
        if self.progress is None:
            return "No tasks have been created yet"

        # Get all tasks
        tasks = await self.progress.get_all_tasks()

        # Build task status string
        task_statuses = []
        for task in tasks:
            status_emoji = "✅" if task.status == TaskStatus.COMPLETED else \
                          "❌" if task.status == TaskStatus.FAILED else \
                          "⏳" if task.status == TaskStatus.IN_PROGRESS else \
                          "📋"
            task_statuses.append(f"{status_emoji} {task.description} ({task.status.value})")

        task_status_str = "\n".join(task_statuses)

        prompt = (
            "Generate a concise summary of the current execution status based on the tasks below.\n"
            "Focus on what has been completed, what is in progress, and any failures.\n\n"
            "Tasks:\n"
            f"{task_status_str}"
        )

        messages = [
            Message(
                role="system",
                content="You are an assistant that summarizes task progress"
            ),
            Message(
                role="user",
                content=prompt
            )
        ]

        try:
            response = await self.llm.complete(messages)
            return response.content or "Unable to generate summary"
        except Exception as e:
            logger.warning(f"Failed to generate execution summary: {e}")
            return "Failed to generate summary"
