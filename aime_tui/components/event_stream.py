"""Event stream pane component for AIME TUI."""

import json
from typing import Any
from textual.widgets import RichLog
from rich.text import Text
from rich.syntax import Syntax

from aime_tui.config import TUIConfig
from aime.base.events import AimeEvent, EventType

# Constants
HEADER_SEPARATOR_WIDTH = 80


class EventStream(RichLog):
    """Event stream pane that displays real-time events from OpenAime.

    Inherits from Textual's RichLog to provide rich text display,
    auto-scrolling, and efficient line management.
    """

    def __init__(self, config: TUIConfig, workspace: str = "", **kwargs: Any) -> None:
        """Initialize the EventStream.

        Args:
            config: TUI configuration object.
            workspace: Current workspace absolute path.
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
        # Display workspace info at the top if provided
        if workspace:
            self._write_workspace_header(workspace)

    def add_event(self, event: AimeEvent) -> None:
        """Add an AimeEvent to the stream.

        Args:
            event: The event to add to the stream.
        """
        # Skip debug events if configured to do so
        if not self._config.show_debug_events and self._is_debug_event(event):
            return

        # Check if this is a long content event that needs spacing
        is_long_content = self._is_long_content_event(event)

        # Add spacing before long content
        if is_long_content:
            self.write(Text(""))

        # Build the rich text representation of the event
        event_text = self._format_event(event)

        # Add to the log
        self.write(event_text)

        # Add spacing after long content
        if is_long_content:
            self.write(Text(""))

    def _write_workspace_header(self, workspace: str) -> None:
        """Write workspace information header at the top of the event stream.

        Args:
            workspace: Current workspace absolute path.
        """
        content = Text.assemble(
            Text("Workspace: ", style="bold"),
            Text(workspace, style="blue underline"),
            Text("\n"),
            Text("=" * HEADER_SEPARATOR_WIDTH, style="dim"),
            Text("\n\n"),
        )
        self.write(content)

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
        # This method always returns False and serves as a placeholder for
        # future expansion where events may be specifically marked as debug
        return False

    def _is_long_content_event(self, event: AimeEvent) -> bool:
        """Check if an event has long content that needs spacing.

        Args:
            event: The event to check.

        Returns:
            True if the event has long content, False otherwise.
        """
        long_content_types = {
            EventType.PLANNER_THOUGHT,
            EventType.ACTOR_THOUGHT,
            EventType.ACTOR_TOOL_CALLED,
            EventType.ACTOR_TOOL_FINISHED,
        }
        return event.event_type in long_content_types

    def _get_event_emoji(self, event_type: EventType) -> str:
        """Get the appropriate emoji for an event type.

        Args:
            event_type: The type of the event.

        Returns:
            An emoji string.
        """
        emoji_map = {
            # Planner events
            EventType.PLANNER_GOAL_STARTED: "🧠",
            EventType.PLANNER_STEP_STARTED: "🧠",
            EventType.PLANNER_THOUGHT: "🧠",
            EventType.PLANNER_TASK_ADDED: "🧠",
            EventType.PLANNER_TASK_MODIFIED: "🧠",
            EventType.PLANNER_TASK_DELETED: "🧠",
            EventType.PLANNER_TASK_MARKED_FAILED: "❌",
            EventType.PLANNER_TASK_DISPATCHED: "🧠",
            EventType.PLANNER_GOAL_COMPLETED: "✅",
            EventType.PLANNER_GOAL_FAILED: "❌",
            # Actor events
            EventType.ACTOR_STARTED: "🤖",
            EventType.ACTOR_THOUGHT: "🤖",
            EventType.ACTOR_TOOL_CALLED: "🔧",
            EventType.ACTOR_TOOL_FINISHED: "📝",
            EventType.ACTOR_FINISHED: "🤖",
            # Progress/Task events
            EventType.TASK_STATUS_CHANGED: "📊",
            # Overall execution
            EventType.EXECUTION_FINISHED: "✅",
        }
        return emoji_map.get(event_type, "•")

    def _get_event_color(self, event_type: EventType) -> str:
        """Get the appropriate color for an event type.

        Args:
            event_type: The type of the event.

        Returns:
            A rich color string.
        """
        # Check for failure events first
        if "failed" in event_type.value or "FAILED" in event_type.value:
            return "error"

        # Success completion events
        if event_type in {EventType.PLANNER_GOAL_COMPLETED, EventType.EXECUTION_FINISHED}:
            return "success"

        # Tool events
        if event_type == EventType.ACTOR_TOOL_CALLED:
            return "accent"
        if event_type == EventType.ACTOR_TOOL_FINISHED:
            return "accent"

        # Task status change
        if event_type == EventType.TASK_STATUS_CHANGED:
            return "accent"

        # Planner events
        if event_type.value.startswith("planner"):
            return "primary"

        # Actor events
        if event_type.value.startswith("actor"):
            return "secondary"

        return "default"

    def _format_event(self, event: AimeEvent) -> Text:
        """Format an AimeEvent into a rich Text object.

        Args:
            event: The event to format.

        Returns:
            A rich Text object representing the event.
        """
        color = self._get_event_color(event.event_type)
        emoji = self._get_event_emoji(event.event_type)

        # Build the base text with timestamp, emoji and event type
        parts = []

        # Timestamp
        timestamp = event.timestamp.split("T")[1] if "T" in event.timestamp else event.timestamp
        parts.append(Text(f"[{timestamp}] ", style="dim"))

        # Emoji and event type
        event_type_name = event.event_type.value.replace("_", " ").upper()
        parts.append(Text(f"{emoji} {event_type_name}: ", style=f"bold {color}"))

        # Handle different event types with special formatting
        if event.event_type in {EventType.PLANNER_THOUGHT, EventType.ACTOR_THOUGHT}:
            thought_content = self._extract_thought(event)
            if thought_content:
                parts.append(self._format_thought(thought_content))
        elif event.event_type == EventType.ACTOR_TOOL_CALLED:
            tool_content = self._format_tool_call(event)
            parts.extend(tool_content)
        elif event.event_type == EventType.ACTOR_TOOL_FINISHED:
            result_content = self._format_tool_result(event)
            parts.extend(result_content)
        else:
            # Default message formatting
            message = self._extract_message(event)
            if message:
                parts.append(Text(message))

        # Combine all parts
        result = Text.assemble(*parts)
        return result

    def _extract_thought(self, event: AimeEvent) -> str:
        """Extract thought content from an event.

        Args:
            event: The event to extract thought from.

        Returns:
            The thought content string.
        """
        if not event.data:
            return ""
        return event.data.get("thought", "")

    def _format_thought(self, thought: str) -> Text:
        """Format thought content with proper indentation and line breaks.

        Args:
            thought: The raw thought content.

        Returns:
            Formatted Text object.
        """
        if not thought:
            return Text("")

        # Split into lines and indent each line
        lines = thought.split("\n")
        formatted_lines = []
        for i, line in enumerate(lines):
            if i == 0:
                # First line stays on the same line
                formatted_lines.append(line)
            else:
                # Subsequent lines get indentation
                formatted_lines.append(f"  {line}")

        return Text("\n".join(formatted_lines))

    def _format_json(self, data: Any) -> Text | Syntax:
        """Format JSON data with syntax highlighting.

        Args:
            data: The data to format as JSON.

        Returns:
            Formatted Text or Syntax object.
        """
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            return Syntax(json_str, "json", theme="monokai", word_wrap=True)
        except (TypeError, ValueError):
            return Text(str(data))

    def _format_tool_call(self, event: AimeEvent) -> list[Text | Syntax]:
        """Format tool call event with highlighted tool name and parameters.

        Args:
            event: The tool call event.

        Returns:
            List of Text/Syntax objects.
        """
        parts = []

        if not event.data:
            return parts

        # Tool name
        tool_name = event.data.get("tool_name", "unknown")
        parts.append(Text(f"\n  Tool: ", style="bold"))
        parts.append(Text(tool_name, style="bold accent"))

        # Tool arguments
        args = event.data.get("args", {})
        if args:
            parts.append(Text("\n  Args: ", style="bold"))
            if isinstance(args, dict):
                parts.append("\n")
                parts.append(self._format_json(args))
            else:
                parts.append(Text(str(args)))

        return parts

    def _format_tool_result(self, event: AimeEvent) -> list[Text | Syntax]:
        """Format tool result event with syntax highlighting for code/JSON.

        Args:
            event: The tool result event.

        Returns:
            List of Text/Syntax objects.
        """
        parts = []

        if not event.data:
            return parts

        # Tool name
        tool_name = event.data.get("tool_name", "unknown")
        parts.append(Text(f"\n  Tool: ", style="bold"))
        parts.append(Text(tool_name, style="bold accent"))

        # Result
        result = event.data.get("result", "")
        if result:
            parts.append(Text("\n  Result: ", style="bold"))

            # Try to detect and format JSON
            if isinstance(result, (dict, list)):
                parts.append("\n")
                parts.append(self._format_json(result))
            elif isinstance(result, str):
                # Check if string is JSON
                stripped_result = result.strip()
                if (stripped_result.startswith("{") and stripped_result.endswith("}")) or \
                   (stripped_result.startswith("[") and stripped_result.endswith("]")):
                    try:
                        parsed = json.loads(stripped_result)
                        parts.append("\n")
                        parts.append(self._format_json(parsed))
                    except (json.JSONDecodeError, TypeError, ValueError):
                        # Not valid JSON, just add as text with indentation
                        parts.append(self._format_multiline_text(result))
                else:
                    # Regular text, format with indentation
                    parts.append(self._format_multiline_text(result))
            else:
                parts.append(Text(str(result)))

        return parts

    def _format_multiline_text(self, text: str) -> Text:
        """Format multiline text with proper indentation.

        Args:
            text: The raw text.

        Returns:
            Formatted Text object.
        """
        if not text:
            return Text("")

        lines = text.split("\n")
        formatted_lines = []
        for i, line in enumerate(lines):
            if i == 0 and line:
                # First line - if not empty, add space before
                formatted_lines.append(f" {line}")
            elif line:
                # Subsequent non-empty lines get indentation
                formatted_lines.append(f"\n  {line}")

        return Text("".join(formatted_lines))

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
        for field in ["message", "description", "result", "output", "status", "task_id", "task"]:
            if field in event.data and event.data[field]:
                value = event.data[field]
                if isinstance(value, (dict, list)):
                    try:
                        return json.dumps(value, ensure_ascii=False)
                    except (TypeError, ValueError):
                        return str(value)
                return str(value)

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
                if isinstance(value, (dict, list)):
                    try:
                        value_str = json.dumps(value, ensure_ascii=False)
                    except (TypeError, ValueError):
                        value_str = str(value)
                else:
                    value_str = str(value)
                parts.append(f"{key}={value_str}")
        return ", ".join(parts)
