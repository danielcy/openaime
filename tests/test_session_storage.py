"""Tests for SessionStorage class."""
import os
import pytest
from aime.base.session_storage import SessionStorage
from aime.base.session import SessionInfo
from aime.base.types import ChatMessage


def test_init_default(tmp_path):
    """Test that default initialization creates ~/.openaime/sessions"""
    # We'll test with a custom base_dir using tmp_path instead of real home
    storage = SessionStorage(base_dir=str(tmp_path))
    assert os.path.exists(str(tmp_path))
    assert storage.base_dir == tmp_path


def test_init_custom(tmp_path):
    """Test that custom base_dir works"""
    custom_dir = tmp_path / "my_custom_sessions"
    storage = SessionStorage(base_dir=str(custom_dir))
    assert os.path.exists(str(custom_dir))
    assert storage.base_dir == custom_dir


def test_create_session(tmp_path):
    """Test that create_session returns a non-empty string session_id and creates the directory"""
    storage = SessionStorage(base_dir=str(tmp_path))
    session_id = storage.create_session()

    assert isinstance(session_id, str)
    assert len(session_id) > 0
    session_dir = tmp_path / session_id
    assert os.path.isdir(str(session_dir))
    # Should create transcript.jsonl file
    transcript_file = session_dir / "transcript.jsonl"
    assert os.path.exists(str(transcript_file))


def test_save_and_get_session_info(tmp_path):
    """Test saving and reading back SessionInfo"""
    storage = SessionStorage(base_dir=str(tmp_path))
    session_id = storage.create_session()

    # Create test session info
    session_info = SessionInfo(
        session_id=session_id,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        title="Test Session",
        workspace_path=str(tmp_path),
        goal_description="Test goal",
        model_name="gpt-4"
    )

    # Save and retrieve
    storage.save_session_info(session_info)
    retrieved = storage.get_session_info(session_id)

    assert retrieved is not None
    assert retrieved.session_id == session_id
    assert retrieved.title == "Test Session"
    assert retrieved.workspace_path == str(tmp_path)
    assert retrieved.goal_description == "Test goal"
    assert retrieved.model_name == "gpt-4"


def test_append_and_load_messages(tmp_path):
    """Test appending multiple ChatMessage objects and loading them back"""
    storage = SessionStorage(base_dir=str(tmp_path))
    session_id = storage.create_session()

    # Create test messages
    messages = [
        ChatMessage(role="user", content="First message"),
        ChatMessage(role="assistant", content="First response"),
        ChatMessage(role="user", content="Second message"),
        ChatMessage(role="assistant", content="Second response")
    ]

    # Append messages
    for msg in messages:
        storage.append_message(session_id, msg)

    # Load and verify
    loaded = storage.load_transcript(session_id)
    assert len(loaded) == len(messages)

    for i, msg in enumerate(loaded):
        assert msg.role == messages[i].role
        assert msg.content == messages[i].content
        assert msg.timestamp is not None


def test_list_sessions(tmp_path):
    """Test listing sessions sorted by updated_at descending"""
    storage = SessionStorage(base_dir=str(tmp_path))

    # Create multiple sessions with different updated times
    session1 = storage.create_session()
    info1 = SessionInfo(
        session_id=session1,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        title="Session 1"
    )
    storage.save_session_info(info1)

    session2 = storage.create_session()
    info2 = SessionInfo(
        session_id=session2,
        created_at="2024-01-01T00:01:00",
        updated_at="2024-01-01T00:01:00",
        title="Session 2"
    )
    storage.save_session_info(info2)

    session3 = storage.create_session()
    info3 = SessionInfo(
        session_id=session3,
        created_at="2024-01-01T00:02:00",
        updated_at="2024-01-01T00:02:00",
        title="Session 3"
    )
    storage.save_session_info(info3)

    # List should be sorted descending by updated_at
    sessions = storage.list_sessions()
    assert len(sessions) == 3
    assert sessions[0].session_id == session3  # Most recent
    assert sessions[1].session_id == session2
    assert sessions[2].session_id == session1  # Oldest


def test_delete_session(tmp_path):
    """Test deleting an existing session"""
    storage = SessionStorage(base_dir=str(tmp_path))
    session_id = storage.create_session()
    assert storage.session_exists(session_id) is True

    deleted = storage.delete_session(session_id)
    assert deleted is True
    assert storage.session_exists(session_id) is False


def test_session_exists(tmp_path):
    """Test session_exists returns correct boolean"""
    storage = SessionStorage(base_dir=str(tmp_path))
    session_id = storage.create_session()

    assert storage.session_exists(session_id) is True
    assert storage.session_exists("non_existent_session") is False
