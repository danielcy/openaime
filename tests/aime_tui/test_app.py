"""Tests for AimeTUI main application class."""

import pytest
from unittest.mock import Mock, AsyncMock
from aime_tui.app import AimeTUI
from aime_tui.config import TUIConfig
from aime.base.events import AimeEvent, EventType


class TestAimeTUI:
    """Test the main AimeTUI application class."""

    @pytest.fixture
    def mock_openaime(self):
        """Create a mock OpenAime instance."""
        mock = Mock()
        mock.run = AsyncMock(return_value="Goal completed successfully")
        return mock

    @pytest.fixture
    def tui_config(self):
        """Create a default TUIConfig instance."""
        return TUIConfig()

    def test_initialization(self, tui_config, mock_openaime):
        """Test that AimeTUI can be initialized correctly."""
        tui = AimeTUI(tui_config, mock_openaime)
        assert tui is not None
        assert tui._config == tui_config
        assert tui._openaime == mock_openaime

    def test_initialization_with_vertical_layout(self, mock_openaime):
        """Test initialization with vertical layout configuration."""
        config = TUIConfig(layout="vertical")
        tui = AimeTUI(config, mock_openaime)
        assert tui._config.layout == "vertical"

    def test_handle_event_updates_event_stream(self, tui_config, mock_openaime):
        """Test that handle_event updates the event stream component."""
        tui = AimeTUI(tui_config, mock_openaime)

        # Create mock event stream
        mock_event_stream = Mock()
        tui._event_stream = mock_event_stream

        # Create test event
        event = AimeEvent(
            event_type=EventType.PLANNER_GOAL_STARTED,
            data={"goal": "Test goal"}
        )

        # Call handle_event
        tui.handle_event(event)

        # Verify event stream was updated
        mock_event_stream.add_event.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_run_goal(self, tui_config, mock_openaime):
        """Test that run_goal method correctly starts OpenAime execution."""
        tui = AimeTUI(tui_config, mock_openaime)

        # Test run_goal method
        await tui.run_goal("Test goal")

        # Verify OpenAime.run was called
        mock_openaime.run.assert_called_once_with("Test goal")
