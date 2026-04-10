"""Event stream pane component for AIME TUI."""

from typing import Any
from textual.widgets import RichLog
from rich.text import Text
from rich.syntax import Syntax

from aime_tui.config import TUIConfig
from aime.base.events import AimeEvent, EventType


class EventStream(RichLog):
    """Event stream pane that displays real-time events from OpenAime.

    Inherits from Textual's RichLog to provide rich text display,
    auto-scrolling, and efficient line management.
    """

    def __init__(self, config: TUIConfig, **kwargs: Any) -> None:
        """Initialize the EventStream.

        Args:
            config: TUI configuration object.
            **kwargs: Additional keyword arguments passed to RichLog.
        """
        super().__init__(
            highlight=True,
            markup=True,
            auto_scroll=config.auto_scroll,
            max_lines=config.max_event_lines,
            **kwargs
        )
        self._config = config
        self._auto_scroll = config.auto_scroll

    def add_event(self, event: AimeEvent) -> None:
        """Add an AimeEvent to the stream.

        Args:
            event: The event to add to the stream.
        """
        # Skip debug events if configured to do so
        if not self._config.show_debug_events and self._is_debug_event(event):
            return

        # Build the rich text representation of the event
        event_text = self._format_event(event)

        # Add to the log
        self.write(event_text)

    def clear(self) -> None:
        """Clear all events from the stream."""
        super().clear()

    def _is_debug_event(self, event: AimeEvent) -> bool:
        """Check if an event is a debug event.

        Args:
            event: The event to check.

        Returns:
            True if the event is a debug event, False otherwise.
        """
        # Currently, no events are specifically marked as debug
        # This is a placeholder for future expansion
        return False

    def _get_event_color(self, event_type: EventType) -> str:
        """Get the appropriate color for an event type.

        Args:
            event_type: The type of the event.

        Returns:
            A rich color string.
        """
        if event_type.value.startswith("planner"):
            return "primary"
        elif event_type.value.startswith("actor"):
            return "secondary"
        elif event_type == EventType.EXECUTION_FINISHED:
            return "success"
        elif event_type == EventType.TASK_STATUS_CHANGED:
            return "info"
        else:
            return "default"

    def _format_event(self, event: AimeEvent) -> Text:
        """Format an AimeEvent into a rich Text object.

        Args:
            event: The event to format.

        Returns:
            A rich Text object representing the event.
        """
        color = self._get_event_color(event.event_type)

        # Build the base text with timestamp and event type
        parts = []

        # Timestamp
        timestamp = event.timestamp.split("T")[1] if "T" in event.timestamp else event.timestamp
        parts.append(Text(f"[{timestamp}] ", style="dim"))

        # Event type
        event_type_name = event.event_type.value.replace("_", " ").upper()
        parts.append(Text(f"{event_type_name}: ", style=f"bold {color}"))

        # Message or data
        message = self._extract_message(event)
        if message:
            parts.append(Text(message))

        # Combine all parts
        result = Text.assemble(*parts)
        return result

    def _extract_message(self, event: AimeEvent) -> str:
        """Extract a human-readable message from an event.

        Args:
            event: The event to extract a message from.

        Returns:
            A human-readable message string.
        """
        if not event.data:
            return ""

        # Try common message fields first
        for field in ["message", "description", "thought", "result", "output"]:
            if field in event.data and event.data[field]:
                return str(event.data[field])

        # If no specific message field, format the data
        return self._format_data(event.data)

    def _format_data(self, data: dict[str, Any]) -> str:
        """Format event data into a readable string.

        Args:
            data: The event data dictionary.

        Returns:
            A formatted string representation of the data.
        """
        # For simple data, just join key-value pairs
        parts = []
        for key, value in data.items():
            if value is not None and value != "":
                parts.append(f"{key}={value}")
        return ", ".join(parts)
