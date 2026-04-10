import pytest
from unittest.mock import AsyncMock, MagicMock

from aime.components.actor_factory import ActorFactory
from aime.components.actor import DynamicActor
from aime.components.planner import Planner
from aime.components.progress_module import ProgressModule
from aime.base.types import Task, TaskStatus, ActorRecord
from aime.base.config import ActorConfig
from aime.base.llm import BaseLLM, Message, LLMResponse
from aime.base.tool import Toolkit, ToolBundle, BaseTool
from aime.base.knowledge import BaseKnowledge


class MockLLM(BaseLLM):
    """Mock LLM for testing."""

    def __init__(self, response_content: str = '{"tool": "test_tool", "parameters": {"test": "value"}}'):
        self.response_content = response_content

    async def complete(
        self,
        messages: list[Message],
        temperature: float | None = None,
    ) -> LLMResponse:
        return LLMResponse(content=self.response_content)

    async def complete_stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
    ):
        yield None


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(self, name: str = "test_tool"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Test tool"

    def get_input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, parameters: dict):
        return {"success": True, "content": "Done"}


def test_actor_factory_initialization():
    mock_llm = MockLLM()
    actor_config = ActorConfig()
    factory = ActorFactory(mock_llm, actor_config)
    assert factory._actor_counter == 0
    assert len(factory._actors) == 0
    assert len(factory.get_available_tool_bundles()) == 0


def test_actor_factory_register_bundle():
    mock_llm = MockLLM()
    actor_config = ActorConfig()
    sample_tool_bundle = ToolBundle(name="test_bundle", description="Test bundle", tools=[])
    factory = ActorFactory(mock_llm, actor_config)
    factory.register_tool_bundle(sample_tool_bundle)
    assert sample_tool_bundle.name in factory.get_available_tool_bundles()


def test_list_actors_empty():
    mock_llm = MockLLM()
    actor_config = ActorConfig()
    factory = ActorFactory(mock_llm, actor_config)
    assert len(factory.list_actors()) == 0


def test_clear_actors():
    mock_llm = MockLLM()
    actor_config = ActorConfig()
    factory = ActorFactory(mock_llm, actor_config)
    # Add a dummy actor manually
    mock_actor = MagicMock(spec=DynamicActor)
    record = ActorRecord(
        actor_id="test",
        role="test",
        description="test",
        tool_bundles=[]
    )
    factory._actors["test"] = (mock_actor, record)
    assert len(factory._actors) == 1
    factory.clear_actors()
    assert len(factory._actors) == 0


@pytest.mark.asyncio
async def test_create_new_actor_when_cache_empty():
    mock_llm = MockLLM()
    actor_config = ActorConfig()
    mock_planner = MagicMock(spec=Planner)
    mock_progress = MagicMock(spec=ProgressModule)
    mock_knowledge = MagicMock(spec=BaseKnowledge)
    # Create sample task
    sample_task = Task(
        id="test-task-1",
        description="Test task description",
        status=TaskStatus.PENDING,
        parent_id=None,
        completion_criteria="Task is complete",
        dependencies=[]
    )
    factory = ActorFactory(mock_llm, actor_config)
    # Should create new when empty
    actor = await factory.create_actor(sample_task, mock_planner, mock_progress, mock_knowledge)
    assert isinstance(actor, DynamicActor)
    assert len(factory.list_actors()) == 1

