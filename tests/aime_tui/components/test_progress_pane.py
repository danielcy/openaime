"""Tests for ProgressPane component."""

from aime.base.types import Task, TaskStatus
from aime_tui.components.progress_pane import ProgressPane
from aime_tui.config import TUIConfig


class TestProgressPane:
    """Test suite for ProgressPane component."""

    def test_progress_pane_initialization(self):
        """Test that ProgressPane initializes correctly."""
        config = TUIConfig()
        pane = ProgressPane(config)

        assert pane is not None
        assert hasattr(pane, "update_progress")

    def test_update_progress_with_empty_list(self):
        """Test update_progress with an empty list of tasks."""
        config = TUIConfig()
        pane = ProgressPane(config)

        # This should not raise any exceptions
        pane.update_progress([])

    def test_update_progress_with_tasks(self):
        """Test update_progress with a list of tasks."""
        config = TUIConfig()
        pane = ProgressPane(config)

        # Create some test tasks
        task1 = Task(
            id="task1",
            description="Test task 1",
            status=TaskStatus.PENDING,
            parent_id=None,
            completion_criteria="Task 1 completed",
            dependencies=[]
        )
        task2 = Task(
            id="task2",
            description="Test task 2",
            status=TaskStatus.IN_PROGRESS,
            parent_id=None,
            completion_criteria="Task 2 completed",
            dependencies=["task1"]
        )

        # This should not raise any exceptions
        pane.update_progress([task1, task2])

    def test_update_progress_with_hierarchy(self):
        """Test update_progress with hierarchical tasks (parent-child)."""
        config = TUIConfig()
        pane = ProgressPane(config)

        # Create parent and child tasks
        parent_task = Task(
            id="parent",
            description="Parent task",
            status=TaskStatus.IN_PROGRESS,
            parent_id=None,
            completion_criteria="Parent completed",
            dependencies=[]
        )
        child_task = Task(
            id="child",
            description="Child task",
            status=TaskStatus.COMPLETED,
            parent_id="parent",
            completion_criteria="Child completed",
            dependencies=[]
        )

        # This should not raise any exceptions
        pane.update_progress([parent_task, child_task])
