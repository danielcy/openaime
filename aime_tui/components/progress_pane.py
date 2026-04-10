"""Progress pane component for AIME TUI."""

from typing import Any, List, Dict, Optional
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from rich.text import Text
from rich.style import Style

from aime_tui.config import TUIConfig
from aime.base.types import Task, TaskStatus


class ProgressPane(Tree):
    """Progress pane that displays live-updating tasks from ProgressModule.

    Inherits from Textual's Tree to provide hierarchical display with
    expandable items, similar to the "Plan" section in Claude Code.
    """

    # Status colors matching Claude Code theme
    STATUS_COLORS = {
        TaskStatus.COMPLETED: "success",      # Green
        TaskStatus.IN_PROGRESS: "warning",     # Yellow
        TaskStatus.FAILED: "error",            # Red
        TaskStatus.PENDING: "text_muted",      # Gray
    }

    def __init__(self, config: TUIConfig, **kwargs: Any) -> None:
        """Initialize the ProgressPane.

        Args:
            config: TUI configuration object.
            **kwargs: Additional keyword arguments passed to Tree.
        """
        super().__init__(
            label="Tasks",
            **kwargs
        )
        self._config = config
        self._current_tasks: List[Task] = []
        # Show the root node initially collapsed
        self.root.expand()

    def update_progress(self, tasks: List[Task]) -> None:
        """Update the tree with the current progress list.

        Rebuilds the tree with all tasks, setting appropriate colors,
        checkboxes, and highlighting the currently executing task.

        Args:
            tasks: List of all tasks from ProgressModule.
        """
        self._current_tasks = tasks

        # Clear existing tree
        self.clear()

        # Build task hierarchy
        task_map: Dict[str, Task] = {task.id: task for task in tasks}
        children_map: Dict[Optional[str], List[Task]] = {}

        # Group tasks by parent
        for task in tasks:
            parent_id = task.parent_id
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(task)

        # Add root tasks and their children recursively
        root_tasks = children_map.get(None, [])
        for task in root_tasks:
            self._add_task_to_node(self.root, task, children_map)

    def _add_task_to_node(
        self,
        parent_node: TreeNode,
        task: Task,
        children_map: Dict[Optional[str], List[Task]]
    ) -> None:
        """Recursively add a task and its children to the tree.

        Args:
            parent_node: The parent tree node to add to.
            task: The task to add.
            children_map: Map of parent IDs to child tasks.
        """
        # Build the task label with checkbox and status
        label = self._build_task_label(task)

        # Add the task node
        task_node = parent_node.add(label, data=task)

        # Expand in-progress tasks by default
        if task.status == TaskStatus.IN_PROGRESS:
            task_node.expand()

        # Add child tasks
        child_tasks = children_map.get(task.id, [])
        for child_task in child_tasks:
            self._add_task_to_node(task_node, child_task, children_map)

    def _build_task_label(self, task: Task) -> Text:
        """Build a rich text label for a task.

        Includes checkbox, task description, and status color.

        Args:
            task: The task to build a label for.

        Returns:
            Rich Text object representing the task.
        """
        color = self.STATUS_COLORS.get(task.status, "default")

        # Checkbox based on completion
        checkbox = "☑" if task.status == TaskStatus.COMPLETED else "☐"

        # Build the label parts
        parts = []

        # Checkbox
        parts.append(Text(f"{checkbox} ", style=color))

        # Task description
        description = Text(task.description, style=color)

        # Highlight in-progress task with bold
        if task.status == TaskStatus.IN_PROGRESS:
            description.stylize("bold")

        parts.append(description)

        # Combine all parts
        result = Text.assemble(*parts)

        return result

    def _get_task_details(self, task: Task) -> List[Text]:
        """Get detailed information about a task.

        Used when expanding a task to show additional details.

        Args:
            task: The task to get details for.

        Returns:
            List of rich Text objects with task details.
        """
        details = []

        # Completion criteria
        if task.completion_criteria:
            details.append(
                Text(f"Completion: {task.completion_criteria}", style="dim")
            )

        # Message/result
        if task.message:
            details.append(
                Text(f"Result: {task.message}", style="italic")
            )

        # Status
        status_text = task.status.value.replace("_", " ").title()
        details.append(
            Text(f"Status: {status_text}", style="dim")
        )

        # Created time
        created_str = task.created_at.strftime("%H:%M:%S")
        details.append(
            Text(f"Created: {created_str}", style="dim")
        )

        return details

    def clear(self) -> None:
        """Clear all tasks from the tree."""
        self.root.remove_children()
