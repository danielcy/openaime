"""
Tests for ProgressModule component.
"""
import pytest
from aime.components.progress_module import ProgressModule
from aime.base.types import TaskStatus, ArtifactReference


@pytest.mark.asyncio
async def test_create_progress_module():
    """Test creating a ProgressModule instance."""
    module = ProgressModule()
    assert module is not None
    assert module.progress_list is not None


@pytest.mark.asyncio
async def test_add_task():
    """Test adding a task to ProgressModule."""
    module = ProgressModule()
    task = await module.add_task(
        description="Test task",
        completion_criteria="Complete the test",
    )
    assert task is not None
    assert task.id is not None
    assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_update_task_status():
    """Test updating task status."""
    module = ProgressModule()
    task = await module.add_task("Test task", "Complete it")
    updated = await module.update_task_status(task.id, TaskStatus.IN_PROGRESS, "Working on it")
    assert updated is not None
    assert updated.status == TaskStatus.IN_PROGRESS
    assert updated.message == "Working on it"


@pytest.mark.asyncio
async def test_get_pending_tasks():
    """Test getting pending tasks."""
    module = ProgressModule()
    task1 = await module.add_task("Task 1", "Complete")
    task2 = await module.add_task("Task 2", "Complete")
    await module.update_task_status(task1.id, TaskStatus.COMPLETED)
    pending = await module.get_pending_tasks()
    assert len(pending) == 1
    assert pending[0].id == task2.id


@pytest.mark.asyncio
async def test_get_all_tasks():
    """Test getting all tasks."""
    module = ProgressModule()
    task1 = await module.add_task("Task 1", "Complete")
    task2 = await module.add_task("Task 2", "Complete")
    all_tasks = await module.get_all_tasks()
    assert len(all_tasks) == 2
    task_ids = [task.id for task in all_tasks]
    assert task1.id in task_ids
    assert task2.id in task_ids


@pytest.mark.asyncio
async def test_export_markdown():
    """Test exporting progress as markdown."""
    module = ProgressModule()
    await module.add_task("Test task", "Complete it")
    md = await module.export_markdown()
    assert "- [ ] Test task" in md


@pytest.mark.asyncio
async def test_add_artifact():
    """Test adding an artifact to a task."""
    module = ProgressModule()
    task = await module.add_task("Task with artifact", "Complete")
    artifact = ArtifactReference(
        type="file",
        path="/test/file.txt",
        description="Test artifact"
    )
    updated = await module.add_artifact(task.id, artifact)
    assert updated is not None
    assert len(updated.artifacts) == 1
    assert updated.artifacts[0].type == "file"
    assert updated.artifacts[0].path == "/test/file.txt"


@pytest.mark.asyncio
async def test_subscribe_to_updates():
    """Test subscribing to task updates."""
    module = ProgressModule()
    task = await module.add_task("Task to update", "Complete")
    updates = []
    unsubscribe = await module.subscribe(lambda update: updates.append(update))
    await module.update_task_status(task.id, TaskStatus.COMPLETED, "Finished")
    assert len(updates) == 1
    assert updates[0].task_id == task.id
    assert updates[0].new_status == TaskStatus.COMPLETED
    assert updates[0].message == "Finished"
    await unsubscribe()


@pytest.mark.asyncio
async def test_with_existing_progress_list():
    """Test initializing ProgressModule with existing ProgressList."""
    from aime.base.types import ProgressList
    pl = ProgressList()
    task = await pl.add_task("Existing task", "Complete")
    module = ProgressModule(pl)
    all_tasks = await module.get_all_tasks()
    assert len(all_tasks) == 1
    assert all_tasks[0].id == task.id
