# OpenAime

中文版 | [English](./README.md)

开源实现 **AIME (Autonomous Interactive Execution Engine)** 框架 - 基于大语言模型的全自动软件工程智能体框架。

## 什么是 AIME

AIME 是 [AIME 论文](https://arxiv.org/abs/2506.1234) 中描述的多智能体自主执行架构，旨在让 AI 智能体全自动完成复杂的软件工程任务，例如：

- 在现有代码库中调试修复 Bug
- 根据需求实现新功能
- 重构和改进代码质量
- 代码审查和分析
- 从头开始开发整个项目

核心思想是 **动态规划 + 专业化智能体执行**：
- **规划器 (Planner)**：根据当前进度持续重新规划任务
- **智能体工厂 (Actor Factory)**：根据所需能力创建或复用专业化智能体
- **进度模块 (Progress Module)**：集中式进度跟踪，支持实时更新
- **原生工具调用**：充分利用 LLM 提供商的原生函数调用能力，提高可靠性

## 和 Claude Code 的区别

| 特性 | OpenAime | Claude Code |
|---------|----------|-------------|
| **架构** | 规划器 + 智能体 + 进度模块 - 动态任务规划，支持并行智能体执行 | 顺序工具执行 |
| **语言** | Python | TypeScript |
| **可嵌入** | 可作为 Python 包导入，集成到任何应用 | 仅独立 CLI |
| **智能体复用** | 自动复用已有匹配能力的智能体 | 每轮创建新上下文 |
| **动态任务管理** | 执行中支持添加/修改/删除任务 | 固定单轮规划 |
| **会话持久化** | 完整会话保存/加载，随时可恢复 | 无内置持久化 |
| **MCP 支持** | 完整 MCP (Model Context Protocol) 工具集成 | 支持 MCP |
| **终端界面** | 内置终端 UI，实时进度跟踪 | 内置终端 UI |

## 功能特性

- ✅ **动态规划器**：支持动态任务操作（添加/修改/删除/标记失败）
- ✅ **智能体复用**：基于能力匹配的智能体复用，避免重复工作
- ✅ **防止重复劳动**：所有智能体可见完整进度上下文
- ✅ **原生函数调用**：纯原生工具调用，避免 JSON 解析错误
- ✅ **多家 LLM 提供商**：支持 OpenAI、Anthropic、火山引擎（豆包）
- ✅ **MCP 集成**：完整支持 MCP (Model Context Protocol) 客户端
- ✅ **交互式用户提问**：智能体可通过 TUI 对话框向用户提问获取决策
- ✅ **会话持久化**：完整会话保存到磁盘，随时可恢复
- ✅ **美观终端界面**：实时事件流、进度树、增量输出
- ✅ **技能系统**：模块化能力扩展，支持热重载
- ✅ **工作空间隔离**：正确的工作目录管理

## 快速开始

### 安装

```bash
pip install openaime
# 或者使用 uv
uv add openaime
```

### 安装可选 TUI 依赖：
```bash
pip install openaime[tui]
```

### 基本使用

```python
import asyncio
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.providers.llm.anthropic import AnthropicLLM

# 创建 LLM 提供商
llm = AnthropicLLM(api_key="你的-api-key")

# 创建 OpenAime 实例
aime = OpenAime(
    config=AimeConfig(),
    llm=llm,
    workspace="./你的项目目录"
)

# 运行自主智能体完成目标
result = await aime.run("修复 login 模块中的 bug")
print(result)
```

### 多轮对话

```python
# 第一个请求
result1 = await aime.run("给 app.py 添加一个 login 接口")
print(result1)

# 第二个请求 - 保留完整上下文！
result2 = await aime.run("现在给这个接口添加 JWT 认证")
print(result2)

# 需要可以开始全新会话
aime.clear_session()
result3 = await aime.run("一个全新的任务在这里", new_goal=True)
```

## 集成到你自己的应用

OpenAime 设计为库，你可以嵌入到自己的 Python 应用中。你可以监听事件进行 UI 集成或日志记录。

```python
import asyncio
import logging
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.base.events import EventType, AimeEvent
from aime.providers.llm.openai import OpenAILLM

def my_event_callback(event: AimeEvent):
    """自定义事件回调处理 OpenAime 发出的事件."""
    event_type = event.event_type
    data = event.data

    if event_type == EventType.ACTOR_INCREMENTAL_OUTPUT:
        # 处理流式思考输出
        actor_name = data.get("actor_name", "")
        text = data.get("text", "")
        full_text = data.get("full_text_so_far", "")
        print(f"[{actor_name}] {text}")  # 增量更新 UI

    elif event_type == EventType.ACTOR_TOOL_CALLED:
        # 智能体调用了工具
        logging.info(f"调用工具: {data.get('tool_name')}")

    elif event_type == EventType.TASK_STATUS_CHANGED:
        # 任务状态更新
        pass

llm = OpenAILLM(api_key="你的-api-key")
aime = OpenAime(
    config=AimeConfig(),
    llm=llm,
    workspace="./workspace",
    event_callback=my_event_callback,
)

result = await aime.run("实现一个简单的 Python HTTP 服务器")
```

## 支持的事件

| 事件类型 | 描述 | 数据字段 |
|------------|-------------|-------------|
| `PLANNER_GOAL_STARTED` | 规划器开始处理新目标 | 无 |
| `PLANNER_STEP_COMPLETED` | 规划器完成一步规划 | `action`, `thought` |
| `ACTOR_STARTED` | 智能体开始执行子任务 | `actor_id`, `actor_name`, `task_description` |
| `ACTOR_INCREMENTAL_OUTPUT` | 智能体增量思考输出（流式） | `actor_id`, `actor_name`, `text`, `full_text_so_far` |
| `ACTOR_THOUGHT` | 智能体完整思考（非流式） | `actor_id`, `actor_name`, `thought` |
| `ACTOR_TOOL_CALLED` | 智能体调用工具 | `actor_id`, `tool_name`, `parameters` |
| `ACTOR_TOOL_FINISHED` | 智能体工具执行完成 | `actor_id`, `tool_name`, `success`, `content` |
| `ACTOR_COMPLETED` | 智能体完成子任务执行 | `actor_id`, `result` |
| `TASK_STATUS_CHANGED` | 任务状态变更（等待 → 执行中 → 完成/失败） | `task_id`, `status` |
| `GOAL_COMPLETED` | 整体目标完成 | `summary`, `total_iterations` |
| `USER_QUESTION_ASKED` | 智能体请求用户回答 | `question` |
| `USER_QUESTION_ANSWERED` | 用户回答了问题 | `answers` |

## 使用终端界面

从命令行使用时，OpenAime 提供交互式终端 UI：

```bash
# 安装后直接启动 TUI
openaime
```

### 命令

| 命令 | 描述 |
|---------|-------------|
| `/goal <描述>` | 开始新的自主目标执行 |
| `/clear` | 清空当前会话 |
| `/sessions` | 列出已保存会话，点击恢复 |
| `/layout horizontal` / `layout vertical` | 切换布局 |
| `/quit` | 退出 TUI |

## 项目结构

```
aime/
├── base/                      # 基础抽象和类型定义
│   ├── llm.py                # LLM 基础接口 (BaseLLM)
│   ├── types.py              # 核心数据类 (Task, ProgressList, ActorRecord 等)
│   ├── tool.py               # 工具基础接口 (BaseTool, Toolkit, ToolBundle)
│   ├── config.py             # 配置类
│   ├── skill.py              # 技能元数据和注册（热重载）
│   ├── knowledge.py          # 知识库抽象
│   ├── user_question.py      # 用户提问管理器
│   └── session/              # 会话持久化
├── components/               # 核心业务组件
│   ├── actor.py              # DynamicActor 带 ReAct 流式循环
│   ├── actor_factory.py      # ActorFactory 基于能力匹配的智能体复用
│   ├── planner.py            # 动态规划器，支持任务变更
│   └── progress_module.py    # 进度跟踪和事件订阅
├── providers/                # 提供商实现
│   ├── llm/                  # LLM 提供商
│   │   ├── openai.py         # OpenAI (GPT-4o 等)
│   │   ├── anthropic.py      # Anthropic (Claude 3.5/3.7)
│   │   └── volcengine.py     # 火山引擎 豆包
│   └── tools/                # 工具提供商
│       └── mcp.py            # MCP (Model Context Protocol) 客户端
├── tools/                    # 内置工具
│   └── builtin/              # 核心内置工具
│       ├── file_read.py      # 读取文本文件
│       ├── file_write.py     # 写入文本文件
│       ├── file_update.py    # 更新现有文件（搜索/替换，追加）
│       ├── shell_exec.py     # 执行 shell 命令
│       └── ask_user_question.py # 向用户交互式提问
├── aime.py                   # 主 OpenAime 入口
└── aime_tui/                 # 终端用户界面
    ├── app.py               # 主 TUI 应用
    ├── components/          # TUI 组件（事件流、进度面板等）
    ├── assets/              # CSS 样式
    └── config.py            # TUI 配置
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE)。

## 致谢

基于 AIME 论文描述的架构实现。
