# Session Persistence Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent session storage to AIME framework, allowing users to save chat history to disk and resume sessions after restart, following Claude Code CLI's architecture.

**Architecture:** Three-layer architecture: `SessionInfo` data types → `SessionStorage` (low-level file operations) → `SessionManager` (business logic). Integrated into `OpenAime` via optional parameters. Uses JSONL format for append-only transcript storage.

**Tech Stack:** Python, dataclasses, jsonlines (or standard json dump per line), pathlib, os, uuid.

---

## File Overview

| File | Action | Responsibility |
|------|--------|----------------|
| `aime/base/__init__.py` | Create/Update | Export new session classes |
| `aime/base/session.py` | Create | `SessionInfo` dataclass for session metadata |
| `aime/base/session_storage.py` | Create | `SessionStorage` - low-level file system operations |
| `aime/base/session_manager.py` | Create | `SessionManager` - business logic, global default singleton |
| `aime/base/types.py` | Modify | Extend existing `ChatMessage` with optional `tools` field |
| `aime/aime.py` | Modify | Add session parameters to `OpenAime`, integrate persistence |
| `aime/components/planner.py` | Modify | Add `load_chat_history()` method to accept loaded history |
| `tests/test_session_persistence.py` | Create | Complete test suite |

---

## Task 1: Add `tools` field to existing `ChatMessage` in `types.py`

**Files:**
- Modify: `aime/base/types.py` (lines 98-104)

- [ ] **Step 1: Add the optional `tools` field**

```diff
@dataclass
class ChatMessage:
    """Chat message for session context retention."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
+   tools: Optional[List[dict]] = None  # Optional: tool call results for persistence
```

- [ ] **Step 2: Run existing tests to verify nothing broke**

```bash
python -m pytest tests/test_aime.py -v
```
Expected: All existing tests still pass

- [ ] **Step 3: Commit**

```bash
git add aime/base/types.py
git commit -m "feat(session): extend ChatMessage with optional tools field

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Create `aime/base/session.py` - `SessionInfo` dataclass

**Files:**
- Create: `aime/base/session.py`

- [ ] **Step 1: Write the `SessionInfo` dataclass**

```python
"""Session data types for persistent session storage.

This module defines the SessionInfo dataclass that stores metadata
about a saved session, including creation time, last update time,
title, workspace path, and goal description.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SessionInfo:
    """Metadata for a saved session.
    
    Stored as session.json in the session directory.
    
    Attributes:
        session_id: Unique UUID identifier for the session
        created_at: ISO format timestamp when session was created
        updated_at: ISO format timestamp when session was last updated
        title: Short title (usually first user message)
        workspace_path: Absolute path to the workspace directory
        goal_description: Initial goal description
        model_name: Name of the LLM model used
    """
    session_id: str
    created_at: str
    updated_at: str
    title: str
    workspace_path: Optional[str] = None
    goal_description: Optional[str] = None
    model_name: Optional[str] = None
```

- [ ] **Step 2: Create/Update `aime/base/__init__.py` to export new classes**

If `__init__.py` doesn't exist, create it. Add these exports:

```python
from aime.base.session import SessionInfo
from aime.base.session_storage import SessionStorage
from aime.base.session_manager import SessionManager
from aime.base.types import ChatMessage

__all__ = [
    'SessionInfo',
    'SessionStorage',
    'SessionManager',
    'ChatMessage',
]
```

- [ ] **Step 3: Run type check (if available)**

```bash
python -c "from aime.base.session import SessionInfo"
```
Expected: No import errors

- [ ] **Step 4: Commit**

```bash
git add aime/base/session.py
git commit -m "feat(session): add SessionInfo dataclass for session metadata

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Create `aime/base/session_storage.py` - Low-level storage

**Files:**
- Create: `aime/base/session_storage.py`

- [ ] **Step 1: Write imports and class skeleton**

```python
"""Low-level session storage operations.

This module handles the actual file system operations:
- Creating session directories
- Reading/writing session.json metadata
- Appending to transcript.jsonl
- Loading complete transcripts
- Deleting sessions
"""
import json
import os
import uuid
from pathlib import Path
from typing import Optional, List
from aime.base.session import SessionInfo
from aime.base.types import ChatMessage


class SessionStorage:
    """Low-level session storage operations.
    
    Handles file system level operations for persistent sessions.
    Each session is stored in its own directory:
    {base_dir}/{session_id}/session.json - metadata
    {base_dir}/{session_id}/transcript.jsonl - chat messages (JSONL)
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize storage with base directory.
        
        Args:
            base_dir: Base directory for all sessions.
                Defaults to ~/.openaime/sessions
        """
        if base_dir is None:
            home = Path.home()
            self.base_dir = home / ".openaime" / "sessions"
        else:
            self.base_dir = Path(base_dir)
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def list_sessions(self) -> List[SessionInfo]:
        """Enumerate all sessions, sorted by updated_at descending.
        
        Returns:
            List of SessionInfo for all existing sessions
        """
        pass  # Implementation
    
    def create_session(self) -> str:
        """Create a new empty session directory.
        
        Returns:
            session_id for the new session
        """
        pass  # Implementation
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Read session metadata from session.json.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionInfo if session exists, None otherwise
        """
        pass  # Implementation
    
    def save_session_info(self, info: SessionInfo) -> None:
        """Save session metadata to session.json.
        
        Args:
            info: SessionInfo to save
        """
        pass  # Implementation
    
    def append_message(self, session_id: str, message: ChatMessage) -> None:
        """Append a message to transcript.jsonl.
        
        Opens the file, appends one JSON line, closes the file.
        This ensures immediate persistence and crash safety.
        
        Args:
            session_id: Session identifier
            message: ChatMessage to append
        """
        pass  # Implementation
    
    def load_transcript(self, session_id: str) -> List[ChatMessage]:
        """Load entire transcript from transcript.jsonl.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of ChatMessage objects
        """
        pass  # Implementation
    
    def delete_session(self, session_id: str) -> bool:
        """Delete the entire session directory.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted successfully, False if not found
        """
        pass  # Implementation
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session directory exists
        """
        pass  # Implementation
    
    def _get_session_dir(self, session_id: str) -> Path:
        """Get path to session directory."""
        return self.base_dir / session_id
    
    def _get_session_info_path(self, session_id: str) -> Path:
        """Get path to session.json."""
        return self._get_session_dir(session_id) / "session.json"
    
    def _get_transcript_path(self, session_id: str) -> Path:
        """Get path to transcript.jsonl."""
        return self._get_session_dir(session_id) / "transcript.jsonl"
```

- [ ] **Step 2: Implement all methods**

Implement each method according to the design:

- `list_sessions()`: Iterate directories, read `session.json`, collect `SessionInfo`, sort by `updated_at` descending
- `create_session()`: Generate UUID, create directory, return session_id
- `get_session_info()`: Read and parse `session.json`, return `SessionInfo` or `None`
- `save_session_info()`: Write JSON to `session.json`
- `append_message()`: Open in append mode, dump message as JSON line, close
- `load_transcript()`: Read each line, parse JSON, collect into `List[ChatMessage]`
- `delete_session()`: Recursively delete session directory
- `session_exists()`: Check if directory exists

**Note:** Use `json.dumps(message.__dict__)` to serialize, `json.loads()` to deserialize.

- [ ] **Step 3: Commit**

```bash
git add aime/base/session_storage.py
git commit -m "feat(session): add SessionStorage low-level storage

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Create `aime/base/session_manager.py` - Business logic layer

**Files:**
- Create: `aime/base/session_manager.py`

- [ ] **Step 1: Write imports and class skeleton**

```python
"""High-level session manager business logic.

This module provides the SessionManager that handles:
- Creating new sessions with proper metadata
- Adding messages (updates updated_at timestamp)
- Loading sessions and converting to ChatMessage format
- Deleting sessions with safety confirmation
- Global default singleton for convenient access
"""
from datetime import datetime
from typing import Optional, List, Tuple
from aime.base.session import SessionInfo
from aime.base.session_storage import SessionStorage
from aime.base.types import ChatMessage


class SessionManager:
    """High-level session manager business logic.
    
    Provides business API for session operations and
    maintains a global default singleton for convenient use.
    """
    
    _default_instance: Optional["SessionManager"] = None
    
    def __init__(self, storage: Optional[SessionStorage] = None):
        """Initialize with optional custom storage.
        
        Args:
            storage: SessionStorage instance, uses default if None
        """
        self.storage = storage or SessionStorage()
    
    def list_sessions(self) -> List[SessionInfo]:
        """Get all sessions sorted by updated_at descending.
        
        Returns:
            List of SessionInfo for all sessions
        """
        pass  # Implementation
    
    def new_session(
        self,
        title: str,
        workspace_path: Optional[str] = None,
        goal_description: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Create a new session with metadata.
        
        Args:
            title: Short title for the session (usually first message)
            workspace_path: Absolute path to workspace
            goal_description: Initial goal description
            model_name: Name of the LLM model used
            
        Returns:
            session_id for the new session
        """
        pass  # Implementation
    
    def load_session(self, session_id: str) -> Tuple[SessionInfo, List[ChatMessage]]:
        """Load a session transcript.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (SessionInfo, List[ChatMessage])
        
        Raises:
            ValueError if session not found
        """
        pass  # Implementation
    
    def add_user_message(self, session_id: str, content: str) -> None:
        """Add a user message and update timestamp.
        
        Args:
            session_id: Session identifier
            content: Message content
        """
        pass  # Implementation
    
    def add_assistant_message(self, session_id: str, content: str) -> None:
        """Add an assistant message and update timestamp.
        
        Args:
            session_id: Session identifier
            content: Message content
        """
        pass  # Implementation
    
    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Add any message and update the session's updated_at timestamp.
        
        Args:
            session_id: Session identifier
            message: ChatMessage to add
        """
        pass  # Implementation
    
    def delete_session(self, session_id: str, confirm: bool = False) -> bool:
        """Delete a session.
        
        Args:
            session_id: Session identifier
            confirm: Must be True to delete, safety check
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass  # Implementation
    
    def update_metadata(self, session_id: str, **kwargs) -> None:
        """Update session metadata and save.
        
        Args:
            session_id: Session identifier
            **kwargs: Fields to update (title, goal_description, etc.)
        """
        pass  # Implementation
    
    @classmethod
    def get_default(cls) -> "SessionManager":
        """Get or create the global default SessionManager instance.
        
        Returns:
            The global default instance
        """
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance
```

- [ ] **Step 2: Implement all methods**

Key implementation notes:
- `add_message()` must: append message to transcript, update `updated_at` in SessionInfo, save SessionInfo
- `update_metadata()` must: get existing SessionInfo, update fields, save
- Truncate title to ~80 characters for display

- [ ] **Step 3: Commit**

```bash
git add aime/base/session_manager.py
git commit -m "feat(session): add SessionManager business logic layer

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Add `load_chat_history` method to `Planner`

**Files:**
- Modify: `aime/components/planner.py` (after line 589)

- [ ] **Step 1: Add `load_chat_history` method**

```python
def load_chat_history(self, history: List[ChatMessage]) -> None:
    """Load chat history from persisted session.
    
    Replaces the existing chat history with the loaded one.
    
    Args:
        history: List of ChatMessage to load
    """
    self._chat_history = history.copy()
```

- [ ] **Step 2: Check existing methods still work**

```bash
python -c "from aime.components.planner import Planner; print('OK')"
```
Expected: No import errors

- [ ] **Step 3: Commit**

```bash
git add aime/components/planner.py
git commit -m "feat(session): add load_chat_history method to Planner

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Integrate session persistence into `OpenAime`

**Files:**
- Modify: `aime/aime.py`

- [ ] **Step 1: Add imports**

Add at top with other imports:
```python
from aime.base.session import SessionInfo
from aime.base.session_manager import SessionManager
```

- [ ] **Step 2: Add instance variables**

In `__init__`, after line 123:
```python
self._session_id: Optional[str] = None
self._session_manager: Optional[SessionManager] = None
self._auto_save_session: bool = False  # Will be set from parameter
```

- [ ] **Step 3: Update `__init__` signature**

Add the new parameters to `__init__`:
```python
def __init__(
    self,
    config: AimeConfig,
    llm: BaseLLM,
    workspace: str,
    log_level: None | Literal["verbose", "debug"] = "verbose",
    debug: Optional[bool] = None,
    toolkit: Optional[Toolkit] = None,
    tool_bundles: Optional[list[ToolBundle]] = None,
    knowledge: Optional[BaseKnowledge] = None,
    event_callback: Optional[EventCallback] = None,
    # New parameters for session persistence
    skills_path: Optional[list[str]] = None,
    auto_discover_skills: bool = True,
    # Above already exists, add these:
    session_id: Optional[str] = None,
    session_manager: Optional[SessionManager] = None,
    auto_save_session: bool = True,
):
```

- [ ] **Step 4: Initialize session in `__init__`**

After skills initialization and before UserQuestionManager setup:

```python
# Session persistence initialization
self._auto_save_session = auto_save_session
if self._auto_save_session:
    self._session_manager = session_manager or SessionManager.get_default()
    if session_id is None:
        # Create new session
        # Title will be set after we get the goal in run()
        pass  # Actual creation happens in run()
    else:
        # Load existing session
        assert self._session_manager is not None
        info, chat_history = self._session_manager.load_session(session_id)
        self._session_id = session_id
        # Load chat history into OpenAime
        self._chat_history = chat_history
        # Load chat history into Planner will happen after Planner is created
        # We'll handle this in _initialize_components
```

- [ ] **Step 4a: Load chat history into Planner in `_initialize_components`**

In `_initialize_components`, after `self.planner = Planner(...)` line, add:

```python
# If we loaded chat history from persistent storage, sync it to Planner
if self._auto_save_session and self._session_id is not None and self.planner:
    self.planner.load_chat_history(self._chat_history)
```

- [ ] **Step 5: Update `run()` method to handle session creation and saving**

In `run()`:

**Before adding goal to `self._chat_history` (current line 217):**
```python
if self._auto_save_session and self._session_manager and self._session_id is None:
    # Create new session with first goal as title
    title = goal[:80] if len(goal) > 80 else goal
    model_name = getattr(self.llm, 'model_name', None)
    session_id = self._session_manager.new_session(
        title=title,
        workspace_path=self.workspace,
        goal_description=goal,
        model_name=model_name,
    )
    self._session_id = session_id
```

**After goal completes, inside finally block before returning:**
```python
if self._auto_save_session and self._session_manager and self._session_id:
    # Generate execution summary and add as assistant message
    summary = await self._generate_execution_summary()
    summary_message = ChatMessage(role="assistant", content=summary)
    # Add to OpenAime chat history
    self._chat_history.append(summary_message)
    # Add to Planner chat history (if Planner exists)
    if self.planner:
        self.planner._chat_history.append(summary_message)
    # Persist to disk
    self._session_manager.add_message(self._session_id, summary_message)
```

**Important:** Must synchronize chat history between `OpenAime` and `Planner` - always add to both when adding a new message.

- [ ] **Step 6: When adding messages, keep both in sync**

When adding a new message:
1. Add to `self._chat_history` (OpenAime copy)
2. If `self.planner` exists (already initialized), also add to `self.planner._chat_history`
3. If session persistence is enabled, also append to persistent storage

This ensures both copies are always consistent.

- [ ] **Step 7: Add public methods**

Add these methods after `clear_session()`:

```python
def get_session_id(self) -> Optional[str]:
    """Get current session ID if auto-save is enabled.
    
    Returns:
        Session ID string, or None if auto-save is disabled
    """
    return self._session_id if self._auto_save_session else None

@classmethod
def list_available_sessions(cls) -> List[SessionInfo]:
    """List all saved sessions from global storage.
    
    Returns:
        List of SessionInfo sorted by updated_at descending
    """
    manager = SessionManager.get_default()
    return manager.list_sessions()

def load_session(self, session_id: str) -> List[ChatMessage]:
    """Load a saved session into current instance.
    
    Chat history is loaded into both OpenAime and Planner.
    Clears any existing chat history.
    
    Args:
        session_id: Session identifier to load
    
    Returns:
        The loaded chat history
    
    Raises:
        ValueError if session not found
    """
    pass  # Implementation

def delete_current_session(self, confirm: bool = False) -> bool:
    """Delete the current session from storage.
    
    Args:
        confirm: Must be True for deletion to proceed (safety check)
    
    Returns:
        True if deleted successfully, False otherwise
    """
    pass  # Implementation
```

- [ ] **Step 8: Update `clear_session()` to also clear session**

In `clear_session()`:
```python
def clear_session(self) -> None:
    """Clear the current session context.
    This includes chat history, progress tracking, planner, and actor factory.
    """
    logger.debug("Clearing session context")
    self._chat_history.clear()
    self._session_id = None
    # Rest remains unchanged
```

- [ ] **Step 9: Test the integration**

```bash
python -c "from aime.aime import OpenAime; print('OK')"
```
Expected: No import errors

- [ ] **Step 10: Commit**

```bash
git add aime/aime.py
git commit -m "feat(session): integrate session persistence into OpenAime

- Add optional session parameters to __init__
- Add public methods: get_session_id, list_available_sessions, load_session, delete_current_session
- Fix: call _generate_execution_summary after completion and persist it
- Keep chat history synchronized between OpenAime and Planner

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Create comprehensive test suite

**Files:**
- Create: `tests/test_session_persistence.py`

- [ ] **Step 1: Write test cases**

Include these test cases:
1. `test_create_new_session` - creates session directory and files
2. `test_append_message` - appends message to JSONL, can read back
3. `test_list_sessions` - lists multiple sessions sorted correctly
4. `test_load_transcript` - loads full transcript correctly
5. `test_delete_session` - deletes session directory, requires confirm=True
6. `test_session_exists` - correctly reports existence
7. `test_backward_compatibility` - auto_save_session=False works unchanged
8. `test_load_session_into_openaime` - loads chat history into OpenAime and Planner
9. `test_crash_safety` - partial append doesn't corrupt existing data
10. `test_execution_summary_persisted` - execution summary is generated and correctly persisted as assistant message

Use a temporary directory for testing (`tempfile.TemporaryDirectory`).

- [ ] **Step 2: Run all tests**

```bash
python -m pytest tests/test_session_persistence.py -v
```
Expected: All tests pass

- [ ] **Step 3: Run all existing tests to ensure no regression**

```bash
python -m pytest tests/ -v
```
Expected: All existing tests still pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_session_persistence.py
git commit -m "test(session): add comprehensive test suite for session persistence

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Final verification and cleanup

- [ ] **Step 1: Run full test suite again**

```bash
python -m pytest tests/ -v
```
Expected: All 200+ tests pass (including new session tests)

- [ ] **Step 2: Check import sorting and lint**

```bash
ruff check aime/base/ aime/components/ aime/aime.py
```
Expected: No lint errors

- [ ] **Step 3: Commit any lint fixes**

If fixes needed:
```bash
git add ...
git commit -m "fix(session): fix lint issues"
```

---

## Summary

**Total changes:**
- 3 new files: `session.py`, `session_storage.py`, `session_manager.py`
- 3 modified files: `types.py`, `planner.py`, `aime.py`
- 1 new test file: `test_session_persistence.py`

After completing all tasks, the feature is ready for use. Example usage:

```python
import asyncio
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.providers.llm.anthropic import AnthropicLLM

llm = AnthropicLLM(api_key="...")

# New session with auto-save (default)
aime = OpenAime(config=AimeConfig(), llm=llm, workspace="./my-project")
result1 = await aime.run("Add a login endpoint to app.py")
session_id = aime.get_session_id()  # Save this for later

# ... later or after restart ...
aime2 = OpenAime(config=AimeConfig(), llm=llm, workspace="./my-project", session_id=session_id)
result2 = await aime2.run("Add JWT authentication to the login endpoint")
# Full context from first run is preserved!
```
