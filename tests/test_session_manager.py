"""Tests for SessionManager class."""
import time
from aime.base.session_manager import SessionManager
from aime.base.session_storage import SessionStorage
from aime.base.session import SessionInfo
from aime.base.types import ChatMessage


def test_init(tmp_path):
    """Test initialization with storage"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)
    assert manager.storage is storage
    assert manager.get_current_session_id() is None


def test_get_or_create_current_session(tmp_path):
    """Test get_or_create when no current session exists creates a new one"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)

    assert manager.get_current_session_id() is None
    session_info = manager.get_or_create_current_session()

    assert session_info is not None
    assert session_info.session_id is not None
    assert manager.get_current_session_id() == session_info.session_id
    # Verify session exists in storage
    assert storage.session_exists(session_info.session_id) is True
    # Verify default title
    assert session_info.title == "New Session"


def test_get_or_create_current_session_existing(tmp_path):
    """Test returns existing if exists"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)

    # First create a session
    session_info1 = manager.get_or_create_current_session()
    session_id = session_info1.session_id

    # Second call should return the same session
    session_info2 = manager.get_or_create_current_session()

    assert session_info2.session_id == session_id
    assert manager.get_current_session_id() == session_id


def test_update_metadata(tmp_path):
    """Test updating metadata fields"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)
    session_info = manager.get_or_create_current_session()
    session_id = session_info.session_id

    # Update metadata
    manager.update_metadata(
        session_id,
        title="Updated Title",
        goal_description="Test goal description",
        workspace_path="/test/path",
        model_name="gpt-4-turbo"
    )

    # Verify changes
    updated_info = manager.get_session_info(session_id)
    assert updated_info is not None
    assert updated_info.title == "Updated Title"
    assert updated_info.goal_description == "Test goal description"
    assert updated_info.workspace_path == "/test/path"
    assert updated_info.model_name == "gpt-4-turbo"
    # Should have updated timestamp
    assert updated_info.updated_at > session_info.updated_at


def test_append_message_updates_timestamp(tmp_path):
    """Test that appending a message updates the updated_at timestamp"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)
    session_info = manager.get_or_create_current_session()
    session_id = session_info.session_id
    original_updated_at = session_info.updated_at

    # Wait a bit to ensure timestamp difference
    time.sleep(0.001)

    # Append a message
    message = ChatMessage(role="user", content="Test message")
    manager.append_message(session_id, message)

    # Verify timestamp was updated
    updated_info = manager.get_session_info(session_id)
    assert updated_info is not None
    assert updated_info.updated_at > original_updated_at

    # Verify message was stored
    transcript = manager.load_chat_history(session_id)
    assert len(transcript) == 1
    assert transcript[0].content == "Test message"


def test_delete_current_session_without_confirm(tmp_path):
    """Test that deleting current session without confirm returns False and doesn't delete"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)
    session_info = manager.get_or_create_current_session()
    session_id = session_info.session_id

    # Try to delete without confirm
    deleted = manager.delete_session(session_id, confirm=False)
    assert deleted is False

    # Verify session still exists
    assert manager.get_current_session_id() == session_id
    assert storage.session_exists(session_id) is True


def test_delete_current_session_with_confirm(tmp_path):
    """Test that deleting current session with confirm deletes it and clears current_session_id"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)
    session_info = manager.get_or_create_current_session()
    session_id = session_info.session_id

    # Delete with confirm
    deleted = manager.delete_session(session_id, confirm=True)
    assert deleted is True

    # Verify session is gone and current is cleared
    assert manager.get_current_session_id() is None
    assert storage.session_exists(session_id) is False


def test_delete_other_session(tmp_path):
    """Test deleting non-current session works"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)

    # Create two sessions
    session1 = manager.get_or_create_current_session()
    # Create a second session directly via storage
    session2_id = storage.create_session()
    session2 = SessionInfo(
        session_id=session2_id,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        title="Session 2"
    )
    storage.save_session_info(session2)

    # Set session1 as current
    manager.set_current_session_id(session1.session_id)

    # Delete session2 (not current) without confirm should work
    deleted = manager.delete_session(session2_id, confirm=False)
    assert deleted is True
    assert storage.session_exists(session2_id) is False
    # Current session should still be session1
    assert manager.get_current_session_id() == session1.session_id


def test_list_sessions(tmp_path):
    """Test list_sessions delegates to storage"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)

    # Create some sessions
    manager.get_or_create_current_session()

    # List should delegate to storage
    manager_sessions = manager.list_sessions()
    storage_sessions = storage.list_sessions()

    assert len(manager_sessions) == len(storage_sessions)
    if manager_sessions and storage_sessions:
        assert manager_sessions[0].session_id == storage_sessions[0].session_id


def test_load_chat_history(tmp_path):
    """Test load_chat_history delegates to storage"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)
    session_info = manager.get_or_create_current_session()
    session_id = session_info.session_id

    # Add messages via manager
    msg1 = ChatMessage(role="user", content="Hello")
    msg2 = ChatMessage(role="assistant", content="Hi there")
    manager.append_message(session_id, msg1)
    manager.append_message(session_id, msg2)

    # Load via manager should give same as loading via storage
    manager_transcript = manager.load_chat_history(session_id)
    storage_transcript = storage.load_transcript(session_id)

    assert len(manager_transcript) == len(storage_transcript) == 2
    assert manager_transcript[0].content == "Hello"
    assert manager_transcript[1].content == "Hi there"


def test_save_actor_registry(tmp_path):
    """Test that actor registry is correctly persisted and loaded"""
    storage = SessionStorage(base_dir=str(tmp_path))
    manager = SessionManager(storage)
    session_info = manager.get_or_create_current_session()
    session_id = session_info.session_id

    # Create mock ActorRecord objects
    from aime.base.types import ActorRecord
    actor1 = ActorRecord(
        actor_id="actor_1",
        role="Software Engineer",
        description="Expert in Python and web development",
        tool_bundles=["web_development", "python"]
    )
    actor2 = ActorRecord(
        actor_id="actor_2",
        role="QA Engineer",
        description="Expert in testing and quality assurance",
        tool_bundles=["testing", "automation"]
    )
    actor_registry = [actor1, actor2]

    # Update session metadata with actor registry
    manager.update_metadata(session_id, actor_registry=actor_registry)

    # Verify the actor registry is in memory
    updated_info = manager.get_session_info(session_id)
    assert updated_info.actor_registry is not None
    assert len(updated_info.actor_registry) == 2
    assert updated_info.actor_registry[0].actor_id == "actor_1"
    assert updated_info.actor_registry[1].actor_id == "actor_2"

    # Create a new manager instance to verify loading from storage
    new_manager = SessionManager(storage)
    new_manager.set_current_session_id(session_id)

    # Load the session info
    loaded_info = new_manager.get_session_info(session_id)
    assert loaded_info.actor_registry is not None
    assert len(loaded_info.actor_registry) == 2
    assert loaded_info.actor_registry[0].actor_id == "actor_1"
    assert loaded_info.actor_registry[0].role == "Software Engineer"
    assert loaded_info.actor_registry[0].description == "Expert in Python and web development"
    assert loaded_info.actor_registry[0].tool_bundles == ["web_development", "python"]
    assert loaded_info.actor_registry[1].actor_id == "actor_2"
    assert loaded_info.actor_registry[1].role == "QA Engineer"
    assert loaded_info.actor_registry[1].description == "Expert in testing and quality assurance"
    assert loaded_info.actor_registry[1].tool_bundles == ["testing", "automation"]
