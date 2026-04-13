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

        # Completely skip these planner events to reduce noise
        if event.event_type in {
            EventType.PLANNER_STEP_STARTED,
            EventType.PLANNER_THOUGHT,
            EventType.PLANNER_TASK_DISPATCHED,
        }:
            return

        # For events that have special formatting with integrated emoji,
        # output timestamp directly with the first line of content on the same line
        events_with_inline_header = {
            EventType.ACTOR_TOOL_CALLED,
            EventType.ACTOR_TOOL_FINISHED,
            EventType.ACTOR_STARTED,
            EventType.ACTOR_THOUGHT,
        }

        if event.event_type in events_with_inline_header:
            # Get just the timestamp part (no event name)
            timestamp_text = self._format_timestamp(event)
            # Write timestamp + content on the same line
            self._write_special_content_with_prefix(event, timestamp_text)
        else:
            # Write the header (timestamp, emoji, event type)
            header_text = self._format_header(event)
            self.write(header_text)
            # Handle special formatting that may contain Syntax objects
            # No extra spacing inside the same event
            self._write_special_content(event)

        # Always add a blank line after each event for consistent spacing between events
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
            EventType.ACTOR_STARTED,
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
            EventType.ACTOR_SKILL_LOADED: "🎯",
            # Progress/Task events
            EventType.TASK_STATUS_CHANGED: "📊",
            # Overall execution
            EventType.EXECUTION_FINISHED: "✅",
            EventType.GOAL_SUMMARY_GENERATED: "📝",
            # User interaction events
            EventType.USER_QUESTION_ASKED: "❓",
            EventType.USER_QUESTION_ANSWERED: "💬",
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

        # User interaction events
        if event_type in {EventType.USER_QUESTION_ASKED, EventType.USER_QUESTION_ANSWERED}:
            return "accent"

        # Planner events
        if event_type.value.startswith("planner"):
            return "primary"

        # Actor events
        if event_type.value.startswith("actor"):
            return "secondary"

        return "default"

    def _format_timestamp(self, event: AimeEvent) -> Text:
        """Format just the timestamp part.

        Args:
            event: The event to format.

        Returns:
            Text object containing only the timestamp with trailing space.
        """
        # Timestamp - keep only HH:mm:ss, drop milliseconds
        timestamp = event.timestamp.split("T")[1] if "T" in event.timestamp else event.timestamp
        timestamp = timestamp.split(".")[0]  # Drop milliseconds
        return Text(f"[{timestamp}] ", style="dim")

    def _format_header(self, event: AimeEvent) -> Text:
        """Format the header line with timestamp, emoji, and event type.

        Args:
            event: The event to format.

        Returns:
            Text object containing the header.
        """
        color = self._get_event_color(event.event_type)
        emoji = self._get_event_emoji(event.event_type)

        # Build the header
        parts = []

        parts.append(self._format_timestamp(event))

        # For events that have their own special formatting in the content,
        # don't display event type name here since it's already included
        if event.event_type not in {
            EventType.ACTOR_TOOL_CALLED,
            EventType.ACTOR_TOOL_FINISHED,
            EventType.ACTOR_STARTED,
            EventType.ACTOR_THOUGHT,
        }:
            # Emoji and event type
            event_type_name = event.event_type.value.replace("_", " ").upper()
            parts.append(Text(f"{emoji} {event_type_name}: ", style=f"bold {color}"))

        return Text.assemble(*parts)

    def _write_special_content_with_prefix(self, event: AimeEvent, prefix: Text) -> None:
        """Write special content with timestamp prefix on the first line.

        Args:
            event: The event containing special content.
            prefix: Timestamp prefix to put on the first line.
        """
        if event.event_type == EventType.ACTOR_TOOL_CALLED:
            parts = self._format_tool_call(event)
            if parts:
                # Prepend timestamp to first part
                if isinstance(parts[0], Text) and parts[0].plain == "":
                    # Remove the empty first line we add for spacing
                    parts = parts[1:]
                if parts:
                    parts[0] = Text.assemble(prefix, parts[0])
            for part in parts:
                self.write(part)
        elif event.event_type == EventType.ACTOR_TOOL_FINISHED:
            parts = self._format_tool_result(event)
            if parts:
                # Remove the empty first line we add for spacing
                if isinstance(parts[0], Text) and parts[0].plain == "":
                    parts = parts[1:]
                if parts:
                    parts[0] = Text.assemble(prefix, parts[0])
            for part in parts:
                self.write(part)
        elif event.event_type == EventType.ACTOR_STARTED:
            content = self._format_actor_started(event)
            if content:
                # Insert timestamp at beginning
                full_content = Text.assemble(prefix, content)
                self.write(full_content)
        elif event.event_type == EventType.ACTOR_THOUGHT:
            thought_content = self._extract_thought(event)
            if thought_content:
                formatted = self._format_actor_thought(thought_content)
                # Insert timestamp at beginning
                full_content = Text.assemble(prefix, formatted)
                self.write(full_content)

    def _write_special_content(self, event: AimeEvent) -> None:
        """Write special content that may contain Syntax objects.

        Since Text.assemble cannot mix Text and Syntax objects, we write
        special content separately after the header.

        Args:
            event: The event containing special content.
        """
        # Handle different event types with special formatting
        if event.event_type == EventType.ACTOR_STARTED:
            content = self._format_actor_started(event)
            if content:
                self.write(content)
        elif event.event_type == EventType.ACTOR_SKILL_LOADED:
            content = self._format_actor_skill_loaded(event)
            if content:
                self.write(content)
        elif event.event_type == EventType.ACTOR_THOUGHT:
            thought_content = self._extract_thought(event)
            if thought_content:
                formatted = self._format_actor_thought(thought_content)
                self.write(formatted)
        elif event.event_type in {EventType.PLANNER_THOUGHT, EventType.PLANNER_STEP_STARTED, EventType.PLANNER_TASK_DISPATCHED}:
            # These are completely skipped in add_event
            pass
        elif event.event_type == EventType.ACTOR_TOOL_CALLED:
            for part in self._format_tool_call(event):
                self.write(part)
        elif event.event_type == EventType.ACTOR_TOOL_FINISHED:
            for part in self._format_tool_result(event):
                self.write(part)
        else:
            # Default message formatting
            message = self._extract_message(event)
            if message:
                self.write(Text(message))

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

    def _format_actor_started(self, event: AimeEvent) -> Text:
        """Format actor started event with role display.

        Args:
            event: The actor started event.

        Returns:
            Formatted Text object.
        """
        if not event.data:
            return Text("")

        role = event.data.get("role", "")
        if not role:
            return Text("")

        # Truncate to max 100 characters
        if len(role) > 100:
            role = role[:97] + "..."

        # Format: 🤖 Actor Launched:
        #         {role}
        return Text(f"🤖 Actor Launched:\n  {role}", style="bold secondary")

    def _format_actor_skill_loaded(self, event: AimeEvent) -> Text:
        """Format actor skill loaded event with loaded skill names.

        Args:
            event: The actor skill loaded event.

        Returns:
            Formatted Text object.
        """
        if not event.data:
            return Text("")

        skills = event.data.get("skills", [])
        if not skills:
            return Text("")

        # Format: 🎯 Skills loaded: skill1, skill2, skill3
        skills_str = ", ".join(skills)
        return Text(f"🎯 Skills: {skills_str}", style="bold secondary")

    def _format_actor_thought(self, thought: str) -> Text:
        """Format actor thought with special handling for THOUGHT/ACTION format.

        Args:
            thought: The raw thought content.

        Returns:
            Formatted Text object.
        """
        if not thought:
            return Text("")

        # Check if it matches THOUGHT: ... ACTION: ... format
        lines = thought.split("\n")
        thought_line = None
        action_line = None

        # Look for lines starting with THOUGHT: and ACTION:
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("thought:"):
                thought_line = stripped[len("thought:"):].strip()
            elif stripped.lower().startswith("action:"):
                action_line = stripped[len("action:"):].strip()

        if thought_line is not None and action_line is not None:
            # Found the expected format - use special emoji formatting
            return Text.assemble(
                Text("🤖 ", style="bold secondary"),
                Text(thought_line + "\n"),
                Text("👊🏻 ", style="bold accent"),
                Text(action_line),
            )
        else:
            # Default format - just display with emoji prefix
            return Text("🤖 " + thought, style="secondary")

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
        parameters = event.data.get("parameters", {})

        # Format: 🔧{tool_name}
        #         {parameters truncated to 100 chars}
        parts.append(Text(f"🔧{tool_name}", style="bold accent"))

        if parameters:
            # Convert to json string
            try:
                json_str = json.dumps(parameters, ensure_ascii=False)
                # Truncate to max 100 characters
                if len(json_str) > 100:
                    json_str = json_str[:97] + "..."
                parts.append(self._format_multiline_text(json_str))
            except Exception:
                # Fallback to string representation
                str_val = str(parameters)
                if len(str_val) > 100:
                    str_val = str_val[:97] + "..."
                parts.append(Text(str_val))

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
        result = event.data.get("content", "")

        # Format: 📝{tool_name}
        #         {result truncated to 200 chars}
        parts.append(Text(f"📝{tool_name}", style="bold accent"))

        if result:
            # Truncate to max 200 characters
            result_str = str(result)
            if len(result_str) > 200:
                result_str = result_str[:197] + "..."
            parts.append(self._format_multiline_text(result_str))

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
