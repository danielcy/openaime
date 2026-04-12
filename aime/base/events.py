"""
AIME Event System - Real-time event streaming for execution monitoring.

Provides structured event types and callback mechanism for receiving
real-time updates as execution progresses through planning, task
management, and actor execution.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional, Any, Awaitable


class EventType(str, Enum):
    """
    Enumeration of all event types that can be emitted during execution.
    """
    # Planner level events
    PLANNER_GOAL_STARTED = "planner_goal_started"
    PLANNER_STEP_STARTED = "planner_step_started"
    PLANNER_THOUGHT = "planner_thought"
    PLANNER_TASK_ADDED = "planner_task_added"
    PLANNER_TASK_MODIFIED = "planner_task_modified"
    PLANNER_TASK_DELETED = "planner_task_deleted"
    PLANNER_TASK_MARKED_FAILED = "planner_task_marked_failed"
    PLANNER_TASK_DISPATCHED = "planner_task_dispatched"
    PLANNER_GOAL_COMPLETED = "planner_goal_completed"
    PLANNER_GOAL_FAILED = "planner_goal_failed"

    # Actor level events
    ACTOR_STARTED = "actor_started"
    ACTOR_SKILL_LOADED = "actor_skill_loaded"
    ACTOR_THOUGHT = "actor_thought"
    ACTOR_TOOL_CALLED = "actor_tool_called"
    ACTOR_TOOL_FINISHED = "actor_tool_finished"
    ACTOR_FINISHED = "actor_finished"

    # Progress/Task status change events
    TASK_STATUS_CHANGED = "task_status_changed"

    # Overall execution
    EXECUTION_FINISHED = "execution_finished"


@dataclass
class AimeEvent:
    """
    Structure representing an event emitted during AIME execution.

    Attributes:
        event_type: Type of the event from EventType enum
        data: Dictionary containing event-specific data
        timestamp: ISO format timestamp when event was created
    """
    event_type: EventType
    data: dict[str, Any]
    timestamp: str = field(default=None)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


# Type alias for event callback
EventCallback = Callable[[AimeEvent], None | Awaitable[None]]
"""
Type alias for event callback functions.
Can be either a synchronous function or an async function.
"""
