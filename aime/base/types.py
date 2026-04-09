from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Callable
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

    action: Action
    subtask_id: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class ActorResult:
    task_id: str
    status: TaskStatus
    summary: str
    artifacts: List[ArtifactReference] = field(default_factory=list)


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
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                old_status = task.status
                task.update_status(status, message)
                task_update = TaskUpdate(task_id, old_status, status, message)
                for subscriber in self._subscribers:
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

    @property
    async def all_tasks(self) -> List[Task]:
        async with self._lock:
            return list(self._tasks.values())
