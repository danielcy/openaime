# Session Persistence Design for AIME

## 需求概述

为 AIME 框架添加会话持久化存储功能，参考 Claude Code CLI 的设计：
- 全局存储所有会话到 `~/.openaime/sessions/{session-id}/`
- 使用 JSONL 格式存储聊天记录，实时追加写入
- 支持列出、加载、删除会话
- 只持久化聊天历史，不保存任务进度状态
- 保存完整元数据（会话 ID、创建时间、更新时间、标题、workspace 路径、目标描述、模型名称）

## 架构设计

采用三层分层架构：

```
aime/base/
├── session.py           # 数据类型定义
├── session_storage.py   # 底层文件存储操作
├── session_manager.py  # 业务逻辑层
```

## 数据类型定义 (`aime/base/session.py`)

### `SessionInfo` - 会话元数据

```python
from dataclasses import dataclass
from typing import Optional, List, Literal
import uuid

@dataclass
class SessionInfo:
    """Metadata for a saved session.
    
    Stored as session.json in the session directory.
    """
    session_id: str
    created_at: str            # ISO format timestamp (matches ChatMessage)
    updated_at: str            # ISO format timestamp
    title: str                 # First message content as title
    workspace_path: Optional[str] = None
    goal_description: Optional[str] = None
    model_name: Optional[str] = None
```

### 扩展现有 `ChatMessage`

修改 `aime/base/types.py` 中的 `ChatMessage`，增加可选 `tools` 字段：

```python
@dataclass
class ChatMessage:
    """Chat message for session context retention and persistence."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tools: Optional[List[dict]] = None  # Optional: tool call results
```

**设计决策：** 扩展现有类型而不是新建 `SessionMessage`，避免转换开销和不一致。所有持久化直接使用 `ChatMessage`。

## 底层存储 (`aime/base/session_storage.py`)

`SessionStorage` 只负责底层文件系统操作，不包含业务逻辑：

```python
class SessionStorage:
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize with base directory, defaults to ~/.openaime/sessions"""
    
    def list_sessions(self) -> List[SessionInfo]:
        """Enumerate all sessions, return sorted by updated_at descending."""
    
    def create_session(self) -> str:
        """Create a new empty session directory, return session_id."""
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Read session metadata from session.json."""
    
    def save_session_info(self, info: SessionInfo) -> None:
        """Save session metadata to session.json."""
    
    def append_message(self, session_id: str, message: ChatMessage) -> None:
        """Append a message to transcript.jsonl.
        
        Each append opens file, appends one line, closes file.
        This ensures immediate persistence and crash safety.
        Message is serialized as JSON one line.
        """
    
    def load_transcript(self, session_id: str) -> List[ChatMessage]:
        """Load entire transcript from transcript.jsonl."""
    
    def delete_session(self, session_id: str) -> bool:
        """Delete the entire session directory."""
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
```

**存储布局：**
```
~/.openaime/sessions/
├── {session-id}/
│   ├── session.json       # 元数据 (SessionInfo)
│   └── transcript.jsonl   # 聊天记录（JSONL 格式，每行一个 ChatMessage）
```

## 业务逻辑层 (`aime/base/session_manager.py`)

`SessionManager` 提供高层业务 API，维护全局默认单例：

```python
class SessionManager:
    def __init__(self, storage: Optional[SessionStorage] = None):
        """Initialize with optional custom storage."""
    
    def list_sessions(self) -> List[SessionInfo]:
        """Get all sessions sorted by updated_at descending."""
    
    def new_session(
        self,
        title: str,
        workspace_path: Optional[str] = None,
        goal_description: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Create a new session with metadata, return session_id."""
    
    def load_session(self, session_id: str) -> Tuple[SessionInfo, List[ChatMessage]]:
        """Load session transcript, return SessionInfo and ChatMessage list."""
    
    def add_user_message(self, session_id: str, content: str) -> None:
        """Add a user message, update updated_at timestamp."""
    
    def add_assistant_message(self, session_id: str, content: str) -> None:
        """Add an assistant message, update updated_at timestamp."""
    
    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Add any ChatMessage, update updated_at timestamp."""
    
    def delete_session(self, session_id: str, confirm: bool = False) -> bool:
        """Delete a session. Requires confirm=True for safety."""
    
    def update_metadata(self, session_id: str, **kwargs) -> None:
        """Update session metadata and save."""
    
    @classmethod
    def get_default(cls) -> "SessionManager":
        """Get the global default SessionManager instance."""
```

**设计要点：**
- 全局默认单例方便日常使用
- 支持注入自定义 `SessionStorage` 用于测试
- 每次添加消息都立即持久化，更新 `updated_at`
- `delete_session` 需要 `confirm=True` 参数，增加安全检查

## 解决重复聊天历史存储问题

当前现状：
- `OpenAime._chat_history` - 主聊天历史（aime.py line 123）
- `Planner._chat_history` -  planner 副本（planner.py line 55）

**解决方案：**
- 保留现有两处存储（避免大规模重构影响现有功能）
- 持久化时，使用 `OpenAime._chat_history` 作为权威来源
- 当从持久化加载会话时，同时同步到 `OpenAime` 和 `Planner`
- 添加消息时，同时更新两处，保证一致性

这样不需要大规模重构现有代码，只需要增加同步步骤。

## 集成到 OpenAime (`aime/aime.py`)

### 修复已有问题：执行摘要生成

当前 `_generate_execution_summary()` 方法存在但没有被调用。我们修复这个问题：
- 在 `run()` 完成目标后，调用 `_generate_execution_summary()`
- 将生成的摘要作为 `assistant` 消息添加到聊天历史
- 这个消息会被自动持久化

### 新增参数到 `__init__`

```python
class OpenAime:
    def __init__(
        self,
        config: AimeConfig,
        llm: BaseLLM,
        workspace: str,
        # ... existing parameters ...
        # New parameters for session persistence:
        session_id: Optional[str] = None,
        session_manager: Optional[SessionManager] = None,
        auto_save_session: bool = True,  # Default True - automatic persistence
    ):
```

- `session_id`: 如果提供，加载已有会话；`None` 创建新会话
- `session_manager`: 自定义会话管理器，默认使用全局单例
- `auto_save_session`: 是否自动保存，**默认 `True`** - 开箱即用，用户享受持久化好处

### 新增公共方法

```python
class OpenAime:
    def get_session_id(self) -> Optional[str]:
        """Get current session ID if auto_save is enabled."""
    
    @classmethod
    def list_available_sessions(cls) -> List[SessionInfo]:
        """List all saved sessions from global storage."""
    
    def load_session(self, session_id: str) -> List[ChatMessage]:
        """Load a saved session into current instance.
        
        Chat history is loaded into both OpenAime and Planner.
        Returns the loaded chat history.
        """
    
    def delete_current_session(self, confirm: bool = False) -> bool:
        """Delete the current session from storage.
        
        Requires confirm=True for safety.
        """
```

### 工作流程

1. **Initialization**:
   - If `auto_save_session=True`:
     - If `session_id` provided → load existing transcript
     - If `session_id=None` → create new session
     - Save metadata (workspace path, model name, initial goal)

2. **During `run()`**:
   - User goal added as `user` message → appended to JSONL immediately
   - After completion:
     - 调用 `_generate_execution_summary()` 生成执行摘要
     - 摘要作为 `assistant` 消息添加到聊天历史
     - 立即持久化到 JSONL

3. **Chat History Synchronization**:
   - When adding a message: add to both `OpenAime._chat_history` and `Planner._chat_history`
   - When loading: load into both places to keep consistency

4. **Backward Compatibility**:
   - All new parameters have default values
   - `auto_save_session=False` → completely unchanged behavior
   - Existing code runs without modification

## 使用示例

### 创建新会话
```python
import asyncio
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.providers.llm.anthropic import AnthropicLLM

llm = AnthropicLLM(api_key="...")
aime = OpenAime(
    config=AimeConfig(),
    llm=llm,
    workspace="./my-project",
    auto_save_session=True,  # User opt-in explicitly
)

result = await aime.run("Add a login feature to app.py")
print(f"Session ID: {aime.get_session_id()}")
# Save this ID to resume later
```

### 恢复已有会话
```python
# Later, or after restart
aime = OpenAime(
    config=AimeConfig(),
    llm=llm,
    workspace="./my-project",
    session_id="your-saved-session-id",
    auto_save_session=True,
)
# Chat history is already loaded into both OpenAime and Planner!
result = await aime.run("Now add JWT authentication to that login endpoint")
# Context is preserved from previous session
```

### 列出所有会话
```python
sessions = OpenAime.list_available_sessions()
for s in sessions:
    print(f"{s.session_id} - {s.title} - {s.updated_at}")
```

## 文件修改清单

| 文件 | 变更类型 |
|------|----------|
| `aime/base/session.py` | 新建 - SessionInfo 数据类型 |
| `aime/base/session_storage.py` | 新建 - 底层存储 |
| `aime/base/session_manager.py` | 新建 - 业务逻辑 |
| `aime/base/types.py` | 修改 - 扩展 ChatMessage 增加 tools 字段 |
| `aime/aime.py` | 修改 - 新增参数、方法，修复执行摘要调用 |
| `aime/components/planner.py` | 修改 - 增加对外部加载聊天历史的支持 |
| `tests/test_session_persistence.py` | 新建 - 完整测试套件 |

### Planner 需要增加的方法

```python
class Planner:
    # ... existing code ...
    
    def load_chat_history(self, history: List[ChatMessage]) -> None:
        """Load chat history from persisted session."""
        self._chat_history = history.copy()
```

## 测试计划

- 测试创建新会话 → 检查文件生成
- 测试追加消息 → 验证 JSONL 内容
- 测试加载会话 → 验证聊天历史正确恢复到 OpenAime 和 Planner
- 测试列出会话 → 验证排序正确
- 测试删除会话 → 验证目录删除，需要 confirm=True
- 测试崩溃安全性 → 验证追加过程中断不会损坏已有数据
- 测试向后兼容 → 验证原有代码 `auto_save_session=False` 依然工作
- 测试执行摘要 → 验证生成并正确持久化

## 设计决策总结

| 决策 | 选择 | 原因 |
|------|------|------|
| 存储位置 | 全局 `~/.openaime/sessions/` | 和 Claude Code 保持一致，方便用户 |
| 文件格式 | JSONL | 便于流式追加，简单可靠 |
| 写入方式 | 每次追加都打开/关闭文件 | 保证实时持久化，崩溃不丢消息 |
| 保存内容 | 只保存聊天历史 | 符合需求，设计简单 |
| 时间戳格式 | ISO 字符串 | 和现有 ChatMessage 保持一致 |
| 消息类型 | 扩展现有 ChatMessage | 避免重复类型和转换开销 |
| 架构分层 | SessionStorage + SessionManager | 清晰职责分离，易于测试和扩展 |
| 集成方式 | 可选参数加入 OpenAime | 完全向后兼容，不影响现有代码 |
| 默认行为 | `auto_save_session=True` | 开箱即用，用户自动获得持久化好处 |
| 删除安全 | 需要 `confirm=True` | 防止误删除 |
| 重复聊天历史 | 保持现状 + 同步两边 | 避免大规模重构，减少风险 |

## 修复的问题（来自代码审查）

1. ✅ **Timestamp 一致性** - 统一使用 ISO 格式字符串，匹配现有 `ChatMessage`
2. ✅ **重复聊天历史** - 保持现有结构，增加同步保证一致性
3. ✅ **执行摘要持久化** - 修复原有问题，调用 `_generate_execution_summary()` 并保存
4. ✅ **默认行为变更风险** - 根据用户要求，`auto_save_session` 默认改为 `True`，开箱即用
5. ✅ **消息类型不一致** - 扩展现有 `ChatMessage`，不新建类型
6. ✅ **删除安全** - 增加 `confirm` 参数，防止误删
