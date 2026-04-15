# OpenAime

[中文版](./README_zh.md) | English

Open-Source implementation of the **AIME (Autonomous Interactive Execution Engine)** framework for LLM-based autonomous software engineering agents.

## What is AIME

AIME is a multi-agent autonomous execution architecture described in the [AIME paper](https://arxiv.org/abs/2506.1234), designed to enable fully autonomous AI agents to complete complex software engineering tasks such as:

- Debugging and fixing bugs in existing codebases
- Implementing new features from requirements
- Refactoring and improving code quality
- Code review and analysis
- Whole-project development from scratch

The core idea is **dynamic planning + specialized actor execution**:
- **Planner**: Continuously plans and re-plans tasks based on current progress
- **Actor Factory**: Creates or reuses specialized actors for different subtasks based on required capabilities
- **Progress Module**: Centralized progress tracking with real-time updates
- **Native Tool Calling**: Leverages LLM provider's native function calling for reliability

## Differences from Claude Code

| Feature | OpenAime | Claude Code |
|---------|----------|-------------|
| **Architecture** | Planner + Actor + Progress Module - dynamic task planning with parallel actor execution | Sequential tool execution |
| **Language** | Python | TypeScript |
| **Embeddable** | Can be imported as Python package and integrated into any application | Standalone CLI only |
| **Actor Reuse** | Automatically reuse existing actors with matching capabilities | Creates new context per turn |
| **Dynamic Task Management** | Supports add/modify/delete tasks during execution | Fixed single-turn planning |
| **Session Persistence** | Full session save/load, can resume work later | No built-in persistence |
| **MCP Support** | Full MCP (Model Context Protocol) tool integration | MCP support |
| **TUI** | Built-in terminal UI with real-time progress tracking | Built-in terminal UI |

## Features

- ✅ **Dynamic Planner**: Continuous planning with dynamic task manipulation (add/modify/delete/mark failed)
- ✅ **Actor Reuse**: Capability-based actor reuse avoids repeated work
- ✅ **Prevent Duplicate Work**: Full progress context visible to all actors
- ✅ **Native Function Calling**: Pure native tool calling eliminates JSON parsing errors
- ✅ **Multiple LLM Providers**: OpenAI, Anthropic, Volcengine (Doubao) all supported
- ✅ **MCP Integration**: Full MCP (Model Context Protocol) client support
- ✅ **Interactive User Questions**: Actors can prompt users for decisions via TUI dialog
- ✅ **Session Persistence**: Save full session to disk, resume anytime
- ✅ **Beautiful TUI**: Real-time event stream, progress tree, incremental output
- ✅ **Skills System**: Modular capability extension with hot-reload
- ✅ **Workspace Isolation**: Proper working directory management

## Quick Start

### Installation

```bash
pip install openaime
# Or with uv
uv add openaime
```

### Install optional TUI dependencies:
```bash
pip install openaime[tui]
```

### Basic Usage

```python
import asyncio
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.providers.llm.anthropic import AnthropicLLM

# Create your LLM provider
llm = AnthropicLLM(api_key="your-api-key-here")

# Create OpenAime instance
aime = OpenAime(
    config=AimeConfig(),
    llm=llm,
    workspace="./your-project-directory"
)

# Run autonomous agent to achieve your goal
result = await aime.run("Fix the bug in the login module")
print(result)
```

### Multi-turn Conversation

```python
# First request
result1 = await aime.run("Add a login endpoint to app.py")
print(result1)

# Second request - retains full context!
result2 = await aime.run("Now add JWT authentication to this endpoint")
print(result2)

# Start fresh if needed
aime.clear_session()
result3 = await aime.run("A completely new task here", new_goal=True)
```

## Integrate into Your Own Application

OpenAime is designed as a library that you can embed into your own Python application. You can listen to events for UI integration or logging.

```python
import asyncio
import logging
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.base.events import EventType, AimeEvent
from aime.providers.llm.openai import OpenAILLM

def my_event_callback(event: AimeEvent):
    """Custom event callback to handle events from OpenAime."""
    event_type = event.event_type
    data = event.data

    if event_type == EventType.ACTOR_INCREMENTAL_OUTPUT:
        # Handle streaming thought output
        actor_name = data.get("actor_name", "")
        text = data.get("text", "")
        full_text = data.get("full_text_so_far", "")
        print(f"[{actor_name}] {text}")  # Update UI incrementally

    elif event_type == EventType.ACTOR_TOOL_CALLED:
        # Actor called a tool
        logging.info(f"Tool called: {data.get('tool_name')}")

    elif event_type == EventType.TASK_STATUS_CHANGED:
        # Task status updated
        pass

llm = OpenAILLM(api_key="your-api-key")
aime = OpenAime(
    config=AimeConfig(),
    llm=llm,
    workspace="./workspace",
    event_callback=my_event_callback,
)

result = await aime.run("Implement a simple Python HTTP server")
```

## Supported Events

| Event Type | Description | Data Fields |
|------------|-------------|-------------|
| `PLANNER_GOAL_STARTED` | Planner started working on a new goal | None |
| `PLANNER_STEP_COMPLETED` | Planner completed one planning step | `action`, `thought` |
| `ACTOR_STARTED` | Actor started executing a subtask | `actor_id`, `actor_name`, `task_description` |
| `ACTOR_INCREMENTAL_OUTPUT` | Incremental thought output from actor (streaming) | `actor_id`, `actor_name`, `text`, `full_text_so_far` |
| `ACTOR_THOUGHT` | Full actor thought (non-streaming) | `actor_id`, `actor_name`, `thought` |
| `ACTOR_TOOL_CALLED` | Actor called a tool | `actor_id`, `tool_name`, `parameters` |
| `ACTOR_TOOL_FINISHED` | Actor tool execution finished | `actor_id`, `tool_name`, `success`, `content` |
| `ACTOR_COMPLETED` | Actor finished subtask execution | `actor_id`, `result` |
| `TASK_STATUS_CHANGED` | Task status changed (pending → in_progress → completed/failed) | `task_id`, `status` |
| `GOAL_COMPLETED` | Overall goal completed | `summary`, `total_iterations` |
| `USER_QUESTION_ASKED` | Actor asked a user question | `question` |
| `USER_QUESTION_ANSWERED` | User answered the question | `answers` |

## TUI Usage

OpenAime includes an interactive terminal UI when used from the command line:

```bash
# After installation, launch TUI:
openaime
```

### Commands

| Command | Description |
|---------|-------------|
| `/goal <description>` | Start a new autonomous goal execution |
| `/clear` | Clear current session |
| `/sessions` | List saved sessions, click to resume |
| `/layout horizontal` / `layout vertical` | Switch layout |
| `/quit` | Exit TUI |

## Project Structure

```
aime/
├── base/                      # Base abstractions and type definitions
│   ├── llm.py                # LLM base interface (BaseLLM)
│   ├── types.py              # Core dataclasses (Task, ProgressList, ActorRecord, etc.)
│   ├── tool.py               # Tool base interface (BaseTool, Toolkit, ToolBundle)
│   ├── config.py             # Configuration classes
│   ├── skill.py              # Skill metadata and registry (hot-reload)
│   ├── knowledge.py          # Knowledge base abstraction
│   ├── user_question.py      # User question manager for interactive prompts
│   └── session/              # Session persistence
├── components/               # Core business components
│   ├── actor.py              # DynamicActor with ReAct streaming loop
│   ├── actor_factory.py      # ActorFactory with capability-based actor reuse
│   ├── planner.py            # Dynamic planner with task mutation support
│   └── progress_module.py    # Progress tracking and event subscription
├── providers/                # Provider implementations
│   ├── llm/                  # LLM providers
│   │   ├── openai.py         # OpenAI (GPT-4o, etc.)
│   │   ├── anthropic.py      # Anthropic (Claude 3.5/3.7)
│   │   └── volcengine.py     # Volcengine Doubao
│   └── tools/                # Tool providers
│       └── mcp.py            # MCP (Model Context Protocol) client
├── tools/                    # Builtin tools
│   └── builtin/              # Core builtin tools
│       ├── file_read.py      # Read text files
│       ├── file_write.py     # Write text files
│       ├── file_update.py    # Update existing files (search/replace, append)
│       ├── shell_exec.py     # Execute shell commands
│       └── ask_user_question.py # Ask user interactive questions
├── aime.py                   # Main OpenAime entry point
└── aime_tui/                 # Terminal User Interface
    ├── app.py               # Main TUI application
    ├── components/          # TUI components (EventStream, ProgressPane, etc.)
    ├── assets/              # CSS styles
    └── config.py            # TUI configuration
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Based on the AIME architecture described in the AIME paper.
