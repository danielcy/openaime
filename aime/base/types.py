from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Callable, Literal
import asyncio


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ArtifactReference:
    type: str  # "file" | "url" | "database" | "text"
    path: str
    description: str


@dataclass
class Task:
    id: str
    description: str
    status: TaskStatus
    parent_id: Optional[str]
    completion_criteria: str
    dependencies: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    message: Optional[str] = None
    artifacts: List[ArtifactReference] = field(default_factory=list)

    def update_status(self, status: TaskStatus, message: Optional[str] = None) -> None:
        self.status = status
        if message:
            self.message = message
        self.updated_at = datetime.now()


@dataclass
class TaskUpdate:
    task_id: str
    old_status: TaskStatus
    new_status: TaskStatus
    message: Optional[str]


@dataclass
class PlannerOutput:
    class Action(str, Enum):
        DISPATCH_SUBTASK = "dispatch_subtask"
        COMPLETE_GOAL = "complete_goal"
        WAIT = "wait"
        ADD_SUBTASK = "add_subtask"
        MODIFY_SUBTASK = "modify_subtask"
        DELETE_SUBTASK = "delete_subtask"
        MARK_FAILED = "mark_failed"

    action: Action
    subtask_id: Optional[str] = None
    summary: Optional[str] = None
    # For modify/delete/mark_failed
    task_id: Optional[str] = None
    # For mark_failed
    message: Optional[str] = None
    # For add/modify subtask
    description: Optional[str] = None
    completion_criteria: Optional[str] = None


@dataclass
class ActorResult:
    task_id: str
    status: TaskStatus
    summary: str
    artifacts: List[ArtifactReference] = field(default_factory=list)


@dataclass
class ActorRecord:
    """Metadata record for a created actor that can be reused."""
    actor_id: str
    role: str  # actor name/role description (ρ_t from paper)
    description: str  # description of what this actor is good for
    tool_bundles: List[str]  # list of tool bundle names this actor has
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)

    def update_last_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.now()


@dataclass
class ChatMessage:
    """Chat message for session context retention."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tools: Optional[List[dict]] = None  # Optional: tool call results for persistence


class ProgressList:
    """Hierarchical thread-safe task progress list."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._subscribers: List[Callable[[TaskUpdate], None]] = []

    async def add_task(
        self,
        description: str,
        completion_criteria: str,
        parent_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Task:
        async with self._lock:
            task_id = str(uuid.uuid4())[:8]
            task = Task(
                id=task_id,
                description=description,
                status=TaskStatus.PENDING,
                parent_id=parent_id,
                completion_criteria=completion_criteria,
                dependencies=dependencies or [],
            )
            self._tasks[task_id] = task
            return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        message: Optional[str] = None,
    ) -> Optional[Task]:
        # Do all the state changes inside the lock
        task_update: Optional[TaskUpdate] = None
        subscribers_copy: list[Callable[[TaskUpdate], None]] = []

        async with self._lock:
            task = self._tasks.get(task_id)
            if task is not None:
                old_status = task.status
                task.update_status(status, message)
                task_update = TaskUpdate(task_id, old_status, status, message)
                # Make a copy of subscribers before releasing the lock
                # This prevents deadlock if subscriber tries to acquire the lock itself
                subscribers_copy = list(self._subscribers)

        # Invoke callbacks outside the lock to avoid deadlock
        if task_update is not None:
            for subscriber in subscribers_copy:
                subscriber(task_update)

        return task

    async def add_artifact(
        self,
        task_id: str,
        artifact: ArtifactReference,
    ) -> Optional[Task]:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.artifacts.append(artifact)
            return task

    async def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks that are ready to execute (dependencies satisfied)."""
        async with self._lock:
            result = []
            for task in self._tasks.values():
                if task.status != TaskStatus.PENDING:
                    continue
                all_deps_completed = True
                for dep_id in task.dependencies:
                    dep_task = self._tasks.get(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        all_deps_completed = False
                        break
                if all_deps_completed:
                    result.append(task)
            return result

    async def export_markdown(self, indent: int = 0) -> str:
        """Export progress list as markdown task list."""
        async with self._lock:
            children: dict[str, List[Task]] = {}
            root_tasks: List[Task] = []
            for task in self._tasks.values():
                if task.parent_id is None:
                    root_tasks.append(task)
                else:
                    if task.parent_id not in children:
                        children[task.parent_id] = []
                    children[task.parent_id].append(task)

            def render_task(task: Task, level: int) -> str:
                prefix = "  " * level
                status_mark = "[x]" if task.status == TaskStatus.COMPLETED else "[ ]"
                line = f"{prefix}- {status_mark} {task.description}\n"
                if task.id in children:
                    for child in children[task.id]:
                        line += render_task(child, level + 1)
                return line

            result = ""
            for root in root_tasks:
                result += render_task(root, indent)
            return result

    async def subscribe(self, callback: Callable[[TaskUpdate], None]) -> Callable:
        """Subscribe to task updates. Returns unsubscribe function."""
        async with self._lock:
            self._subscribers.append(callback)

        async def unsubscribe():
            async with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)
        return unsubscribe

    async def get_all_tasks(self) -> List[Task]:
        async with self._lock:
            return list(self._tasks.values())

    async def modify_task(
        self,
        task_id: str,
        description: Optional[str] = None,
        completion_criteria: Optional[str] = None,
    ) -> Optional[Task]:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is not None:
                if description is not None:
                    task.description = description
                if completion_criteria is not None:
                    task.completion_criteria = completion_criteria
                task.updated_at = datetime.now()
            return task

    async def delete_task(self, task_id: str) -> bool:
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False
