"""
AIME TUI Application - Main Textual User Interface for OpenAime.

Provides a real-time, interactive terminal interface for monitoring and
controlling OpenAime execution. Features include:
- Event stream showing real-time execution events
- Progress pane displaying task hierarchy and status
- Status bar with execution metrics
- Input box for user interaction
"""

from datetime import datetime, timedelta
from typing import Optional
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer

from aime_tui.config import TUIConfig
from aime_tui.theme import get_theme
from aime_tui.components import EventStream, ProgressPane, InputBox, StatusBar
from aime.base.events import AimeEvent, EventType
from aime.aime import OpenAime
from aime.base.types import Task


class AimeTUI(App):
    """
    Main AIME TUI application class that extends Textual's App.

    Provides the complete terminal interface for OpenAime with:
    - Real-time event streaming
    - Task progress visualization
    - Execution status monitoring
    - User input handling
    """

    CSS_PATH = None  # We'll use programmatic styling with themes

    def __init__(
        self,
        tui_config: TUIConfig,
        openaime: OpenAime,
        **kwargs
    ) -> None:
        """
        Initialize the AimeTUI application.

        Args:
            tui_config: TUI configuration object
            openaime: OpenAime instance to control and monitor
            **kwargs: Additional keyword arguments passed to textual.app.App
        """
        super().__init__(**kwargs)

        self._config = tui_config
        self._openaime = openaime

        # Set up theme
        custom_theme = get_theme(tui_config.theme)
        # Register the custom theme
        if custom_theme.name not in self.available_themes:
            self.register_theme(custom_theme)
        self.theme = custom_theme.name

        # Components (initialized in compose)
        self._event_stream: Optional[EventStream] = None
        self._progress_pane: Optional[ProgressPane] = None
        self._input_box: Optional[InputBox] = None
        self._status_bar: Optional[StatusBar] = None

        # Execution tracking
        self._start_time: Optional[datetime] = None
        self._current_iteration: int = 0
        self._is_running: bool = False

        # Register event callback with OpenAime
        self._openaime.event_callback = self.handle_event

    def compose(self) -> ComposeResult:
        """
        Compose the UI layout based on configuration.

        Yields:
            Textual widgets in the correct layout structure
        """
        yield Header()

        # Status bar at the top
        self._status_bar = StatusBar(self._config)
        yield self._status_bar

        # Main content area - layout depends on configuration
        if self._config.layout == "horizontal":
            with Horizontal():
                self._event_stream = EventStream(self._config)
                self._progress_pane = ProgressPane(self._config)
                yield self._event_stream
                yield self._progress_pane
        else:  # vertical
            with Vertical():
                self._event_stream = EventStream(self._config)
                self._progress_pane = ProgressPane(self._config)
                yield self._event_stream
                yield self._progress_pane

        # Input box at the bottom
        self._input_box = InputBox(
            self._config,
            on_submit=self._handle_user_input
        )
        yield self._input_box

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is ready and mounted."""
        self.title = "AIME - Autonomous Interactive Execution Engine"
        self.sub_title = "Monitoring OpenAime Execution"

    def handle_event(self, event: AimeEvent) -> None:
        """
        Handle events from OpenAime and update the UI accordingly.

        This is the callback registered with OpenAime to receive real-time
        events during execution.

        Args:
            event: The AimeEvent from OpenAime
        """
        # Update event stream
        if self._event_stream:
            self._event_stream.add_event(event)

        # Update progress pane on task status changes
        if self._progress_pane and event.event_type == EventType.TASK_STATUS_CHANGED:
            self._update_progress_from_event(event)

        # Update status bar based on event type
        self._update_status_from_event(event)

    def _update_progress_from_event(self, event: AimeEvent) -> None:
        """
        Update progress pane from a TASK_STATUS_CHANGED event.

        Args:
            event: The TASK_STATUS_CHANGED event
        """
        # Get tasks from OpenAime's progress module
        if self._openaime.progress:
            # Since this is a sync method, create an async task to update progress
            async def update_progress_async():
                tasks = await self._openaime.progress.get_all_tasks()
                self.update_progress(tasks)

            import asyncio
            asyncio.create_task(update_progress_async())

    def _update_status_from_event(self, event: AimeEvent) -> None:
        """
        Update status bar based on event type.

        Args:
            event: The event to process
        """
        if not self._status_bar:
            return

        # Track execution start
        if event.event_type == EventType.PLANNER_GOAL_STARTED:
            self._start_time = datetime.now()
            self._is_running = True
            self._status_bar.update_state("running")
            self._status_bar.update_iteration(0)

        # Track iteration (increment on planner step)
        elif event.event_type == EventType.PLANNER_STEP_STARTED:
            self._current_iteration += 1
            self._status_bar.update_iteration(self._current_iteration)

        # Track completion
        elif event.event_type == EventType.EXECUTION_FINISHED:
            self._is_running = False
            self._status_bar.update_state("finished")

        # Update elapsed time on any event when running
        if self._is_running and self._start_time:
            elapsed = datetime.now() - self._start_time
            self._status_bar.update_elapsed_time(elapsed)

    def _handle_user_input(self, input_text: str) -> None:
        """
        Handle user input from the input box.

        Args:
            input_text: The text submitted by the user
        """
        command = input_text.strip().lower()

        if command in ["quit", "exit", "q"]:
            self.exit()
        elif command in ["pause", "stop"]:
            # TODO: Implement pause functionality
            pass
        elif command in ["resume", "start"]:
            # TODO: Implement resume functionality
            pass
        else:
            # TODO: Handle other inputs like adding instructions
            pass

    async def run_goal(self, goal: str) -> str:
        """
        Run OpenAime with the given goal and update the UI in real-time.

        This method starts the OpenAime execution and monitors it through
        the event callback system.

        Args:
            goal: The goal to achieve

        Returns:
            The final result from OpenAime
        """
        # Reset state
        self._current_iteration = 0
        self._start_time = None
        self._is_running = False

        # Run OpenAime
        result = await self._openaime.run(goal)

        return result

    def update_progress(self, tasks: list[Task]) -> None:
        """
        Update the progress pane with the latest task list.

        Can be called manually to refresh the progress display.

        Args:
            tasks: List of all tasks to display
        """
        if self._progress_pane:
            self._progress_pane.update_progress(tasks)
