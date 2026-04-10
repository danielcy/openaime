from dataclasses import dataclass, field
from typing import Optional, Literal


@dataclass
class TUIConfig:
    """Configuration for the AIME TUI frontend."""

    # Theme - currently only supports Claude Code inspired theme
    theme: Literal["claude-code", "monokai", "default"] = "claude-code"

    # Whether to show verbose debug events in the event stream
    show_debug_events: bool = False

    # Auto-scroll event stream to bottom on new events
    auto_scroll: bool = True

    # Pane layout - "horizontal" (event left, progress right) or "vertical" (event top, progress bottom)
    layout: Literal["horizontal", "vertical"] = "horizontal"

    # Maximum lines to keep in event stream buffer
    max_event_lines: int = 10000
