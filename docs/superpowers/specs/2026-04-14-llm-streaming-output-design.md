# LLM 流式输出改造设计文档

## 概述

对 AIME 框架中 actor 对 LLM 的调用进行流式改造，实现增量输出到 TUI，让用户实时看到 actor 的思考过程，改善交互体验。

## 目标

- **用户体验**：用户无需等待完整响应，可实时看到思考过程逐步输出
- **向后兼容**：不破坏现有 API，所有现有代码保持可用
- **实现简洁**：避免过度复杂的增量解析，在体验和复杂度之间取得平衡
- **全覆盖**：所有三个 LLM providers (Anthropic, OpenAI, Volcengine) 都支持流式

## 方案选择

考虑了三个方案：

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **方案 1：增量改造** | 只给 base llm 添加流式接口，actor 逐步改造 | 对现有代码改动最小，不破坏现有结构 | 需要修改 actor 主循环，仍然需要攒完整响应才能处理工具调用 |
| **方案 2：全流式工具调用** | 工具调用也流式解析 | 真正全程流式，体验最好 | 增量解析工具调用复杂，容易出错，改动大 |
| **方案 3：混合** | thought 流式输出，工具调用等待完整 | 兼顾体验和实现简单，thought 实时显示，工具调用等待完整 | thought 已经能满足实时观看体验，工具调用本来就需要完整才能解析 |

**最终选择：方案 3 - 混合方案**

理由：
1. 用户最想实时看到的就是思考过程，这一需求已经满足
2. 工具调用必须获得完整参数才能执行，等待完整是合理的
3. 实现复杂度最低，风险最小，改动量可控

## 架构设计

### 之前架构

```
actor.run() -> _react_loop() -> llm.complete() -> [等待完整响应] -> 解析工具调用 -> 执行 -> 重复
```

### 改造后架构

```
actor.run() -> _react_loop() -> llm.complete_stream() -> 
  for chunk in stream:
    累积文本 ->
    发送增量事件到 TUI -> TUI 实时更新显示
  流式结束后获得完整响应 ->
  解析工具调用 -> 执行 -> 添加观察 -> 重复
```

## 详细设计

### 1. 基类扩展 `aime/base/llm.py`

新增 `LLMResponseChunk` 数据类：

```python
@dataclass
class LLMResponseChunk:
    """A single chunk of streaming response from LLM."""
    text: str
    is_done: bool = False
    tool_calls: Optional[list[dict]] = None
```

`BaseLLM` 新增抽象方法：

```python
async def complete_stream(
    self,
    messages: list[Message],
    *,
    temperature: float = 0.0,
    tools: Optional[list[dict]] = None,
) -> AsyncIterator[LLMResponseChunk]:
    """Stream LLM completion token by token.
    
    Args:
        messages: Input messages
        temperature: Sampling temperature
        tools: List of tool definitions (for native function calling)
    
    Yields:
        LLMResponseChunk chunks incrementally. The last chunk has is_done=True.
    """
    raise NotImplementedError("Subclasses must implement complete_stream")
```

保持原有的 `complete()` 方法不变，向后兼容。

### 2. LLM Provider 实现

每个 provider 需要实现 `complete_stream` 方法：

| Provider | 实现方式 |
|----------|----------|
| Anthropic | 使用 Anthropic Messages API with `stream=True` |
| OpenAI | 使用 OpenAI Chat Completions API with `stream=True` |
| Volcengine | 使用火山引擎流式 API |

每个实现逐块读取响应，yield `LLMResponseChunk`。

**关于 tool_calls**:
- 根据原生 function calling 的设计，tool_calls 只会在**最后一个 chunk**完整返回
- 如果某个 provider 在流式传输过程中提前返回部分 tool_calls，实现会累积覆盖 `tool_calls` 变量，最终结果仍然正确
- 流式结束后，`tool_calls` 持有完整工具调用信息供后续处理

### 3. 新增事件类型 `aime/base/events.py`

```python
ACTOR_INCREMENTAL_OUTPUT = "actor_incremental_output"
```

事件 payload：
- `actor_id`: actor ID
- `actor_name`: actor name (用于显示)
- `text`: 当前增量的文本片段
- `full_text_so_far`: 累积到目前的完整文本

### 4. Actor 主循环改造 `aime/components/actor.py`

`_react_loop` 中原有的：

```python
response = await self.llm.complete(messages, temperature=..., tools=tool_defs)
```

改为：

```python
full_text = ""
tool_calls = None

# 流式接收
async for chunk in self.llm.complete_stream(messages, temperature=..., tools=tool_defs):
    full_text += chunk.text
    if chunk.text and self.emit_event:
        # 发送增量事件到 TUI 实时显示
        self.emit_event(EventType.ACTOR_INCREMENTAL_OUTPUT, {
            "actor_id": self.actor_id,
            "actor_name": self.name,
            "text": chunk.text,
            "full_text_so_far": full_text,
        })
    if chunk.tool_calls:
        tool_calls = chunk.tool_calls
# 流式结束，full_text 和 tool_calls 准备好了
```

后续解析和处理逻辑保持不变。

### 5. TUI 支持增量显示

- `aime_tui/app.py`: 订阅 `ACTOR_INCREMENTAL_OUTPUT` 事件
- `aime_tui/components/event_stream.py`: 支持增量更新最后一个活跃事件，而不是每次都新增事件
- 收到增量后自动滚动到底部，让用户看到最新内容

## 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `aime/base/llm.py` | 修改 | 新增 `LLMResponseChunk`，新增 `complete_stream` 抽象方法 |
| `aime/providers/llm/anthropic.py` | 修改 | 实现 `complete_stream` |
| `aime/providers/llm/openai.py` | 修改 | 实现 `complete_stream` |
| `aime/providers/llm/volcengine.py` | 修改 | 实现 `complete_stream` |
| `aime/base/events.py` | 修改 | 新增 `ACTOR_INCREMENTAL_OUTPUT` 事件类型 |
| `aime/components/actor.py` | 修改 | `_react_loop` 改用流式接口 |
| `aime_tui/app.py` | 修改 | 订阅增量事件 |
| `aime_tui/components/event_stream.py` | 修改 | 支持增量更新显示 |

总计：8 个文件修改。

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 流式传输中断 | 使用已累积的文本继续处理，可能导致工具调用解析失败，进入正常重试流程 |
| TUI 显示错误 | 不影响核心执行逻辑，仅记录日志继续执行 |
| Provider 未实现 | 抛出 `NotImplementedError` 明确提示 |

## 向后兼容

- 原有的 `complete()` 方法保持不变
- 所有现有调用方式仍然可用
- 只有 actor 主循环改用流式，不影响其他调用者

## 测试计划

### 单元测试
- 每个 provider 的 `complete_stream` 能正确产生 chunks
- 验证流式结束后 `is_done` 标志正确设置
- 验证 tool_calls 在最后一个 chunk 正确返回

### 集成测试
- 测试短 thought 流式输出，验证增量事件正确发送
- 测试长 thought 流式输出，验证 TUI 增量更新正常
- 测试带工具调用的流式输出，验证工具调用解析正确
- 测试流式传输中断（连接断开），验证已累积文本能正常处理，进入重试流程
- 测试 TUI 增量更新性能，验证大流量增量不会卡住 UI

### 回归测试
- 运行全部现有测试用例，确保原有功能正常
- 验证 `complete()` 方法仍然可用（向后兼容）

### 性能测试
- 测试长文本流式输出的内存使用
- 验证高频率 TUI 更新不会造成明显卡顿

## 性能考虑

### Chunk 大小和更新频率
- LLM API 通常以 token 为单位流式返回，每个 token 对应一个 chunk
- 每个 chunk 都会触发一次 TUI 更新，这在当前设计下是可接受的
- 对于极快的流式输出，TUI 框架 (Textual) 能够处理高频更新

### 内存使用
- `full_text` 在每次 react 循环迭代结束后会被丢弃，由 GC 回收
- 长流式响应（数千 token）累积的文本仍然在合理内存范围内
- 最坏情况：如果超出内存限制，Python GC 会处理，不影响进程稳定性

### 优化空间
- 如果未来出现性能问题，可以考虑：
  - 对极高频增量进行防抖（比如最多 100ms 更新一次 TUI）
  - 累积多个 chunks 再一次性发送事件
  - 当前设计不预做这些优化，因为经验表明现有方式已经足够流畅

## 风险评估

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 某个 provider 流式 API 接口不兼容 | 单个 provider 无法使用 | 详细测试每个 provider，保持非流式接口作为后备 |
| TUI 增量更新引入显示问题 | 显示问题不影响执行 | 充分测试，保持原有显示方式作为备选 |
| 内存泄漏（流式累积） | 可忽略，每次迭代后 full_text 会被丢弃 | 每次 react 循环重新创建变量，GC 会回收 |
| 高频 TUI 更新导致卡顿 | 影响用户体验，不影响执行 | 实测观察，如果出现问题再加防抖优化 |
