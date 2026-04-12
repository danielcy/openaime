"""Status bar component for AIME TUI."""

from typing import Any
from datetime import timedelta
from textual.widgets import Static
from rich.text import Text

from aime_tui.config import TUIConfig


class StatusBar(Static):
    """Status bar that displays current execution state and metrics.

    Shows:
    - Current state (idle/running/finished)
    - Iteration count
    - Elapsed time since execution started
    - Workspace path

    Inherits from Textual's Static widget.
    """

    def __init__(self, config: TUIConfig, workspace: str, **kwargs: Any) -> None:
        """Initialize the StatusBar.

        Args:
            config: TUI configuration object.
            workspace: Current workspace absolute path.
            **kwargs: Additional keyword arguments passed to Static.
        """
        super().__init__(**kwargs)
        self._config = config
        self._workspace = workspace
        self._state = "idle"
        self._iteration = 0
        self._elapsed_time = timedelta(seconds=0)

    def update_state(self, state: str) -> None:
        """Update the current execution state.

        Args:
            state: New state (idle/running/finished).
        """
        self._state = state
        self._update_display()

    def update_iteration(self, iteration: int) -> None:
        """Update the iteration count.

        Args:
            iteration: Current iteration number.
        """
        self._iteration = iteration
        self._update_display()

    def update_elapsed_time(self, elapsed: timedelta) -> None:
        """Update the elapsed time since execution started.

        Args:
            elapsed: Timedelta representing elapsed time.
        """
        self._elapsed_time = elapsed
        self._update_display()

    def _update_display(self) -> None:
        """Update the status bar display with current values.

        Handles case where no active Textual app context is available (e.g., in tests).
        """
        # Build rich text with appropriate colors and styles
        parts = []

        # State indicator with color
        state_text = self._get_state_text()
        parts.append(state_text)
        parts.append(Text(" | "))

        # Iteration count
        parts.append(Text(f"Iteration: {self._iteration}"))
        parts.append(Text(" | "))

        # Elapsed time
        time_str = self._format_elapsed_time()
        parts.append(Text(f"Elapsed: {time_str}"))
        parts.append(Text(" | "))

        # Workspace path (rightmost)
        parts.append(Text(f"Workspace: {self._workspace}", style="dim"))

        # Try to update the widget, but handle case where no app is active (testing)
        try:
            self.update(Text.assemble(*parts))
        except Exception:  # noqa: B001
            pass

    def _get_state_text(self) -> Text:
        """Get styled state text based on current state.

        Returns:
            Rich Text object with appropriate style.
        """
        if self._state == "running":
            return Text(f"State: {self._state.upper()}", style="bold warning")
        elif self._state == "finished":
            return Text(f"State: {self._state.upper()}", style="bold success")
        elif self._state == "idle":
            return Text(f"State: {self._state.upper()}", style="bold info")
        else:
            return Text(f"State: {self._state.upper()}")

    def _format_elapsed_time(self) -> str:
        """Format elapsed time as HH:MM:SS.

        Returns:
            Formatted time string.
        """
        total_seconds = int(self._elapsed_time.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
