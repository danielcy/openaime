"""End-to-end integration test for AIME TUI.

Test the complete integration between the TUI application and OpenAime.
This test uses mock LLM to avoid real API calls.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from aime_tui.app import AimeTUI
from aime_tui.config import TUIConfig
from aime.base.events import AimeEvent, EventType
from aime.base.types import Task, TaskStatus


class TestAimeTUIE2E:
    """End-to-end integration tests for AimeTUI."""

    @pytest.fixture
    def mock_openaime(self):
        """Create a comprehensive mock OpenAime instance with progress tracking."""
        mock = Mock()

        # Mock run method
        mock.run = AsyncMock(return_value="Goal completed successfully")

        # Mock progress module
        mock_progress = Mock()
        mock_progress.get_all_tasks = AsyncMock(return_value=[
            Task(
                id="1",
                description="Write hello world program",
                status=TaskStatus.COMPLETED,
                parent_id=None,
                completion_criteria="File hello.txt created with 'Hello World' content",
                dependencies=[],
                message="Hello world program written successfully"
            )
        ])
        mock.progress = mock_progress

        return mock

    @pytest.fixture
    def tui_config(self):
        """Create a default TUIConfig instance for testing."""
        return TUIConfig()

    @pytest.mark.asyncio
    async def test_e2e_integration(self, tui_config, mock_openaime):
        """Test complete integration between TUI and OpenAime."""
        # Create TUI instance
        tui = AimeTUI(tui_config, mock_openaime)

        # Verify initialization
        assert tui is not None
        assert tui._config == tui_config
        assert tui._openaime == mock_openaime
        assert not tui._is_running

        # Test that event callback is properly registered
        assert mock_openaime.event_callback == tui.handle_event

    @pytest.mark.asyncio
    async def test_run_goal_flow(self, tui_config, mock_openaime):
        """Test the complete flow from start to completion of a simple goal."""
        tui = AimeTUI(tui_config, mock_openaime)

        # Run a simple goal
        result = await tui.run_goal("Write hello world")

        # Verify OpenAime was called
        mock_openaime.run.assert_called_once_with("Write hello world")

        # Verify result
        assert result == "Goal completed successfully"

    @pytest.mark.asyncio
    async def test_event_handling_and_progress_updates(self, tui_config, mock_openaime):
        """Test that events are properly handled and progress is updated."""
        tui = AimeTUI(tui_config, mock_openaime)

        # Create mock components
        mock_event_stream = Mock()
        mock_progress_pane = Mock()
        mock_status_bar = Mock()

        tui._event_stream = mock_event_stream
        tui._progress_pane = mock_progress_pane
        tui._status_bar = mock_status_bar

        # Test handling a goal started event
        goal_started_event = AimeEvent(
            event_type=EventType.PLANNER_GOAL_STARTED,
            data={"goal": "Write hello world"}
        )
        tui.handle_event(goal_started_event)

        # Verify event stream was updated
        mock_event_stream.add_event.assert_called_once_with(goal_started_event)

        # Verify status bar state was updated
        mock_status_bar.update_state.assert_called_once_with("running")
        mock_status_bar.update_iteration.assert_called_once_with(0)

        # Reset mock calls for next test
        mock_event_stream.add_event.reset_mock()

        # Test handling task dispatched event
        task_dispatched_event = AimeEvent(
            event_type=EventType.PLANNER_TASK_DISPATCHED,
            data={"task_id": "1", "description": "Write hello world program"}
        )
        tui.handle_event(task_dispatched_event)

        # Verify event was added to stream
        mock_event_stream.add_event.assert_called_once_with(task_dispatched_event)

    @pytest.mark.asyncio
    async def test_task_status_change_event(self, tui_config, mock_openaime):
        """Test handling TASK_STATUS_CHANGED event and progress updates."""
        tui = AimeTUI(tui_config, mock_openaime)

        # Create mock components
        mock_event_stream = Mock()
        mock_progress_pane = Mock()
        mock_status_bar = Mock()

        tui._event_stream = mock_event_stream
        tui._progress_pane = mock_progress_pane
        tui._status_bar = mock_status_bar

        # Test task status change event
        task_status_event = AimeEvent(
            event_type=EventType.TASK_STATUS_CHANGED,
            data={"task_id": "1", "status": "completed", "result": "Hello world written"}
        )
        tui.handle_event(task_status_event)

        # Verify event stream was updated
        mock_event_stream.add_event.assert_called_once_with(task_status_event)

    @pytest.mark.asyncio
    async def test_execution_finished_event(self, tui_config, mock_openaime):
        """Test handling EXECUTION_FINISHED event."""
        tui = AimeTUI(tui_config, mock_openaime)

        # Create mock components
        mock_event_stream = Mock()
        mock_progress_pane = Mock()
        mock_status_bar = Mock()

        tui._event_stream = mock_event_stream
        tui._progress_pane = mock_progress_pane
        tui._status_bar = mock_status_bar

        # Set running state
        tui._is_running = True
        tui._start_time = Mock()

        # Test execution finished event
        finished_event = AimeEvent(
            event_type=EventType.EXECUTION_FINISHED,
            data={"result": "Goal completed successfully"}
        )
        tui.handle_event(finished_event)

        # Verify event stream was updated
        mock_event_stream.add_event.assert_called_once_with(finished_event)

        # Verify status bar shows finished state
        mock_status_bar.update_state.assert_called_once_with("finished")

    @pytest.mark.asyncio
    async def test_different_layout_configurations(self, mock_openaime):
        """Test TUI integration with different layout configurations."""
        # Test horizontal layout
        horizontal_config = TUIConfig(layout="horizontal")
        horizontal_tui = AimeTUI(horizontal_config, mock_openaime)
        assert horizontal_tui._config.layout == "horizontal"

        # Test vertical layout
        vertical_config = TUIConfig(layout="vertical")
        vertical_tui = AimeTUI(vertical_config, mock_openaime)
        assert vertical_tui._config.layout == "vertical"

    @pytest.mark.asyncio
    async def test_custom_theme_configuration(self, mock_openaime):
        """Test TUI integration with custom theme configuration."""
        theme_config = TUIConfig(theme="claude-code")
        tui = AimeTUI(theme_config, mock_openaime)
        assert tui._config.theme == "claude-code"
