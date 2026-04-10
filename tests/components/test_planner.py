"""
Tests for Planner component.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from aime.components.planner import Planner
from aime.components.progress_module import ProgressModule
from aime.base.types import PlannerOutput, TaskStatus
from aime.base.config import PlannerConfig
from aime.base.llm import BaseLLM, Message, LLMResponse


class MockLLM(BaseLLM):
    """Mock LLM for testing Planner."""

    def __init__(self, response_content: str = "dispatch_subtask"):
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


@pytest.mark.asyncio
async def test_planner_initialization():
    """Test creating a Planner instance."""
    mock_llm = MockLLM()
    config = PlannerConfig()
    planner = Planner(mock_llm, config)

    assert planner is not None
    assert planner.base_llm == mock_llm
    assert planner.config == config
    assert planner.goal is None


@pytest.mark.asyncio
async def test_initialize_with_goal():
    """Test initializing the planner with a root goal."""
    mock_llm = MockLLM()
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)

    assert planner.goal == "Test goal"


@pytest.mark.asyncio
async def test_plan_step_not_initialized():
    """Test that plan_step raises error when planner not initialized."""
    mock_llm = MockLLM()
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    with pytest.raises(RuntimeError, match="Planner not initialized"):
        await planner.plan_step(progress)


@pytest.mark.asyncio
async def test_plan_step_returns_dispatch_subtask():
    """Test plan_step returns dispatch_subtask action."""
    mock_llm = MockLLM("dispatch_subtask")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    output = await planner.plan_step(progress)

    assert isinstance(output, PlannerOutput)
    assert output.action == PlannerOutput.Action.DISPATCH_SUBTASK


@pytest.mark.asyncio
async def test_plan_step_returns_complete_goal():
    """Test plan_step returns complete_goal action."""
    mock_llm = MockLLM("complete_goal")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    output = await planner.plan_step(progress)

    assert isinstance(output, PlannerOutput)
    assert output.action == PlannerOutput.Action.COMPLETE_GOAL


@pytest.mark.asyncio
async def test_plan_step_returns_wait():
    """Test plan_step returns wait action."""
    mock_llm = MockLLM("wait")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    output = await planner.plan_step(progress)

    assert isinstance(output, PlannerOutput)
    assert output.action == PlannerOutput.Action.WAIT


@pytest.mark.asyncio
async def test_plan_step_with_empty_progress():
    """Test plan_step with empty progress (no tasks yet)."""
    mock_llm = MockLLM("dispatch_subtask")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Complete a project", progress)
    output = await planner.plan_step(progress)

    assert isinstance(output, PlannerOutput)
    assert output.action == PlannerOutput.Action.DISPATCH_SUBTASK


@pytest.mark.asyncio
async def test_plan_step_with_some_completed_tasks():
    """Test plan_step with some completed tasks."""
    mock_llm = MockLLM("dispatch_subtask")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Complete a project", progress)

    # Add some tasks and mark them as completed
    task1 = await progress.add_task("Task 1", "Complete task 1")
    task2 = await progress.add_task("Task 2", "Complete task 2")
    await progress.update_task_status(task1.id, TaskStatus.COMPLETED)

    output = await planner.plan_step(progress)

    assert isinstance(output, PlannerOutput)
    assert output.action == PlannerOutput.Action.DISPATCH_SUBTASK


@pytest.mark.asyncio
async def test_plan_step_parses_ambiguous_response():
    """Test plan_step defaults to wait for ambiguous responses."""
    mock_llm = MockLLM("Not sure what to do next...")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    output = await planner.plan_step(progress)

    assert isinstance(output, PlannerOutput)
    assert output.action == PlannerOutput.Action.WAIT


@pytest.mark.asyncio
async def test_plan_step_with_custom_temperature():
    """Test plan_step uses custom temperature from config."""
    class RecordingMockLLM(MockLLM):
        def __init__(self, response_content: str):
            super().__init__(response_content)
            self.last_temperature: float | None = None

        async def complete(
            self,
            messages: list[Message],
            temperature: float | None = None,
        ) -> LLMResponse:
            self.last_temperature = temperature
            return await super().complete(messages, temperature)

    mock_llm = RecordingMockLLM("wait")
    config = PlannerConfig(temperature=0.3)
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    await planner.plan_step(progress)

    assert mock_llm.last_temperature == 0.3


@pytest.mark.asyncio
async def test_planner_output_fields():
    """Test PlannerOutput has all expected fields and values."""
    mock_llm = MockLLM("dispatch_subtask")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    output = await planner.plan_step(progress)

    assert hasattr(output, 'action')
    assert hasattr(output, 'subtask_id')
    assert hasattr(output, 'summary')
    assert output.subtask_id is not None  # Should now have task id
    assert output.summary is not None    # Should now have task description


@pytest.mark.asyncio
async def test_planner_output_new_actions():
    """Test that new PlannerOutput actions exist and work."""
    from aime.base.types import PlannerOutput

    # Test all action types exist
    assert PlannerOutput.Action.ADD_SUBTASK == "add_subtask"
    assert PlannerOutput.Action.MODIFY_SUBTASK == "modify_subtask"
    assert PlannerOutput.Action.DELETE_SUBTASK == "delete_subtask"
    assert PlannerOutput.Action.MARK_FAILED == "mark_failed"
    # Existing actions should still work
    assert PlannerOutput.Action.DISPATCH_SUBTASK == "dispatch_subtask"
    assert PlannerOutput.Action.COMPLETE_GOAL == "complete_goal"
    assert PlannerOutput.Action.WAIT == "wait"

    # Test new fields exist
    output = PlannerOutput(
        action=PlannerOutput.Action.ADD_SUBTASK,
        description="New task",
        completion_criteria="Done",
    )
    assert hasattr(output, 'task_id')
    assert hasattr(output, 'message')
    assert hasattr(output, 'description')
    assert hasattr(output, 'completion_criteria')


@pytest.mark.asyncio
async def test_parse_add_subtask():
    """Test parsing add_subtask action."""
    mock_llm = MockLLM('add_subtask {"description": "Test add", "completion_criteria": "Test done"}')
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)

    # Initial task count after initialize
    initial_tasks = await progress.get_all_tasks()
    initial_count = len(initial_tasks)

    # Change LLM response to add_subtask for plan_step
    mock_llm.response_content = 'add_subtask {"description": "New subtask", "completion_criteria": "Subtask done"}'

    # plan_step will process the add_subtask and then default to wait
    # since no dispatch was specified after add
    await planner.plan_step(progress)

    # Verify the task was added
    all_tasks = await progress.get_all_tasks()
    assert len(all_tasks) == initial_count + 1
    task_descriptions = [t.description for t in all_tasks]
    assert "New subtask" in task_descriptions


@pytest.mark.asyncio
async def test_parse_modify_subtask():
    """Test parsing modify_subtask action."""
    mock_llm = MockLLM("wait")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    task = await progress.add_task("Original description", "Original criteria")

    new_description = "Updated description"
    new_criteria = "Updated criteria"
    mock_llm.response_content = f'modify_subtask {{"task_id": "{task.id}", "description": "{new_description}", "completion_criteria": "{new_criteria}"}}'

    await planner.plan_step(progress)

    updated_task = await progress.get_task(task.id)
    assert updated_task is not None
    assert updated_task.description == new_description
    assert updated_task.completion_criteria == new_criteria


@pytest.mark.asyncio
async def test_parse_delete_subtask():
    """Test parsing delete_subtask action."""
    mock_llm = MockLLM("wait")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    task = await progress.add_task("Task to delete", "Delete me")

    # Verify task exists
    task_before = await progress.get_task(task.id)
    assert task_before is not None

    mock_llm.response_content = f'delete_subtask {{"task_id": "{task.id}"}}'
    await planner.plan_step(progress)

    # Verify task is gone
    task_after = await progress.get_task(task.id)
    assert task_after is None


@pytest.mark.asyncio
async def test_parse_mark_failed():
    """Test parsing mark_failed action."""
    mock_llm = MockLLM("wait")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    task = await progress.add_task("Task to fail", "Fail me")

    failure_message = "Something went wrong"
    mock_llm.response_content = f'mark_failed {{"task_id": "{task.id}", "message": "{failure_message}"}}'
    await planner.plan_step(progress)

    failed_task = await progress.get_task(task.id)
    assert failed_task is not None
    assert failed_task.status == TaskStatus.FAILED
    assert failed_task.message == failure_message


@pytest.mark.asyncio
async def test_parse_multiple_actions():
    """Test parsing multiple actions in one response."""
    mock_llm = MockLLM("wait")
    config = PlannerConfig()
    planner = Planner(mock_llm, config)
    progress = ProgressModule()

    await planner.initialize("Test goal", progress)
    task_to_modify = await progress.add_task("Original", "Original criteria")
    task_to_delete = await progress.add_task("Delete me", "Delete")

    # Multiple actions in sequence
    mock_llm.response_content = f'''
modify_subtask {{"task_id": "{task_to_modify.id}", "description": "Modified"}}
delete_subtask {{"task_id": "{task_to_delete.id}"}}
add_subtask {{"description": "New task", "completion_criteria": "Done"}}
'''
    await planner.plan_step(progress)

    # Check modify worked
    modified = await progress.get_task(task_to_modify.id)
    assert modified is not None
    assert modified.description == "Modified"

    # Check delete worked
    deleted = await progress.get_task(task_to_delete.id)
    assert deleted is None

    # Check add worked
    all_tasks = await progress.get_all_tasks()
    descriptions = [t.description for t in all_tasks]
    assert "New task" in descriptions


@pytest.mark.asyncio
async def test_progress_list_modify_task():
    """Test ProgressList.modify_task method directly."""
    from aime.base.types import ProgressList

    pl = ProgressList()
    task = await pl.add_task("Original", "Original criteria")

    # Modify description only
    await pl.modify_task(task.id, description="New description")
    updated = await pl.get_task(task.id)
    assert updated.description == "New description"
    assert updated.completion_criteria == "Original criteria"

    # Modify completion criteria only
    await pl.modify_task(task.id, completion_criteria="New criteria")
    updated = await pl.get_task(task.id)
    assert updated.description == "New description"
    assert updated.completion_criteria == "New criteria"

    # Modify both
    await pl.modify_task(task.id, description="Final", completion_criteria="Final criteria")
    updated = await pl.get_task(task.id)
    assert updated.description == "Final"
    assert updated.completion_criteria == "Final criteria"


@pytest.mark.asyncio
async def test_progress_list_delete_task():
    """Test ProgressList.delete_task method directly."""
    from aime.base.types import ProgressList

    pl = ProgressList()
    task = await pl.add_task("Delete me", "Delete")

    # Verify exists
    assert await pl.get_task(task.id) is not None

    # Delete
    result = await pl.delete_task(task.id)
    assert result is True

    # Verify gone
    assert await pl.get_task(task.id) is None

    # Delete non-existent
    result = await pl.delete_task("non-existent")
    assert result is False


@pytest.mark.asyncio
async def test_progress_module_modify_task():
    """Test ProgressModule.modify_task method."""
    pm = ProgressModule()
    task = await pm.add_task("Original", "Original criteria")

    await pm.modify_task(task.id, description="Updated")
    updated = await pm.get_task(task.id)
    assert updated.description == "Updated"


@pytest.mark.asyncio
async def test_progress_module_delete_task():
    """Test ProgressModule.delete_task method."""
    pm = ProgressModule()
    task = await pm.add_task("Delete me", "Delete")

    result = await pm.delete_task(task.id)
    assert result is True
    assert await pm.get_task(task.id) is None
