"""
Tests for DynamicActor component.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from aime.components.actor import DynamicActor
from aime.components.progress_module import ProgressModule
from aime.components.planner import Planner
from aime.base.config import ActorConfig
from aime.base.llm import BaseLLM, Message, LLMResponse
from aime.base.tool import Toolkit, ToolBundle, BaseTool, ToolResult
from aime.base.knowledge import BaseKnowledge, SimpleInMemoryKnowledge
from aime.base.types import Task, TaskStatus


class MockLLM(BaseLLM):
    """Mock LLM for testing."""

    def __init__(self, response_content: str = '{"tool": "test_tool", "parameters": {"test": "value"}}'):
        self.response_content = response_content

    async def complete(
        self,
        messages: list[Message],
        temperature: float | None = None,
        tools: list[dict[str, any]] | None = None,
    ) -> LLMResponse:
        return LLMResponse(content=self.response_content)

    async def complete_stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
        tools: list[dict[str, any]] | None = None,
    ):
        yield None


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(self, name: str = "test_tool", success: bool = True):
        self._name = name
        self._success = success

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Test tool"

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "test": {"type": "string"}
            },
            "required": ["test"]
        }

    async def execute(self, parameters: dict) -> ToolResult:
        if self._success:
            return ToolResult(
                success=True,
                content="Tool executed successfully",
            )
        else:
            return ToolResult(
                success=False,
                content="Tool failed to execute",
            )


@pytest.mark.asyncio
async def test_actor_creation():
    """Test creating a DynamicActor instance with new API."""
    # Create mock dependencies
    mock_planner = MagicMock(spec=Planner)
    mock_progress = MagicMock(spec=ProgressModule)
    mock_toolkit = MagicMock(spec=Toolkit)
    mock_knowledge = MagicMock(spec=BaseKnowledge)
    mock_llm = MagicMock(spec=BaseLLM)
    config = ActorConfig()

    # Create mock task
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_1"
    mock_task.description = "Test task"
    mock_task.completion_criteria = "Complete test task"

    # Create actor with new API
    actor = DynamicActor(
        actor_id="actor_1",
        role="Test Role",
        task=mock_task,
        llm=mock_llm,
        planner=mock_planner,
        progress=mock_progress,
        toolkit=mock_toolkit,
        knowledge=mock_knowledge,
        config=config
    )

    assert actor is not None
    assert actor.actor_id == "actor_1"
    assert actor.role == "Test Role"
    assert actor.task == mock_task
    assert actor.llm == mock_llm
    assert actor.planner == mock_planner
    assert actor.progress == mock_progress
    assert actor.toolkit == mock_toolkit
    assert actor.knowledge == mock_knowledge
    assert actor.config == config


@pytest.mark.asyncio
async def test_actor_basic_execution_flow():
    """Test actor executes a task with a tool using new run() method."""
    # Create real progress module with task
    progress = ProgressModule()
    task = await progress.add_task("Test task", "Complete test task")

    # Create real tool and toolkit
    test_tool = MockTool()
    toolkit = MagicMock(spec=Toolkit)
    toolkit.get_all_tools.return_value = [test_tool]
    toolkit.get_tool_by_name.return_value = test_tool

    # Create mock planner
    mock_planner = MagicMock(spec=Planner)

    # Create LLM that responds with finish action
    class FinishMockLLM(BaseLLM):
        async def complete(self, messages: list[Message], temperature: float | None = None, tools: list[dict[str, any]] | None = None) -> LLMResponse:
            return LLMResponse(content='THOUGHT: Task is complete\nACTION: {"tool": "finish", "parameters": {"summary": "Done"}}')

        async def complete_stream(self, messages: list[Message], temperature: float | None = None, tools: list[dict[str, any]] | None = None):
            yield None

    mock_llm = FinishMockLLM()

    # Create actor with new API and run it
    config = ActorConfig()
    actor = DynamicActor(
        actor_id="actor_1",
        role="Test Executor",
        task=task,
        llm=mock_llm,
        planner=mock_planner,
        progress=progress,
        toolkit=toolkit,
        knowledge=SimpleInMemoryKnowledge(),
        config=config
    )

    result = await actor.run()

    # Verify task was processed
    updated_task = await progress.get_task(task.id)
    assert updated_task is not None
    assert result.status == TaskStatus.COMPLETED
    assert updated_task.status == TaskStatus.COMPLETED

    # Verify task was processed
    updated_task = await progress.get_task(task.id)
    assert updated_task is not None
    assert updated_task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)


@pytest.mark.asyncio
async def test_actor_with_no_tools():
    """Test actor handling case with no tools available using new API."""
    # Create real progress module with task
    progress = ProgressModule()
    task = await progress.add_task("Test task", "Complete test task")

    # Create toolkit with no tools
    toolkit = MagicMock(spec=Toolkit)
    toolkit.get_all_tools.return_value = []

    # Create mock planner
    mock_planner = MagicMock(spec=Planner)

    # Create mock LLM
    mock_llm = MockLLM()

    # Create actor and run it
    config = ActorConfig()
    actor = DynamicActor(
        actor_id="actor_1",
        role="Test Executor",
        task=task,
        llm=mock_llm,
        planner=mock_planner,
        progress=progress,
        toolkit=toolkit,
        knowledge=SimpleInMemoryKnowledge(),
        config=config
    )

    result = await actor.run()

    # Verify task failed
    updated_task = await progress.get_task(task.id)
    assert updated_task is not None
    assert result.status == TaskStatus.FAILED
    assert updated_task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_actor_tool_selection():
    """Test actor tool selection via LLM using new API."""
    # Create real progress module with task
    progress = ProgressModule()
    task = await progress.add_task("Test task", "Complete test task")

    # Create real tool and toolkit
    test_tool = MockTool()
    toolkit = MagicMock(spec=Toolkit)
    toolkit.get_all_tools.return_value = [test_tool]
    toolkit.get_tool_by_name.return_value = test_tool

    # Create mock planner
    mock_planner = MagicMock(spec=Planner)

    # Create mock LLM with specific tool selection response
    mock_llm = MockLLM('THOUGHT: I need to use the test tool\nACTION: {"tool": "test_tool", "parameters": {"test": "value"}}')

    # Create actor and run it
    config = ActorConfig()
    actor = DynamicActor(
        actor_id="actor_1",
        role="Test Executor",
        task=task,
        llm=mock_llm,
        planner=mock_planner,
        progress=progress,
        toolkit=toolkit,
        knowledge=SimpleInMemoryKnowledge(),
        config=config
    )

    # We need to limit iterations since we're not testing full completion
    config.max_iterations = 1
    result = await actor.run()

    # Verify task was processed (will fail due to max iterations, but that's expected)
    updated_task = await progress.get_task(task.id)
    assert updated_task is not None


@pytest.mark.asyncio
async def test_actor_with_failed_task():
    """Test actor handles task failure with retries using new API."""
    # Create real progress module with task
    progress = ProgressModule()
    task = await progress.add_task("Test task", "Complete test task")

    # Create failing tool
    test_tool = MockTool(success=False)
    toolkit = MagicMock(spec=Toolkit)
    toolkit.get_all_tools.return_value = [test_tool]
    toolkit.get_tool_by_name.return_value = test_tool

    # Create mock planner
    mock_planner = MagicMock(spec=Planner)

    # Create mock LLM
    mock_llm = MockLLM('THOUGHT: I need to use the test tool\nACTION: {"tool": "test_tool", "parameters": {"test": "value"}}')

    # Create actor and run it with limited retries
    config = ActorConfig(max_retries=1)
    actor = DynamicActor(
        actor_id="actor_1",
        role="Test Executor",
        task=task,
        llm=mock_llm,
        planner=mock_planner,
        progress=progress,
        toolkit=toolkit,
        knowledge=SimpleInMemoryKnowledge(),
        config=config
    )

    result = await actor.run()

    # Verify task failed after retries
    updated_task = await progress.get_task(task.id)
    assert updated_task is not None
    assert result.status == TaskStatus.FAILED
    assert updated_task.status == TaskStatus.FAILED
