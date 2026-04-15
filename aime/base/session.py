"""Session data types for persistent session storage.

This module defines the SessionInfo dataclass that stores metadata
about a saved session, including creation time, last update time,
title, workspace path, and goal description.
"""
from dataclasses import dataclass
from typing import Optional, List
from aime.base.types import ActorRecord


@dataclass
class SessionInfo:
    """Metadata for a saved session.

    Stored as session.json in the session directory.

    Attributes:
        session_id: Unique UUID identifier for the session
        created_at: ISO format timestamp when session was created
        updated_at: ISO format timestamp when session was last updated
        title: Short title (usually first user message)
        workspace_path: Absolute path to the workspace directory
        goal_description: Initial goal description
        model_name: Name of the LLM model used
        actor_registry: List of ActorRecord objects representing registered actors
        events: List of serialized events for TUI replay
    """
    session_id: str
    created_at: str
    updated_at: str
    title: str
    workspace_path: Optional[str] = None
    goal_description: Optional[str] = None
    model_name: Optional[str] = None
    actor_registry: Optional[List[ActorRecord]] = None
    events: Optional[List[dict]] = None
