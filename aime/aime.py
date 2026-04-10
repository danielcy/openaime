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
"""
import asyncio
import logging
import os
from typing import Optional

from aime.base.config import AimeConfig
from aime.base.llm import BaseLLM
from aime.base.tool import Toolkit, ToolBundle
from aime.base.knowledge import BaseKnowledge, SimpleInMemoryKnowledge
from aime.components.planner import Planner
from aime.components.actor_factory import ActorFactory
from aime.components.actor import DynamicActor
from aime.components.progress_module import ProgressModule
from aime.base.types import PlannerOutput, Task

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
        toolkit: Toolkit containing available tools
        tool_bundles: List of tool bundles for ActorFactory
        knowledge: Knowledge base for information retrieval
        planner: Planner component for task planning
        progress: ProgressModule for tracking task status
        actor_factory: ActorFactory for creating dynamic actors
        _running: Flag indicating if the agent is running
        _lock: Lock for thread-safe operations
    """

    def __init__(
        self,
        config: AimeConfig,
        llm: BaseLLM,
        workspace: str,
        toolkit: Optional[Toolkit] = None,
        tool_bundles: Optional[list[ToolBundle]] = None,
        knowledge: Optional[BaseKnowledge] = None,
    ):
        """
        Initialize the OpenAime instance.

        Args:
            config: Configuration from aime.base.config
            llm: The LLM to use for planning and decision-making
            workspace: The directory where OpenAime will work. Must exist.
            toolkit: Optional Toolkit containing available tools. If None, an
                empty toolkit will be used.
            tool_bundles: Optional list of pre-organized tool bundles by capability.
                These are used by ActorFactory to select appropriate tools for each task.
            knowledge: Optional Knowledge base for information retrieval. If
                None, a SimpleInMemoryKnowledge instance will be used.

        Raises:
            ValueError: If workspace directory does not exist
        """
        self.config = config
        self.llm = llm
        self.toolkit = toolkit or Toolkit()
        self.tool_bundles = tool_bundles or []
        self.knowledge = knowledge or SimpleInMemoryKnowledge()
        self.planner: Optional[Planner] = None
        self.progress: Optional[ProgressModule] = None
        self.actor_factory: Optional[ActorFactory] = None
        self._running = False
        self._lock = asyncio.Lock()

        # Validate and store workspace
        self.workspace = os.path.abspath(workspace)
        if not os.path.exists(self.workspace):
            raise ValueError(f"Workspace directory does not exist: {self.workspace}")
        if not os.path.isdir(self.workspace):
            raise ValueError(f"Workspace must be a directory: {self.workspace}")

    async def run(self, goal: str) -> str:
        """
        Run the autonomous agent to achieve a specific goal.

        This is the main entry point method that:
        1. Saves original working directory
        2. Changes to workspace directory
        3. Initializes all components
        4. Starts the actor
        5. Waits until the planner decides the goal is complete
        6. Stops the actor and cleans up resources
        7. Restores original working directory
        8. Returns the final status

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

            logger.info(f"Goal completed: {final_status}")
            return final_status

        finally:
            # Restore original working directory
            try:
                logger.debug(f"Restoring original working directory: {original_cwd}")
                os.chdir(original_cwd)
            except Exception as e:
                logger.error(f"Failed to restore working directory: {e}")

            # Cleanup resources
            logger.debug("Cleaning up resources")
            await self._cleanup()
            logger.info("OpenAime execution stopped")

    async def _initialize_components(self, goal: str) -> None:
        """
        Initialize all components with the given goal.

        Args:
            goal: The overall goal to achieve
        """
        # Create progress module
        self.progress = ProgressModule()

        # Create planner
        self.planner = Planner(self.llm, self.config.planner)
        await self.planner.initialize(goal, self.progress)

        # Create actor factory
        self.actor_factory = ActorFactory(
            base_llm=self.llm,
            actor_config=self.config.actor,
            tool_bundles=self.tool_bundles,
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
                )

                # Run the actor to completion
                result = await actor.run()

                logger.debug(f"Subtask {subtask_id} completed with status: {result.status.value}")

            iteration_count += 1

        return f"Goal not completed within {max_iterations} iterations"

    async def _cleanup(self) -> None:
        """
        Clean up all resources.
        """
        async with self._lock:
            self._running = False

        # All actors are temporary and finish after running, no need to stop
        self.planner = None
        self.progress = None
        self.actor_factory = None

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
