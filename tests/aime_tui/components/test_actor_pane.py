"""Tests for ActorPane component."""

import pytest
from datetime import datetime
from aime.base.types import ActorRecord
from aime_tui.components.actor_pane import ActorPane
from aime_tui.config import TUIConfig


class TestActorPane:
    """Test suite for ActorPane component."""

    def test_actor_pane_initialization(self):
        """Test that ActorPane initializes correctly."""
        config = TUIConfig()
        pane = ActorPane(config)

        assert pane is not None
        assert hasattr(pane, "update_actors")

    def test_update_actors_with_empty_list(self):
        """Test update_actors with an empty list of actors."""
        config = TUIConfig()
        pane = ActorPane(config)

        # This should not raise any exceptions
        pane.update_actors([])

    def test_update_actors_with_actors(self):
        """Test update_actors with a list of actors."""
        config = TUIConfig()
        pane = ActorPane(config)

        # Create some test actors
        actor1 = ActorRecord(
            actor_id="actor-0-task1",
            role="Test Actor 1",
            description="This is a test actor for task 1",
            tool_bundles=["test-bundle-1"]
        )
        actor2 = ActorRecord(
            actor_id="actor-1-task2",
            role="Test Actor 2",
            description="This is a test actor for task 2",
            tool_bundles=["test-bundle-2", "test-bundle-3"]
        )

        # This should not raise any exceptions
        pane.update_actors([actor1, actor2])

    def test_actor_details(self):
        """Test that actor details are correctly retrieved and formatted."""
        config = TUIConfig()
        pane = ActorPane(config)

        # Create a test actor with complete details
        test_actor = ActorRecord(
            actor_id="actor-0-task1",
            role="Test Actor",
            description="This actor tests functionality",
            tool_bundles=["test-bundle-1", "test-bundle-2"],
            created_at=datetime(2025, 1, 1, 10, 30, 45),
            last_used_at=datetime(2025, 1, 1, 11, 45, 30)
        )

        # Get details
        details = pane._get_actor_details(test_actor)

        # Verify we have all expected details
        assert any("description" in str(detail).lower() for detail in details)
        assert any("test-bundle-1" in str(detail) for detail in details)
        assert any("test-bundle-2" in str(detail) for detail in details)
        assert any("10:30:45" in str(detail) for detail in details)
        assert any("11:45:30" in str(detail) for detail in details)
