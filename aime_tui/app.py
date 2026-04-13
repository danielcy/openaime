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
from aime_tui.components import EventStream, ProgressPane, ActorPane, InputBox, StatusBar, AskQuestionDialog
from aime.base.events import AimeEvent, EventType
from aime.aime import OpenAime
from aime.base.types import Task, ActorRecord
from aime.base.session import SessionInfo
from aime.base.session_manager import get_default_session_manager
from aime_tui.components.session_list_dialog import SessionListDialog


class AimeTUI(App):
    """
    Main AIME TUI application class that extends Textual's App.

    Provides the complete terminal interface for OpenAime with:
    - Real-time event streaming
    - Task progress visualization
    - Execution status monitoring
    - User input handling
    """

    CSS_PATH = "assets/aime.tcss"

    def __init__(
        self,
        tui_config: TUIConfig,
        openaime: OpenAime,
        initial_goal: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Initialize the AimeTUI application.

        Args:
            tui_config: TUI configuration object
            openaime: OpenAime instance to control and monitor
            initial_goal: Optional goal to run immediately on startup
            **kwargs: Additional keyword arguments passed to textual.app.App
        """
        super().__init__(**kwargs)

        self._config = tui_config
        self._openaime = openaime
        self._initial_goal = initial_goal

        # Set up theme
        custom_theme = get_theme(tui_config.theme)
        # Register the custom theme
        if custom_theme.name not in self.available_themes:
            self.register_theme(custom_theme)
        self.theme = custom_theme.name

        # Components (initialized in compose)
        self._event_stream: Optional[EventStream] = None
        self._progress_pane: Optional[ProgressPane] = None
        self._actor_pane: Optional[ActorPane] = None
        self._input_box: Optional[InputBox] = None
        self._status_bar: Optional[StatusBar] = None

        # Execution tracking
        self._execution_start_time: Optional[datetime] = None
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

        # Main content area - layout depends on configuration
        if self._config.layout == "horizontal":
            with Horizontal():
                self._event_stream = EventStream(self._config, self._openaime.workspace)
                yield self._event_stream
                with Vertical(id="right-sidebar"):
                    self._progress_pane = ProgressPane(self._config)
                    yield self._progress_pane
                    self._actor_pane = ActorPane(self._config)
                    yield self._actor_pane
        else:  # vertical
            with Vertical():
                self._event_stream = EventStream(self._config, self._openaime.workspace)
                self._progress_pane = ProgressPane(self._config)
                self._actor_pane = ActorPane(self._config)
                yield self._event_stream
                yield self._progress_pane
                yield self._actor_pane

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

        # If we have an initial goal, run it after a short delay to let the UI render
        if self._initial_goal is not None:
            import asyncio
            asyncio.create_task(self.run_goal(self._initial_goal))

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

        # Update progress pane when new goal starts (fresh progress module)
        # This ensures we don't keep showing the previous goal's task list
        if self._progress_pane and event.event_type == EventType.PLANNER_GOAL_STARTED:
            self._update_progress_from_event(event)

        # Update actor pane when actors start (actors are created/started)
        if self._actor_pane and event.event_type == EventType.ACTOR_STARTED:
            self._update_actors()

        # Update status bar based on event type
        self._update_status_from_event(event)

        # Handle user question asked event - show dialog
        if event.event_type == EventType.USER_QUESTION_ASKED:
            self._handle_user_question(event)

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

    def _update_actors(self) -> None:
        """
        Update actor pane with the latest list of actors.
        """
        if self._openaime.actor_factory is not None:
            actors = self._openaime.actor_factory.list_actors()
            self.update_actors(actors)

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
            self._execution_start_time = datetime.now()
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
        if self._is_running and self._execution_start_time:
            elapsed = datetime.now() - self._execution_start_time
            self._status_bar.update_elapsed_time(elapsed)

    def _handle_user_input(self, input_text: str) -> None:
        """
        Handle user input from the input box.

        Args:
            input_text: The text submitted by the user
        """
        input_text = input_text.strip()
        if not input_text:
            return

        command = input_text.lower()

        if command in ["quit", "exit", "q"]:
            self.exit()
        elif command in ["/resume", "/sessions"]:
            self._show_session_list_dialog()
            return
        elif command in ["pause", "stop"]:
            # TODO: Implement pause functionality
            pass
        elif self._is_running:
            # Already running, treat this as additional instructions
            # TODO: Handle adding additional instructions
            pass
        else:
            # User input a goal to run - start execution
            import asyncio
            asyncio.create_task(self.run_goal(input_text))

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
        self._execution_start_time = None
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

    def update_actors(self, actors: list[ActorRecord]) -> None:
        """
        Update the actor pane with the latest list of actors.

        Can be called manually to refresh the actors display.

        Args:
            actors: List of all actors to display
        """
        if self._actor_pane:
            self._actor_pane.update_actors(actors)

    def _handle_user_question(self, event: AimeEvent) -> None:
        """
        Handle the USER_QUESTION_ASKED event by pushing the dialog screen.

        Args:
            event: The USER_QUESTION_ASKED event
        """
        question_id = event.data.get("question_id")
        questions = event.data.get("questions", [])

        # Create and push the dialog screen
        dialog = AskQuestionDialog(question_id, questions)
        self.push_screen(dialog)

    def _show_session_list_dialog(self) -> None:
        """Show the session list dialog for user to select a session to load."""
        def on_session_selected(session_id: str) -> None:
            """Callback when a session is selected."""
            self._load_session(session_id)

        dialog = SessionListDialog(on_session_selected)
        self.push_screen(dialog)

    def _load_session(self, session_id: str) -> None:
        """Load a saved session and replay all events to rebuild the UI.

        Args:
            session_id: The session ID to load
        """
        # Load the session into OpenAime
        self._openaime.load_session(session_id)

        # Get the session info with saved events
        session_info = self._openaime.session_manager.get_session_info(session_id)
        if session_info is None or session_info.events is None:
            return

        # Replay all events to rebuild the UI
        # Skip USER_QUESTION_ASKED when replaying - question was already answered in original session
        from aime.base.events import AimeEvent, EventType
        for event_dict in session_info.events:
            event_type = EventType(event_dict["event_type"])
            if event_type == EventType.USER_QUESTION_ASKED:
                continue
            data = event_dict["data"]
            event = AimeEvent(event_type=event_type, data=data)
            self.handle_event(event)

        # Update actors list - actor registry should already be loaded by OpenAime.load_session
        if self._actor_pane and self._openaime.actor_factory:
            actors = self._openaime.actor_factory.list_actors()
            self._actor_pane.update_actors(actors)
