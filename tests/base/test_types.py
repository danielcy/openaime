import pytest
import time
from aime.base.types import TaskStatus, Task, ProgressList, ActorRecord


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


@pytest.mark.asyncio
async def test_progress_list_add_task():
    pl = ProgressList()
    task = await pl.add_task(
        "Test task",
        "Complete it",
    )
    assert task.id is not None
    assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_progress_list_update_status():
    pl = ProgressList()
    task = await pl.add_task("Test", "Done")
    await pl.update_status(task.id, TaskStatus.IN_PROGRESS)
    updated = await pl.get_task(task.id)
    assert updated.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_get_pending_tasks():
    pl = ProgressList()
    parent = await pl.add_task("Parent", "Done")
    await pl.add_task("Child", "Done", parent_id=parent.id, dependencies=[parent.id])
    pending_tasks = await pl.get_pending_tasks()
    assert len(pending_tasks) == 1  # parent pending


@pytest.mark.asyncio
async def test_export_markdown():
    pl = ProgressList()
    await pl.add_task("Test task", "Complete it")
    md = await pl.export_markdown()
    assert "- [ ] Test task" in md


@pytest.mark.asyncio
async def test_subscribe():
    pl = ProgressList()
    task = await pl.add_task("Test", "Done")
    updates = []
    unsubscribe = await pl.subscribe(lambda update: updates.append(update))
    await pl.update_status(task.id, TaskStatus.COMPLETED, "Finished")
    assert len(updates) == 1
    assert updates[0].task_id == task.id
    assert updates[0].new_status == TaskStatus.COMPLETED
    await unsubscribe()


def test_actor_record_creation():
    record = ActorRecord(
        actor_id="test-actor-1",
        role="Python Code Expert",
        description="Specializes in writing and debugging Python code",
        tool_bundles=["file_system", "python_execution"]
    )
    assert record.actor_id == "test-actor-1"
    assert record.role == "Python Code Expert"
    assert "Python" in record.description
    assert len(record.tool_bundles) == 2
    assert record.created_at is not None


def test_actor_record_update_last_used():
    record = ActorRecord(
        actor_id="test-actor-1",
        role="Python Code Expert",
        description="Specializes in Python",
        tool_bundles=["file_system"]
    )
    original_time = record.last_used_at
    time.sleep(0.001)
    record.update_last_used()
    assert record.last_used_at > original_time
