"""Session Manager - Business logic layer for session persistence.

This module provides a high-level API for managing sessions,
built on top of the low-level SessionStorage.
"""
from datetime import datetime
from typing import Optional, List
from aime.base.session import SessionInfo
from aime.base.session_storage import SessionStorage
from aime.base.types import ChatMessage


# Module-level singleton instance
_session_manager: Optional['SessionManager'] = None


class SessionManager:
    """Business logic layer for session management.

    Provides high-level operations on top of SessionStorage,
    including current session tracking, metadata management,
    and chat history operations.
    """

    def __init__(self, storage: SessionStorage):
        """Initialize SessionManager with storage backend.

        Args:
            storage: SessionStorage instance to use for persistence
        """
        self.storage = storage
        self._current_session_id: Optional[str] = None

    def get_current_session_id(self) -> Optional[str]:
        """Get the current active session ID.

        Returns:
            Current session ID if set, None otherwise
        """
        return self._current_session_id

    def set_current_session_id(self, session_id: str) -> None:
        """Set the current active session ID.

        Args:
            session_id: Session ID to set as current
        """
        self._current_session_id = session_id

    def get_or_create_current_session(self) -> SessionInfo:
        """Get current session or create a new one if none exists.

        If current session ID is set but the session doesn't exist,
        creates a new session and sets it as current.

        Returns:
            SessionInfo for the current session
        """
        if self._current_session_id is not None:
            session_info = self.get_session_info(self._current_session_id)
            if session_info is not None:
                return session_info

        # Create new session
        session_id = self.storage.create_session()
        now = datetime.now().isoformat()
        session_info = SessionInfo(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            title="New Session"
        )
        self.storage.save_session_info(session_info)
        self._current_session_id = session_id
        return session_info

    def update_metadata(self, session_id: str, **kwargs) -> None:
        """Update session metadata and save.

        Valid keyword arguments: title, goal_description, workspace_path, model_name

        Args:
            session_id: Session identifier
            **kwargs: Metadata fields to update
        """
        session_info = self.get_session_info(session_id)
        if session_info is None:
            return

        # Update fields if provided
        valid_fields = ['title', 'goal_description', 'workspace_path', 'model_name', 'actor_registry']
        for field in valid_fields:
            if field in kwargs:
                setattr(session_info, field, kwargs[field])

        # Update timestamp and save
        session_info.updated_at = datetime.now().isoformat()
        self.storage.save_session_info(session_info)

    def list_sessions(self) -> List[SessionInfo]:
        """List all sessions, sorted by updated_at descending.

        Returns:
            List of SessionInfo objects
        """
        return self.storage.list_sessions()

    def load_chat_history(self, session_id: str) -> List[ChatMessage]:
        """Load full chat history from a session.

        Args:
            session_id: Session identifier

        Returns:
            List of ChatMessage objects
        """
        return self.storage.load_transcript(session_id)

    def append_message(self, session_id: str, message: ChatMessage) -> None:
        """Append a message to the session and update timestamp.

        Args:
            session_id: Session identifier
            message: ChatMessage to append
        """
        # Append the message
        self.storage.append_message(session_id, message)

        # Update the session's updated_at timestamp
        session_info = self.get_session_info(session_id)
        if session_info is not None:
            session_info.updated_at = datetime.now().isoformat()
            self.storage.save_session_info(session_info)

    def delete_session(self, session_id: str, confirm: bool = False) -> bool:
        """Delete a session.

        If confirm is False and the session is the current session,
        deletion will be refused.

        Args:
            session_id: Session identifier
            confirm: If True, force deletion even if it's the current session

        Returns:
            True if deleted, False otherwise
        """
        if not confirm and self._current_session_id == session_id:
            return False

        deleted = self.storage.delete_session(session_id)

        # Clear current session if it was deleted
        if deleted and self._current_session_id == session_id:
            self._current_session_id = None

        return deleted

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Get session info for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            SessionInfo if session exists, None otherwise
        """
        return self.storage.get_session_info(session_id)

    def append_event(self, session_id: str, event: dict) -> None:
        """Append an event to the session and save the updated session info.

        Args:
            session_id: Session identifier
            event: Event dict to append (contains event_type and data)
        """
        session_info = self.get_session_info(session_id)
        if session_info is None:
            return

        # Ensure events list exists
        if session_info.events is None:
            session_info.events = []
        session_info.events.append(event)

        # Update timestamp and save
        session_info.updated_at = datetime.now().isoformat()
        self.storage.save_session_info(session_info)


def get_default_session_manager() -> SessionManager:
    """Get the global SessionManager singleton instance.

    Creates the singleton with default SessionStorage if it doesn't exist.

    Returns:
        The global SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        storage = SessionStorage()
        _session_manager = SessionManager(storage)
    return _session_manager
