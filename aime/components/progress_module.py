"""
Progress Module - Manages overall progress of agentic workflows using ProgressList.
"""
import logging
from typing import Optional, Callable, List
from aime.base.types import ProgressList, Task, TaskStatus, TaskUpdate, ArtifactReference

logger = logging.getLogger(__name__)


class ProgressModule:
    """
    Higher-level component that manages the overall progress of agentic workflows
    by integrating with and delegating to ProgressList.
    """

    def __init__(self, progress_list: Optional[ProgressList] = None):
        """
        Initialize ProgressModule with a ProgressList instance.

        Args:
            progress_list: Optional ProgressList instance. If None, creates a new one.
        """
        self._progress_list = progress_list or ProgressList()

    @property
    def progress_list(self) -> ProgressList:
        """Get the underlying ProgressList instance."""
        return self._progress_list

    async def add_task(
        self,
        description: str,
        completion_criteria: str,
        parent_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Task:
        """
        Add a new task to the progress list.

        Args:
            description: Task description
            completion_criteria: How to determine if the task is complete
            parent_id: Optional parent task ID
            dependencies: Optional list of task IDs this task depends on

        Returns:
            Created Task instance
        """
        logger.info(f"Adding new task: {description}")
        task = await self._progress_list.add_task(
            description=description,
            completion_criteria=completion_criteria,
            parent_id=parent_id,
            dependencies=dependencies,
        )
        logger.debug(f"Task added with ID: {task.id}")
        return task

    async def update_task_status(
        self, task_id: str, status: TaskStatus, message: Optional[str] = None
    ) -> Optional[Task]:
        """
        Update the status of a task.

        Args:
            task_id: ID of the task to update
            status: New status
            message: Optional message about the status change

        Returns:
            Updated Task instance if found, None otherwise
        """
        logger.debug(f"Updating task {task_id} status to {status.value}: {message or 'No message'}")
        task = await self._progress_list.update_status(
            task_id=task_id, status=status, message=message
        )
        if task:
            logger.info(f"Task {task_id} status updated to {status.value}")
        return task

    async def update_status(
        self, task_id: str, status: TaskStatus, message: Optional[str] = None
    ) -> Optional[Task]:
        """
        Alias for update_task_status for consistency with ProgressList naming.

        Args:
            task_id: ID of the task to update
            status: New status
            message: Optional message about the status change

        Returns:
            Updated Task instance if found, None otherwise
        """
        return await self.update_task_status(task_id, status, message)

    async def get_pending_tasks(self) -> List[Task]:
        """
        Get all pending tasks that are ready to execute (dependencies satisfied).

        Returns:
            List of pending tasks ready for execution
        """
        return await self._progress_list.get_pending_tasks()

    async def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks in the progress list.

        Returns:
            List of all Task instances
        """
        return await self._progress_list.get_all_tasks()

    async def export_markdown(self, indent: int = 0) -> str:
        """
        Export progress as markdown task list.

        Args:
            indent: Indentation level for the markdown output

        Returns:
            Markdown string representation
        """
        return await self._progress_list.export_markdown(indent=indent)

    async def add_artifact(self, task_id: str, artifact: ArtifactReference) -> Optional[Task]:
        """
        Add an artifact to a task.

        Args:
            task_id: ID of the task to add artifact to
            artifact: ArtifactReference instance to add

        Returns:
            Updated Task instance if found, None otherwise
        """
        return await self._progress_list.add_artifact(
            task_id=task_id, artifact=artifact
        )

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a specific task by ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            Task instance if found, None otherwise
        """
        return await self._progress_list.get_task(task_id=task_id)

    async def subscribe(self, callback: Callable[[TaskUpdate], None]) -> Callable:
        """
        Subscribe to task updates. Returns unsubscribe function.

        Args:
            callback: Function to call when task updates occur

        Returns:
            Unsubscribe function
        """
        return await self._progress_list.subscribe(callback=callback)

    async def modify_task(
        self,
        task_id: str,
        description: Optional[str] = None,
        completion_criteria: Optional[str] = None,
    ) -> Optional[Task]:
        """
        Modify an existing task's description and/or completion criteria.

        Args:
            task_id: ID of the task to modify
            description: New description (optional)
            completion_criteria: New completion criteria (optional)

        Returns:
            Updated Task instance if found, None otherwise
        """
        logger.info(f"Modifying task {task_id}: description={description is not None}, completion_criteria={completion_criteria is not None}")
        task = await self._progress_list.modify_task(
            task_id=task_id,
            description=description,
            completion_criteria=completion_criteria,
        )
        if task:
            logger.info(f"Task {task_id} modified successfully")
        return task

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from the progress list.

        Args:
            task_id: ID of the task to delete

        Returns:
            True if task was found and deleted, False otherwise
        """
        logger.info(f"Deleting task {task_id}")
        deleted = await self._progress_list.delete_task(task_id=task_id)
        if deleted:
            logger.info(f"Task {task_id} deleted successfully")
        return deleted
