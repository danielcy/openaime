"""Low-level session storage operations.

This module handles the actual file system operations:
- Creating session directories
- Reading/writing session.json metadata
- Appending to transcript.jsonl
- Loading complete transcripts
- Deleting sessions
"""
import json
import os
import uuid
from pathlib import Path
from typing import Optional, List
from aime.base.session import SessionInfo
from aime.base.types import ChatMessage


class SessionStorage:
    """Low-level session storage operations.

    Handles file system level operations for persistent sessions.
    Each session is stored in its own directory:
    {base_dir}/{session_id}/session.json - metadata
    {base_dir}/{session_id}/transcript.jsonl - chat messages (JSONL)
    """

    def __init__(self, base_dir: Optional[str] = None):
        """Initialize storage with base directory.

        Args:
            base_dir: Base directory for all sessions.
                Defaults to ~/.openaime/sessions
        """
        if base_dir is None:
            home = Path.home()
            self.base_dir = home / ".openaime" / "sessions"
        else:
            self.base_dir = Path(base_dir)

        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def list_sessions(self) -> List[SessionInfo]:
        """Enumerate all sessions, sorted by updated_at descending.

        Returns:
            List of SessionInfo for all existing sessions
        """
        sessions = []
        for item in self.base_dir.iterdir():
            if item.is_dir():
                session_info_path = item / "session.json"
                if session_info_path.exists():
                    try:
                        with open(session_info_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            # Deserialize actor_registry if present
                            if data.get('actor_registry'):
                                from aime.base.types import ActorRecord
                                data['actor_registry'] = [
                                    ActorRecord(**actor_dict)
                                    for actor_dict in data['actor_registry']
                                ]
                            sessions.append(SessionInfo(**data))
                    except Exception as e:
                        print(f"Error reading session {item.name}: {e}")
                        continue

        # Sort by updated_at descending
        return sorted(sessions, key=lambda x: x.updated_at, reverse=True)

    def create_session(self) -> str:
        """Create a new empty session directory.

        Returns:
            session_id for the new session
        """
        session_id = str(uuid.uuid4())
        session_dir = self._get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        # Create empty transcript file
        transcript_path = self._get_transcript_path(session_id)
        transcript_path.touch(exist_ok=True)

        return session_id

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Read session metadata from session.json.

        Args:
            session_id: Session identifier

        Returns:
            SessionInfo if session exists, None otherwise
        """
        session_info_path = self._get_session_info_path(session_id)

        if not session_info_path.exists():
            return None

        try:
            with open(session_info_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Deserialize actor_registry if present
                if data.get('actor_registry'):
                    from aime.base.types import ActorRecord
                    data['actor_registry'] = [
                        ActorRecord(**actor_dict)
                        for actor_dict in data['actor_registry']
                    ]
                return SessionInfo(**data)
        except Exception as e:
            print(f"Error reading session info {session_id}: {e}")
            return None

    def save_session_info(self, info: SessionInfo) -> None:
        """Save session metadata to session.json.

        Args:
            info: SessionInfo to save
        """
        session_dir = self._get_session_dir(info.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        session_info_path = self._get_session_info_path(info.session_id)

        try:
            # Convert to dict and serialize actor_registry properly
            data = info.__dict__.copy()
            if data.get('actor_registry'):
                data['actor_registry'] = [
                    actor.__dict__
                    for actor in data['actor_registry']
                ]

            with open(session_info_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving session info {info.session_id}: {e}")

    def append_message(self, session_id: str, message: ChatMessage) -> None:
        """Append a message to transcript.jsonl.

        Opens the file, appends one JSON line, closes the file.
        This ensures immediate persistence and crash safety.

        Args:
            session_id: Session identifier
            message: ChatMessage to append
        """
        transcript_path = self._get_transcript_path(session_id)

        try:
            with open(transcript_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(message.__dict__, default=str) + "\n")
        except Exception as e:
            print(f"Error appending message to session {session_id}: {e}")

    def load_transcript(self, session_id: str) -> List[ChatMessage]:
        """Load entire transcript from transcript.jsonl.

        Args:
            session_id: Session identifier

        Returns:
            List of ChatMessage objects
        """
        transcript_path = self._get_transcript_path(session_id)

        if not transcript_path.exists():
            return []

        messages = []

        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            messages.append(ChatMessage(**data))
                        except Exception as e:
                            print(f"Error parsing message in session {session_id}: {e}")
                            continue

        except Exception as e:
            print(f"Error loading transcript for session {session_id}: {e}")

        return messages

    def delete_session(self, session_id: str) -> bool:
        """Delete the entire session directory.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted successfully, False if not found
        """
        session_dir = self._get_session_dir(session_id)

        if not session_dir.exists():
            return False

        try:
            import shutil
            shutil.rmtree(session_dir)
            return True
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False

    def session_exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session directory exists
        """
        return self._get_session_dir(session_id).exists()

    def _get_session_dir(self, session_id: str) -> Path:
        """Get path to session directory."""
        return self.base_dir / session_id

    def _get_session_info_path(self, session_id: str) -> Path:
        """Get path to session.json."""
        return self._get_session_dir(session_id) / "session.json"

    def _get_transcript_path(self, session_id: str) -> Path:
        """Get path to transcript.jsonl."""
        return self._get_session_dir(session_id) / "transcript.jsonl"
