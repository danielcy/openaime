# AIME TUI Terminal Frontend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a terminal UI (TUI) frontend for OpenAime that provides an interactive interface similar to Claude Code, allowing users to interactively run autonomous agents with real-time event streaming, progress viewing, and command interaction.

**Architecture:** The TUI will be built using Textualize/textual (the de facto standard Python TUI framework) with a multi-pane layout: left/top pane for event streaming and conversation, right/bottom pane for progress tracking and task list. The TUI will connect to the OpenAime core via the existing Python API, consuming real-time events through the event callback system we just implemented. All UI updates will be driven by incoming events from the OpenAime execution engine.

**Tech Stack:**
- **Textual**: Python TUI framework (modern, async-native, similar styling to Claude Code's terminal UI)
- **Rich**: For rich text formatting and syntax highlighting
- **OpenAime Core**: Uses existing OpenAime API and event system (no changes to core needed)
- **Python asyncio**: Full async integration with Textual's async event loop

---

## File Structure

```
aime_tui/                      # New TUI package
├── __init__.py                # Package exports
├── app.py                     # Main TUI application class (extends textual.app.App)
├── components/                # Reusable TUI components
│   ├── __init__.py
│   ├── event_stream.py        # Event stream/console output pane
│   ├── progress_pane.py       # Task progress list with status indicators
│   ├── input_box.py           # User input bar at bottom
│   └── status_bar.py          # Status bar showing current execution state
├── theme.py                   # Theme configuration (colors matching Claude Code)
├── config.py                  # TUI configuration options
└── main.py                    # CLI entry point (console script)

tests/
└── aime_tui/                  # Tests for TUI components
    ├── __init__.py
    ├── test_app.py
    └── test_components.py

pyproject.toml                 # Add optional dependency group [tui]
```

---

### Task 1: Project Setup and Dependencies

**Files:**
- Create: `aime_tui/__init__.py`
- Create: `aime_tui/config.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add textual dependency to pyproject.toml**

Add to `pyproject.toml` in the `[project.optional-dependencies]` section:
```toml
tui = [
    "textual>=0.43.0",
    "rich>=13.0.0",
]
```

- [ ] **Step 2: Create TUI configuration class**

```python
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
```

- [ ] **Step 3: Create `__init__.py` with exports**

- [ ] **Step 4: Run dependency check and install**

Run: `pip install -e ".[tui]"`
Expected: Installs textual and rich successfully

- [ ] **Step 5: Commit**

```bash
git add aime_tui/__init__.py aime_tui/config.py pyproject.toml
git commit -m "feat(tui): add tui project structure and dependency config"
```

---

### Task 2: Theme Configuration (Claude Code Inspired)

**Files:**
- Create: `aime_tui/theme.py`

Create a color theme inspired by Claude Code's terminal UI:

Claude Code style reference:
- Background: Dark (almost black) charcoal
- Text: White/light gray for normal text
- Green: For user messages and success
- Blue: For assistant/thinking messages
- Yellow: For warnings
- Red: For errors
- Cyan: For debug/info

- [ ] **Step 1: Write failing test for theme**

```python
# tests/aime_tui/test_theme.py
from aime_tui.theme import get_theme, ClaudeCodeTheme

def test_claude_code_theme():
    theme = get_theme("claude-code")
    assert theme is not None
    assert hasattr(theme, "primary")
    assert hasattr(theme, "background")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/aime_tui/test_theme.py -v`
Expected: FAIL with module not found

- [ ] **Step 3: Implement Claude Code inspired theme**

```python
from textual.app import Theme

CLAUDE_CODE_THEME = Theme(
    name="claude-code",
    primary="#58A6FF",        # GitHub blue - matches Claude's links/accents
    secondary="#3FB950",      # GitHub green - for success
    warning="#D29922",         # GitHub yellow - for warnings
    error="#F85149",          # GitHub red - for errors
    background="#0D1117",     # GitHub dark bg - matches Claude Code dark mode
    surface="#161B22",        # Slightly lighter for widgets
    panel="#21262D",          # Even lighter for panels
    text="#C9D1D9",           # Light gray text
    text-muted="#8B949E",     # Muted gray for secondary text
    accent="#58A6FF",         # Accent blue
)

def get_theme(theme_name: str = "claude-code") -> Theme:
    """Get theme by name."""
    match theme_name:
        case "claude-code":
            return CLAUDE_CODE_THEME
        case _:
            return CLAUDE_CODE_THEME
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/aime_tui/test_theme.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add aime_tui/theme.py tests/aime_tui/test_theme.py
git commit -m "feat(tui): add claude-code inspired color theme"
```

---

### Task 3: TUI Components - Event Stream Pane

**Files:**
- Create: `aime_tui/components/__init__.py`
- Create: `aime_tui/components/event_stream.py`
- Test: `tests/aime_tui/components/test_event_stream.py`

The event stream pane displays real-time events from OpenAime as they happen, similar to Claude Code's output area.

Features:
- Different colors for different event types
- Collapsible sections for tool calls
- Syntax highlighting for code
- Auto-scrolling

- [ ] **Step 1: Write failing test**

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement EventStream component**

The component should:
- Inherit from `textual.widgets.RichLog` or `textual.widgets.Static`
- Have a method `add_event()` that takes an `AimeEvent` and adds it to the log
- Apply correct color based on event type
- Support clearing the log

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

---

### Task 4: TUI Components - Progress Pane

**Files:**
- Create: `aime_tui/components/progress_pane.py`

The progress pane shows a live-updating list of all tasks (from the ProgressModule), with:
- Checkboxes for completed tasks
- Status colors (green = completed, yellow = in progress, red = failed, gray = pending)
- Expandable to show task details and result message
- Similar to the "Plan" section in Claude Code

- [ ] **Step 1: Write failing test**

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement ProgressPane component**

The component should:
- Inherit from `textual.widgets.Tree` or `textual.widgets.Container`
- Have an `update_progress()` method that takes the full progress list
- Update the tree when tasks change status
- Highlight the currently executing task

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

---

### Task 5: TUI Components - Input Box and Status Bar

**Files:**
- Create: `aime_tui/components/input_box.py`
- Create: `aime_tui/components/status_bar.py`

Input box at bottom for:
- Allowing user to pause/resume execution
- Adding additional instructions to the agent
- Interrupting current execution

Status bar shows:
- Current state (idle/running/finished)
- Iteration count
- Elapsed time

- [ ] **Step 1: Write failing tests**

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement components**

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

---

### Task 6: Main TUI Application Class

**Files:**
- Create: `aime_tui/app.py`

Main application class that:
- Extends `textual.app.App`
- Sets up layout with all panes
- Holds the OpenAime instance
- Handles events from OpenAime and routes them to the correct components
- Handles user input from the input box
- Manages async execution of OpenAime

Layout (horizontal orientation):
```
┌─────────────────┬─────────────────┐
│                 │                 │
│   Event Stream  │  Progress Pane  │
│                 │                 │
└─────────────────┴─────────────────┘
└────────────────────────────────────┘
│          Status Bar                │
└────────────────────────────────────┘
└────────────────────────────────────┘
│          Input Box                 │
└────────────────────────────────────┘
```

- [ ] **Step 1: Write failing test**

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement AimeTUI App class**

Key methods:
- `__init__(config, openaime_instance)`
- `compose()` returns all the widgets
- `on_mount()` starts any background tasks
- `handle_event(event)` - callback for OpenAime events, updates UI components
- `run_goal(goal)` - async runs OpenAime with the given goal, updates UI in real-time

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

---

### Task 7: CLI Entry Point

**Files:**
- Create: `aime_tui/main.py`
- Modify: `pyproject.toml`

Add console script `aime-tui` that can be run from the command line.

The CLI should:
- Accept a goal as a command-line argument
- Accept `--workspace` to specify the working directory
- Accept `--config` for configuration
- Load LLM from environment variables (API key)
- Start the TUI app

- [ ] **Step 1: Implement CLI with argparse**

- [ ] **Step 2: Add console script to pyproject.toml**

```toml
[project.scripts]
aime-tui = "aime_tui.main:main"
```

- [ ] **Step 3: Test the CLI**

Run: `aime-tui --help`
Expected: Shows help message

- [ ] **Step 4: Commit**

---

### Task 8: Integration and End-to-End Test

**Files:**
- Create: `tests/aime_tui/test_e2e.py`

Test a complete interaction:
- Mock LLM for testing
- Simple goal like "write hello world"
- Verify all events are displayed correctly
- Verify progress updates work

- [ ] **Step 1: Write end-to-end test**

- [ ] **Step 2: Run test**

- [ ] **Step 3: Fix any integration issues**

- [ ] **Step 4: Verify all tests pass**

- [ ] **Step 5: Commit**

---

### Task 9: Demo File Update

**Files:**
- Modify: `.demo/try_tui.py` (new file)

Create a demo script showing how to use the TUI programmatically:

```python
#!/usr/bin/env python3
"""Demo script showing how to use AIME TUI."""
import asyncio
import os
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.providers.llm.volcengine import VolcengineLLM
from aime.base.tool import Toolkit, ToolBundle
from aime.tools.builtin import Read, ShellExec, Update, Write
from aime_tui.app import AimeTUI
from aime_tui.config import TUIConfig
import asyncio

async def main():
    # Initialize LLM
    llm = VolcengineLLM(
        api_key=os.environ.get("VOLCENGINE_API_KEY"),
        base_url="https://ark.cn-beijing.volces.com/api/coding/v3",
        model="ark-code-latest"
    )

    # Setup tools
    toolkit = Toolkit()
    toolkit.add_bundle(
        ToolBundle(
            name="Default tools",
            description="Default tools",
            tools=[ShellExec(), Read(), Write(), Update()],
        )
    )

    # Create OpenAime
    aime = OpenAime(
        config=AimeConfig(),
        llm=llm,
        toolkit=toolkit,
        workspace=".demo/workspace",
        log_level=None,  # Disable logging since TUI displays everything
    )

    # Create TUI
    tui = AimeTUI(
        openaime=aime,
        config=TUIConfig(
            theme="claude-code",
            layout="horizontal",
            show_debug_events=True,
        )
    )

    # Get goal from user or use default
    goal = input("Enter your goal: ") or "Write a hello world Python program"

    # Run TUI - this will block until done
    await tui.run_goal(goal)

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 1: Create demo file**

- [ ] **Step 2: Commit**

---

## Notes for Implementation

- The TUI **does not** need to change any existing OpenAime core code - it uses the existing public API and event callback system
- All event handling is already implemented in core, TUI just consumes events
- Textual is async-native and integrates well with Python asyncio, so no threading issues
- Claude Code layout is the goal - clean, functional, with a focus on readability
- Keep it simple initially - we can add more features later if needed
