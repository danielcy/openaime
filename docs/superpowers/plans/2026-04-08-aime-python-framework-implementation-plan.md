# Aime Python 框架实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现论文 "AIME: TOWARDS FULLY-AUTONOMOUS MULTI-AGENT FRAMEWORK" 描述的完整Python版本Aime框架，基于asyncio Actor并发模式，生产可用，支持多LLM提供商和MCP工具调用。

**Architecture:** 采用分层模块化架构，基于 asyncio Actor 并发模型。核心四大组件：DynamicPlanner（动态规划器）、ActorFactory（Actor工厂）、DynamicActor（动态执行Actor）、ProgressManagementModule（集中式进度管理模块）。抽象接口层支持多LLM提供商，工具系统支持工具捆绑包和MCP兼容。

**Tech Stack:** Python 3.13+, asyncio, pydantic, openai, anthropic, rich, pytest, mcp

**Related Documents:**
- 设计文档: `docs/superpowers/specs/2026-04-08-aime-python-framework-design.md`
- 论文翻译: `aime_zh.md`

---

## 项目初始化

### Task 0: 项目配置和目录结构初始化

**Files:**
- Create: `.gitignore`
- Modify: `pyproject.toml` (update dependencies)
- Create: `aime/__init__.py`
- Create: `aime/_version.py`
- Create: `aime/base/__init__.py`
- Create: `aime/components/__init__.py`
- Create: `aime/providers/__init__.py`
- Create: `aime/tools/__init__.py`
- Create: `aime/tools/builtin/__init__.py`
- Create: `aime/io/__init__.py`
- Create: `aime/templates/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/base/__init__.py`
- Create: `tests/components/__init__.py`
- Create: `tests/providers/__init__.py`
- Create: `tests/tools/__init__.py`
- Create: `tests/io/__init__.py`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
*.manifest
*.spec

# Virtual environment
.venv/
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment variables
.env
.env.local
*.env

# API keys and secrets
*api-key*
*secret*

# Coverage
.htmlcov
.coverage
.coverage.*
.pytest_cache/

# Jupyter
.ipynb_checkpoints/
```

- [ ] **Step 2: Update pyproject.toml with all dependencies**

```python
[project]
name = "aime"
version = "0.1.0"
description = "Aime: Fully-autonomous Multi-agent Framework"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "pydantic>=2.0",
    "openai>=1.0",
    "anthropic>=0.40",
    "rich>=13.0",
    "aiofiles>=23.0",
    "mcp>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "black>=24.0",
    "ruff>=0.5",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-v"
```

- [ ] **Step 3: Create all subdirectory __init__.py files**

```python
# aime/base/__init__.py
from .types import *
from .llm import *
from .tool import *
from .config import *

__all__ = [
    # types
    "TaskStatus", "Task", "ArtifactReference", "TaskUpdate", "ProgressList",
    # llm
    "BaseLLM", "Message", "ToolCall", "LLMResponse", "LLMResponseChunk",
    # tool
    "BaseTool", "ToolResult", "ToolBundle", "Toolkit",
    # config
    "AimeConfig", "PlannerConfig", "ActorConfig",
]
```

Other `__init__.py` files are empty for now.

- [ ] **Step 4: Create main __init__.py and _version.py**

- [ ] **Step 5: Create pytest configuration**

- [ ] **Step 6: Install dependencies**

```bash
pip install -e ".[dev]"
```

- [ ] **Step 7: Run empty test suite verify configuration**

```bash
pytest tests/ -v
```

Expected: no tests collected (OK)

- [ ] **Step 8: Commit**

```bash
git add .gitignore pyproject.toml aime/**/__init__.py tests/**/__init__.py aime/_version.py tests/conftest.py
git commit -m "chore: initialize project structure and directories"
```

---

## Stage 1: 基础抽象层（所有依赖从此开始）

### Task 1: 配置类定义 (base/config.py)

**Files:**
- Create: `aime/base/config.py`
- Create: `tests/base/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/base/test_config.py
import pytest
from aime.base.config import AimeConfig, PlannerConfig, ActorConfig

def test_aime_config_defaults():
    config = AimeConfig()
    assert config.max_iterations > 0
    assert config.temperature > 0

def test_planner_config():
    config = PlannerConfig()
    assert config.allow_replan_on_failure is True
```

- [ ] **Step 2: Run test - verify it fails**

```bash
pytest tests/base/test_config.py -v
```

Expected: FAIL (module not found)

- [ ] **Step 3: Implement configuration dataclasses**

```python
# aime/base/config.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PlannerConfig:
    max_iterations: int = 100
    temperature: float = 0.7
    allow_replan_on_failure: bool = True
    max_retries_on_failure: int = 3

@dataclass
class ActorConfig:
    temperature: float = 0.7
    max_iterations: int = 50
    enable_auto_progress_update: bool = True

@dataclass
class KnowledgeConfig:
    enable_retrieval: bool = True
    top_k: int = 3

@dataclass
class AimeConfig:
    planner: PlannerConfig = field(default_factory=PlannerConfig)
    actor: ActorConfig = field(default_factory=ActorConfig)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    max_total_iterations: int = 200
```

- [ ] **Step 4: Run test - verify it passes**

```bash
pytest tests/base/test_config.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add aime/base/config.py tests/base/test_config.py
git commit -m "feat: base configuration classes"
```

### Task 2: 基础类型定义 (base/types.py)

**Files:**
- Create: `aime/base/types.py`
- Create: `tests/base/test_types.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/base/test_types.py
import pytest
from aime.base.types import TaskStatus, Task, ArtifactReference, ProgressList

def test_task_status_enum():
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.IN_PROGRESS == "in_progress"

def test_task_creation():
    task = Task(
        id="test-1",
        description="Test task",
        status=TaskStatus.PENDING,
        parent_id=None,
        completion_criteria="Complete the test",
        dependencies=[],
    )
    assert task.id == "test-1"
    assert task.status == TaskStatus.PENDING

def test_task_update_status():
    task = Task(
        id="test-1",
        description="Test task",
        status=TaskStatus.PENDING,
        parent_id=None,
        completion_criteria="Complete",
        dependencies=[],
    )
    task.update_status(TaskStatus.COMPLETED, "Done!")
    assert task.status == TaskStatus.COMPLETED
    assert task.message == "Done!"
```

- [ ] **Step 2: Run test - verify it fails**

```bash
pytest tests/base/test_types.py -v
```

Expected: FAIL (module not found)

- [ ] **Step 3: Implement all types**

```python
# aime/base/types.py
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Callable
import asyncio

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ArtifactReference:
    type: str  # "file" | "url" | "database" | "text"
    path: str
    description: str

@dataclass
class Task:
    id: str
    description: str
    status: TaskStatus
    parent_id: Optional[str]
    completion_criteria: str
    dependencies: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    message: Optional[str] = None
    artifacts: List[ArtifactReference] = field(default_factory=list)

    def update_status(self, status: TaskStatus, message: Optional[str] = None) -> None:
        self.status = status
        if message:
            self.message = message
        self.updated_at = datetime.now()

@dataclass
class TaskUpdate:
    task_id: str
    old_status: TaskStatus
    new_status: TaskStatus
    message: Optional[str]

@dataclass
class PlannerOutput:
    class Action(str, Enum):
        DISPATCH_SUBTASK = "dispatch_subtask"
        COMPLETE_GOAL = "complete_goal"
        WAIT = "wait"

    action: Action
    subtask_id: Optional[str] = None
    summary: Optional[str] = None

@dataclass
class ActorResult:
    task_id: str
    status: TaskStatus
    summary: str
    artifacts: List[ArtifactReference] = field(default_factory=list)

class ProgressList:
    """Hierarchical thread-safe task progress list."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._subscribers: List[Callable[[TaskUpdate], None]] = []

    async def add_task(
        self,
        description: str,
        completion_criteria: str,
        parent_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Task:
        async with self._lock:
            task_id = str(uuid.uuid4())[:8]
            task = Task(
                id=task_id,
                description=description,
                status=TaskStatus.PENDING,
                parent_id=parent_id,
                completion_criteria=completion_criteria,
                dependencies=dependencies or [],
            )
            self._tasks[task_id] = task
            return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        message: Optional[str] = None,
    ) -> Optional[Task]:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                old_status = task.status
                task.update_status(status, message)
                task_update = TaskUpdate(task_id, old_status, status, message)
                for subscriber in self._subscribers:
                    subscriber(task_update)
            return task

    async def add_artifact(
        self,
        task_id: str,
        artifact: ArtifactReference,
    ) -> Optional[Task]:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.artifacts.append(artifact)
            return task

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks that are ready to execute (dependencies satisfied)."""
        # All tasks not in-progress, and all dependencies completed
        result = []
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            all_deps_completed = True
            for dep_id in task.dependencies:
                dep_task = self._tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    all_deps_completed = False
                    break
            if all_deps_completed:
                result.append(task)
        return result

    def export_markdown(self, indent: int = 0) -> str:
        """Export progress list as markdown task list."""
        # Build tree structure
        children: dict[str, List[Task]] = {}
        root_tasks: List[Task] = []
        for task in self._tasks.values():
            if task.parent_id is None:
                root_tasks.append(task)
            else:
                if task.parent_id not in children:
                    children[task.parent_id] = []
                children[task.parent_id].append(task)

        def render_task(task: Task, level: int) -> str:
            prefix = "  " * level
            status_mark = "[x]" if task.status == TaskStatus.COMPLETED else "[ ]"
            line = f"{prefix}- {status_mark} {task.description}\n"
            if task.id in children:
                for child in children[task.id]:
                    line += render_task(child, level + 1)
            return line

        result = ""
        for root in root_tasks:
            result += render_task(root, indent)
        return result

    def subscribe(self, callback: Callable[[TaskUpdate], None]) -> Callable:
        """Subscribe to task updates. Returns unsubscribe function."""
        self._subscribers.append(callback)
        def unsubscribe():
            if callback in self._subscribers:
                self._subscribers.remove(callback)
        return unsubscribe

    @property
    def all_tasks(self) -> List[Task]:
        async with self._lock:
            return list(self._tasks.values())
```

- [ ] **Step 5: Add ProgressList tests**

Add to `tests/base/test_types.py`:

```python
async def test_progress_list_add_task():
    pl = ProgressList()
    task = await pl.add_task(
        "Test task",
        "Complete it",
    )
    assert task.id is not None
    assert task.status == TaskStatus.PENDING

async def test_progress_list_update_status():
    pl = ProgressList()
    task = await pl.add_task("Test", "Done")
    await pl.update_status(task.id, TaskStatus.IN_PROGRESS)
    updated = await pl.get_task(task.id)
    assert updated.status == TaskStatus.IN_PROGRESS

async def test_get_pending_tasks():
    pl = ProgressList()
    parent = await pl.add_task("Parent", "Done")
    child = await pl.add_task("Child", "Done", parent_id=parent.id, dependencies=[parent.id])
    assert len(pl.get_pending_tasks()) == 1  # parent pending

def test_export_markdown():
    # test that markdown is generated
```

- [ ] **Step 6: Run test - verify all pass**

```bash
pytest tests/base/test_types.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add aime/base/types.py tests/base/test_types.py
git commit -m "feat: base types and ProgressList"
```

### Task 3: LLM 基础抽象 (base/llm.py)

**Files:**
- Create: `aime/base/llm.py`
- Create: `tests/base/test_llm.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/base/test_llm.py
import pytest
from aime.base.llm import BaseLLM, Message, ToolCall, LLMResponse

def test_message_creation():
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

def test_tool_call_creation():
    call = ToolCall(id="call-1", name="search", arguments={"query": "test"})
    assert call.name == "search"
```

- [ ] **Step 2: Run test - verify fails**

```bash
pytest tests/base/test_llm.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement BaseLLM and related types**

```python
# aime/base/llm.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, AsyncIterator, Protocol
from abc import ABC, abstractmethod

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None

@dataclass
class UsageInfo:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

@dataclass
class LLMResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Optional[UsageInfo] = None

@dataclass
class LLMResponseChunk:
    content: str
    tool_call_id: Optional[str] = None
    tool_call_name: Optional[str] = None
    tool_call_arguments: str = ""
    finished: bool = False

class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @property
    def model_name(self) -> str:
        """Return the model name."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate complete response (non-streaming)."""
        ...

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming generation."""
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[LLMResponseChunk]:
        """Generate response in streaming mode."""
        ...
```

- [ ] **Step 4: Run test - verify passes**

```bash
pytest tests/base/test_llm.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add aime/base/llm.py tests/base/test_llm.py
git commit -m "feat: BaseLLM abstract interface"
```

### Task 4: 工具基础抽象 (base/tool.py)

**Files:**
- Create: `aime/base/tool.py`
- Create: `tests/base/test_tool.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/base/test_tool.py
import pytest
from aime.base.tool import BaseTool, ToolResult, ToolBundle

def test_tool_bundle_creation():
    bundle = ToolBundle("test", "Test bundle", [])
    assert bundle.name == "test"
```

- [ ] **Step 2: Run test - verify fails**

```bash
pytest tests/base/test_tool.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement BaseTool, ToolResult, ToolBundle**

```python
# aime/base/tool.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, AsyncIterator, ABC, abstractmethod

from .types import ArtifactReference

@dataclass
class ToolResult:
    success: bool
    content: str
    artifacts: List[ArtifactReference] = field(default_factory=list)

class BaseTool(ABC):
    """Abstract base class for tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used for invocation."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        ...

    @property
    @abstractmethod
    def parameters_schema(self) -> dict:
        """JSON Schema for tool parameters."""
        ...

    @abstractmethod
    async def __call__(self, params: dict) -> ToolResult:
        """Execute the tool with given parameters."""
        ...

@dataclass
class ToolBundle:
    """A bundle of related tools grouped by functionality."""
    name: str
    description: str
    tools: List[BaseTool]

    def get_tools(self) -> List[BaseTool]:
        return self.tools

@dataclass
class Toolkit:
    """A collection of tool bundles selected for a specific task."""
    bundles: List[ToolBundle]

    def get_all_tools(self) -> List[BaseTool]:
        """Flatten all tools from all bundles."""
        return [tool for bundle in self.bundles for tool in bundle.tools]
```

- [ ] **Step 4: Run test - verify passes**

```bash
pytest tests/base/test_tool.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add aime/base/tool.py tests/base/test_tool.py
git commit -m "feat: BaseTool and ToolBundle abstractions"
```

### Task 5: 知识库 (base/knowledge.py)

**Files:**
- Create: `aime/base/knowledge.py`
- Create: `tests/base/test_knowledge.py`

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Run test - verify fails**
- [ ] **Step 3: Implement KnowledgeBase interface and simple in-memory implementation**
- [ ] **Step 4: Run test - verify passes**
- [ ] **Step 5: Commit**

---

## Stage 2: 核心组件（依赖基础抽象）

### Task 6: 进度管理模块 (components/progress_module.py)

**Files:**
- Create: `aime/components/progress_module.py`
- Create: `tests/components/test_progress_module.py`

- [ ] **Step 1: Write tests** (add_task, get_task, update_status, export_markdown, subscribe, concurrent updates)
- [ ] **Step 2: Run test - verify fails**
- [ ] **Step 3: Implement ProgressManagementModule that wraps ProgressList**
- [ ] **Step 4: Run test - verify passes**
- [ ] **Step 5: Test concurrent updates verify thread safety**
- [ ] **Step 6: Commit**

### Task 7: 错误处理和重试工具 (components/retry.py)

**Files:**
- Create: `aime/components/retry.py`
- Create: `tests/components/test_retry.py`

- [ ] **Step 1: Implement retry with exponential backoff for LLM API calls**
- [ ] **Step 2: Write tests**
- [ ] **Step 3: Commit**

### Task 8: 动态规划器 (components/dynamic_planner.py)

**Files:**
- Create: `aime/components/dynamic_planner.py`
- Create: `tests/components/test_dynamic_planner.py`

- [ ] **Step 1: Write tests for initialize and step**
- [ ] **Step 2: Run test - verify fails**
- [ ] **Step 3: Implement DynamicPlanner with LLM prompting**
- [ ] **Step 4: Run test - verify passes**
- [ ] **Step 5: Commit**

### Task 9: Actor工厂 (components/actor_factory.py)

**Files:**
- Create: `aime/components/actor_factory.py`
- Create: `tests/components/test_actor_factory.py`

- [ ] **Step 1: Write tests for create_actor**
- [ ] **Step 2: Run test - verify fails**
- [ ] **Step 3: Implement ActorFactory with prompt composition (persona + tools + knowledge + env + format)**
- [ ] **Step 4: Run test - verify passes**
- [ ] **Step 5: Commit**

### Task 10: 动态Actor (components/dynamic_actor.py)

**Files:**
- Create: `aime/components/dynamic_actor.py`
- Create: `tests/components/test_dynamic_actor.py`

- [ ] **Step 1: Write tests for ReAct loop**
- [ ] **Step 2: Run test - verify fails**
- [ ] **Step 3: Implement DynamicActor with async run method**
- [ ] **Step 4: Run test - verify passes**
- [ ] **Step 5: Commit**

---

## Stage 3: LLM 提供商实现

### Task 11: OpenAI 提供商 (providers/openai.py)

**Files:**
- Create: `aime/providers/openai.py`
- Create: `tests/providers/test_openai.py`

- [ ] **Step 1: Implement OpenAILLM that implements BaseLLM**
- [ ] **Step 2: Write tests (requires OPENAI_API_KEY)**
- [ ] **Step 3: Commit**

### Task 12: Anthropic 提供商 (providers/anthropic.py)

**Files:**
- Create: `aime/providers/anthropic.py`
- Create: `tests/providers/test_anthropic.py`

- [ ] **Step 1: Implement AnthropicLLM that implements BaseLLM**
- [ ] **Step 2: Write tests (requires ANTHROPIC_API_KEY)**
- [ ] **Step 3: Commit**

---

## Stage 4: 工具系统

### Task 13: 工具捆绑包和内置工具 (tools/)

**Files:**
- Create: `aime/tools/bundle.py` (extra utilities)
- Create: `aime/tools/builtin/__init__.py` (already created in Task 0)
- Create: `aime/tools/builtin/update_progress.py`
- Create: `aime/tools/builtin/python_repl.py`
- Create: `aime/tools/builtin/web_search.py`
- Create: `aime/tools/builtin/read_file.py`
- Create: `aime/tools/builtin/write_file.py`
- Create: `tests/tools/test_tools.py`

- [ ] **Step 1: Implement ToolBundle registry in bundle.py**
- [ ] **Step 2: Implement UpdateProgress tool (system tool for progress reporting)**
- [ ] **Step 3: Implement PythonREPL tool for executing Python code**
- [ ] **Step 4: Implement WebSearch tool (configurable backend)**
- [ ] **Step 5: Implement read_file/write_file tools for file system access**
- [ ] **Step 6: Write tests**
- [ ] **Step 7: Commit**

### Task 14: MCP 适配器 (tools/mcp_adapter.py)

**Files:**
- Create: `aime/tools/mcp_adapter.py`
- Create: `tests/tools/test_mcp_adapter.py`

- [ ] **Step 1: Implement MCPAdapter that converts MCP tools to BaseTool**
- [ ] **Step 2: Write tests**
- [ ] **Step 3: Commit**

---

## Stage 5: IO 和辅助功能

### Task 15: Markdown 导入导出 (io/markdown.py)

**Files:**
- Create: `aime/io/markdown.py`
- Create: `tests/io/test_markdown.py`

- [ ] **Step 1: Implement export_markdown(ProgressList)**
- [ ] **Step 2: Implement parse_markdown(text) for importing existing plans**
- [ ] **Step 3: Write tests**
- [ ] **Step 4: Run test - verify passes**
- [ ] **Step 5: Commit**

### Task 16: 角色提示模板 (templates/personas.py)

**Files:**
- Create: `aime/templates/personas.py`

- [ ] **Step 1: Create common persona templates (software engineering, research, planning, etc.)**
- [ ] **Step 2: Commit**

---

## Stage 6: 主入口和示例

### Task 17: 主Aime入口 (aime.py)

**Files:**
- Create: `aime/aime.py`
- Create: `tests/test_aime.py`

- [ ] **Step 1: Implement main Aime class that orchestrates all components**

```python
# aime/aime.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List

from .base.types import (
    Task, TaskStatus, ArtifactReference, ProgressList, PlannerOutput,
)
from .base.llm import BaseLLM
from .base.tool import ToolBundle
from .base.config import AimeConfig
from .components.dynamic_planner import DynamicPlanner
from .components.actor_factory import ActorFactory
from .components.progress_module import ProgressManagementModule

@dataclass
class AimeResult:
    success: bool
    goal: str
    final_summary: str
    artifacts: List[ArtifactReference] = field(default_factory=list)

class Aime:
    def __init__(
        self,
        llm: BaseLLM,
        tool_bundles: Optional[List[ToolBundle]] = None,
        config: Optional[AimeConfig] = None,
    ):
        self._llm = llm
        self._config = config or AimeConfig()
        self._progress_module = ProgressManagementModule()
        self._actor_factory = ActorFactory(
            llm=llm,
            tool_bundles=tool_bundles or [],
            config=self._config.actor,
        )
        self._planner = DynamicPlanner(
            llm=llm,
            progress_module=self._progress_module,
            config=self._config.planner,
        )

    async def run(self, goal: str) -> AimeResult:
        """Main entry point: run Aime to complete a goal."""
        # Initialize planner with goal
        await self._planner.initialize(goal)

        # Main loop
        for iteration in range(self._config.max_total_iterations):
            output = await self._planner.step()

            if output.action == PlannerOutput.Action.COMPLETE_GOAL:
                # Goal completed
                progress = self._progress_module.get_progress_list()
                final_task = self._find_final_task(progress)
                return AimeResult(
                    success=True,
                    goal=goal,
                    final_summary=output.summary or "Completed successfully",
                    artifacts=final_task.artifacts if final_task else [],
                )
            elif output.action == PlannerOutput.Action.DISPATCH_SUBTASK:
                # Create actor and run it in background task
                if output.subtask_id:
                    actor = await self._actor_factory.create_actor(
                        await self._progress_module.get_task(output.subtask_id),
                        self._progress_module,
                    )
                    # Spawn async task - actor will update progress independently
                    asyncio.create_task(actor.run())
            elif output.action == PlannerOutput.Action.WAIT:
                # Wait for actors to make progress
                await asyncio.sleep(0.1)
                continue

        # Max iterations reached
        return AimeResult(
            success=False,
            goal=goal,
            final_summary=f"Reached maximum iterations ({self._config.max_total_iterations})",
        )

    def export_progress(self) -> str:
        """Export current progress as markdown."""
        return self._progress_module.export_markdown()
```

- [ ] **Step 2: Write integration test with mock LLM**
- [ ] **Step 3: Run test - verify passes**
- [ ] **Step 4: Commit**

### Task 18: 示例 - GAIA 问题解决

**Files:**
- Create: `examples/gaia_solve.py`

- [ ] **Step 1: Create example that solves a GAIA question using Aime**
- [ ] **Step 2: Add comments explaining usage and configuration**
- [ ] **Step 3: Commit**

---

## Stage 7: 文档和收尾

### Task 19: README 和使用说明

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write README with: project intro, installation, quickstart, example**
- [ ] **Step 2: Commit**

### Task 20: 完整测试套件运行和检查

- [ ] **Step 1: Run full test suite with coverage**

```bash
pytest tests/ -v --cov=aime
```

- [ ] **Step 2: Fix any failing tests**
- [ ] **Step 3: Run ruff linting**

```bash
ruff check aime/ tests/
```

- [ ] **Step 4: Fix linting issues**
- [ ] **Step 5: Commit**

---

## 依赖关系图（修正后，无循环依赖）

```
0: 项目结构初始化
├─→ 1: 配置类定义
   ├─→ 2: 基础类型定义
      ├─→ 3: LLM 基础抽象
      ├─→ 4: 工具基础抽象
         ├─→ 5: 知识库
            ├─→ 6: 进度管理模块
               ├─→ 7: 错误处理和重试
                  ├─→ 8: 动态规划器
                  ├─→ 9: Actor工厂
                  ├─→ 10: 动态Actor
                     ├─→ 11: OpenAI 提供商
                     ├─→ 12: Anthropic 提供商
                     ├─→ 13: 工具捆绑包和内置工具
                     ├─→ 14: MCP 适配器
                     ├─→ 15: Markdown IO
                     ├─→ 16: 角色模板
                        ├─→ 17: 主入口 Aime class
                           ├─→ 18: 示例
                              ├─→ 19: README
                                 └─→ 20: 完整测试
```

## 统计

| 项目 | 数值 |
|------|------|
| 总任务数 | 20 |
| 预计代码行数 | ~1800-2200 行（不含测试和空行） |
| 预计完成时间 | 2-3 个完整会话 |
