# LLM 流式输出改造实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AIME 框架中 actor 对 LLM 的调用改为流式输出，实现 thought 过程增量实时显示到 TUI，改善用户交互体验。

**Architecture:** `LLMResponseChunk` 和 `complete_stream` 已经在基类和三个 providers 中实现。只需更新基类方法签名添加 `tools` 参数，修改 actor 主循环使用流式接口累积响应并发送增量事件到 TUI，TUI 实时更新显示。工具调用仍等待完整响应累积完成后再解析执行。完全保持向后兼容，原有 `complete()` 方法不变。

**Tech Stack:** Python asyncio, AsyncIterator for streaming, Anthropic/OpenAI/Volcengine native streaming APIs, Textual TUI incremental updates.

---

## 文件修改概览

| 文件 | 操作 | 职责 |
|------|------|------|
| `aime/base/llm.py` | 修改 | 更新 `complete_stream` 抽象方法签名添加 `tools` 参数 |
| `aime/base/events.py` | 修改 | 新增 `ACTOR_INCREMENTAL_OUTPUT` 事件类型 |
| `aime/components/actor.py` | 修改 | `_react_loop` 改用 `complete_stream`，累积 chunks，增量发送事件 |
| `tests/components/test_actor.py` | 修改 | 更新测试适应流式 |
| `aime_tui/app.py` | 修改 | 订阅 `ACTOR_INCREMENTAL_OUTPUT` 事件 |
| `aime_tui/components/event_stream.py` | 修改 | 支持增量更新显示，添加 `add_incremental_output` 方法 |

总计：6 个文件修改。(`LLMResponseChunk` 和三个 providers 的 `complete_stream` 已经存在且实现正确)

---

### Task 1: 更新基类 complete_stream 签名添加 tools 参数

**Files:**
- Modify: `aime/base/llm.py`
- Test: `tests/base/test_llm.py`

- [ ] **Step 1: Update complete_stream signature in BaseLLM**

Find the `complete_stream` method:
```python
@abstractmethod
async def complete_stream(
    self,
    messages: list[Message],
    temperature: Optional[float] = None,
) -> AsyncIterator[LLMResponseChunk]:
    """Stream the response."""
    pass
```

Update it to add `tools` parameter:
```python
@abstractmethod
async def complete_stream(
    self,
    messages: list[Message],
    temperature: Optional[float] = None,
    tools: Optional[List[dict[str, Any]]] = None,
) -> AsyncIterator[LLMResponseChunk]:
    """Stream the response.

    Args:
        messages: List of conversation messages
        temperature: Sampling temperature
        tools: Optional list of tool definitions for native tool calling
    """
    pass
```

- [ ] **Step 2: Verify existing tests still pass**

Run:
```bash
python -m pytest tests/base/test_llm.py -v
```
Expected: All existing tests still pass.

- [ ] **Step 3: Commit**

```bash
git add aime/base/llm.py
git commit -m "fix: add tools parameter to complete_stream abstract method"
```

---

### Task 2: 添加 ACTOR_INCREMENTAL_OUTPUT 事件类型

**Files:**
- Modify: `aime/base/events.py`

- [ ] **Step 1: Add new event type to EventType class**

Add this line:
```python
ACTOR_INCREMENTAL_OUTPUT = "actor_incremental_output"
```

- [ ] **Step 2: Verify no syntax errors**

Run:
```bash
python -m pytest tests/base/test_events.py -v 2>/dev/null || python -c "from aime.base.events import EventType; print('import ok')"
```
Expected: No syntax errors.

- [ ] **Step 3: Commit**

```bash
git add aime/base/events.py
git commit -m "feat: add ACTOR_INCREMENTAL_OUTPUT event type"
```

---

### Task 3: 修改 actor.py _react_loop 使用流式接口

**Files:**
- Modify: `aime/components/actor.py`
- Test: `tests/components/test_actor.py`

- [ ] **Step 1: Ensure imports**

Verify these imports exist at top:
```python
from aime.base.llm import LLMResponseChunk, LLMResponse
from aime.base.events import EventType
```

Add if missing.

- [ ] **Step 2: Replace complete call with complete_stream in _react_loop**

Find this section in `_react_loop`:
```python
# Get LLM response
if self.config.use_native_function_calling:
    # Use native function calling
    response = await self.llm.complete(
        messages,
        temperature=self.config.temperature,
        tools=tool_defs,
    )
```

Replace with:
```python
# Get LLM response with streaming - incremental output to TUI
if self.config.use_native_function_calling:
    # Use native function calling with streaming
    full_content: list[str] = []
    tool_calls: list[ToolCall] = []

    async for chunk in self.llm.complete_stream(
        messages,
        temperature=self.config.temperature,
        tools=tool_defs,
    ):
        if chunk.content is not None:
            full_content.append(chunk.content)
            # Send incremental output event for TUI real-time display
            if self.emit_event:
                self.emit_event(EventType.ACTOR_INCREMENTAL_OUTPUT, {
                    "actor_id": self.actor_id,
                    "actor_name": self.name,
                    "text": chunk.content,
                    "full_text_so_far": "".join(full_content),
                })
        if chunk.tool_call_delta is not None:
            tool_calls.append(chunk.tool_call_delta)
        # is_final indicates the last chunk
        # No special action needed until streaming completes

    # Create complete response compatible with existing code
    full_text = "".join(full_content) if full_content else None
    response = LLMResponse(
        content=full_text,
        tool_calls=tool_calls,
    )
```

- [ ] **Step 3: Run existing tests**

Run:
```bash
python -m pytest tests/components/test_actor.py -v
```
Expected: Tests pass (update tests if needed).

- [ ] **Step 4: Fix any failing tests**

If tests fail, fix them.

- [ ] **Step 5: Commit**

```bash
git add aime/components/actor.py tests/components/test_actor.py
git commit -m "feat(actor): change _react_loop to use complete_stream with incremental output"
```

---

### Task 4: TUI - App 订阅增量输出事件

**Files:**
- Modify: `aime_tui/app.py`

- [ ] **Step 1: Add import for ACTOR_INCREMENTAL_OUTPUT**

Find where `EventType` is imported, add `ACTOR_INCREMENTAL_OUTPUT`:
```python
from aime.base.events import EventType
```

- [ ] **Step 2: Add event handler subscription**

In `_subscribe_events` method (where other events are subscribed), add:
```python
self.subscribe(EventType.ACTOR_INCREMENTAL_OUTPUT, self._on_actor_incremental_output)
```

- [ ] **Step 3: Implement _on_actor_incremental_output method**

Add method:
```python
def _on_actor_incremental_output(self, event_type: EventType, event_data: dict[str, Any]) -> None:
    """Handle incremental actor output for real-time display."""
    self.event_stream.add_incremental_output(event_data)
```

- [ ] **Step 4: Verify syntax**

Run:
```bash
python -c "import aime_tui.app; print('import ok')"
```
Expected: No syntax errors.

- [ ] **Step 5: Commit**

```bash
git add aime_tui/app.py
git commit -m "feat(tui): subscribe to ACTOR_INCREMENTAL_OUTPUT event"
```

---

### Task 5: TUI - EventStream 支持增量更新

**Files:**
- Modify: `aime_tui/components/event_stream.py`

Current code: This component inherits from `RichLog` from Textual.

- [ ] **Step 1: Add import and state**

Add at top if not present:
```python
from typing import Optional
```

Add instance variable in `__init__`:
```python
self._current_incremental: Optional[dict[str, Any]] = None
```

- [ ] **Step 2: Implement add_incremental_output method**

Add method after `add_event`:
```python
def add_incremental_output(self, event_data: dict[str, Any]) -> None:
    """Add or update incremental thought output in real-time.

    Updates the last event entry rather than creating a new event for each chunk,
    which provides smoother real-time display.
    """
    from textual.widgets import Static

    actor_name = event_data.get("actor_name", "actor")
    full_text = event_data.get("full_text_so_far", "")

    # Check if we're still updating the same incremental thought from same actor
    if (self._current_incremental is not None and
        self._current_incremental.get("actor_id") == event_data.get("actor_id")):
        # Update existing - the last widget we added is this incremental entry
        if self.children:
            last_child = self.children[-1]
            if isinstance(last_child, Static):
                last_child.update(f"🤖 **{actor_name}**\n{full_text}")
        self._current_incremental = event_data
    else:
        # Start a new incremental event entry
        self._current_incremental = event_data
        self.write(f"🤖 **{actor_name}**\n{full_text}")

    # Scroll to bottom to show latest content
    self.scroll_end(animate=False)
```

- [ ] **Step 3: Reset incremental tracker when new event is added**

Modify the existing `add_event` method: add this line at the end:
```python
def add_event(...):
    # ... existing code ...
    # Reset incremental tracker when a complete event is added
    self._current_incremental = None
```

- [ ] **Step 4: Verify syntax**

Run:
```bash
python -c "import aime_tui.components.event_stream; print('import ok')"
```
Expected: No syntax errors.

- [ ] **Step 5: Commit**

```bash
git add aime_tui/components/event_stream.py
git commit -m "feat(tui-event-stream): add incremental output support for streaming LLM"
```

---

### Task 6: 运行完整测试套件验证功能

**Files:** All modified files

- [ ] **Step 1: Run all tests**

Run:
```bash
python -m pytest tests/ -v
```
Expected: All 236+ tests pass.

- [ ] **Step 2: Fix any failures**

If any tests fail, fix them.

- [ ] **Step 3: Commit any fixes**

```bash
git add .
git commit -m "fix: fix failing tests after streaming changes"
```

---

## 验收标准

- [x] 基类 `complete_stream` 签名已更新添加 `tools` 参数
- [x] `actor._react_loop` 使用流式输出，增量发送事件
- [x] `ACTOR_INCREMENTAL_OUTPUT` 事件已添加
- [x] TUI 订阅事件并支持增量更新显示
- [x] TUI 实时显示 incremental thought，滚动到底部
- [x] 工具调用累积 `tool_call_delta` 完整后正常工作
- [x] 所有现有测试通过
- [x] 向后兼容 - `complete()` 方法仍然可用
