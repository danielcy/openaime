"""Tests for StatusBar component."""

from datetime import timedelta
from aime_tui.components.status_bar import StatusBar
from aime_tui.config import TUIConfig


class TestStatusBar:
    """Test suite for StatusBar component."""

    def test_status_bar_initialization(self):
        """Test that StatusBar initializes correctly."""
        config = TUIConfig()
        status_bar = StatusBar(config, "/test/workspace")

        assert status_bar is not None
        assert hasattr(status_bar, "update_state")
        assert hasattr(status_bar, "update_iteration")
        assert hasattr(status_bar, "update_elapsed_time")
        assert hasattr(status_bar, "_get_state_text")
        assert hasattr(status_bar, "_format_elapsed_time")

    def test_initial_state_values(self):
        """Test initial state values."""
        config = TUIConfig()
        status_bar = StatusBar(config, "/test/workspace")

        # Initial state should be idle
        assert status_bar._state == "idle"
        # Initial iteration count should be 0
        assert status_bar._iteration == 0
        # Initial elapsed time should be 0 seconds
        assert status_bar._elapsed_time.total_seconds() == 0

    def test_update_state(self):
        """Test updating state."""
        config = TUIConfig()
        status_bar = StatusBar(config, "/test/workspace")

        # Test running state
        status_bar.update_state("running")
        assert status_bar._state == "running"

        # Test finished state
        status_bar.update_state("finished")
        assert status_bar._state == "finished"

        # Test idle state
        status_bar.update_state("idle")
        assert status_bar._state == "idle"

    def test_update_iteration(self):
        """Test updating iteration count."""
        config = TUIConfig()
        status_bar = StatusBar(config, "/test/workspace")

        # Test incrementing iteration count
        status_bar.update_iteration(5)
        assert status_bar._iteration == 5

        status_bar.update_iteration(10)
        assert status_bar._iteration == 10

    def test_update_elapsed_time(self):
        """Test updating elapsed time."""
        config = TUIConfig()
        status_bar = StatusBar(config, "/test/workspace")

        # Test with 1 minute 30 seconds
        status_bar.update_elapsed_time(timedelta(seconds=90))
        assert status_bar._elapsed_time.total_seconds() == 90

        # Test with 2 hours 15 minutes 45 seconds
        status_bar.update_elapsed_time(timedelta(hours=2, minutes=15, seconds=45))
        assert status_bar._elapsed_time.total_seconds() == 2*3600 + 15*60 + 45

    def test_format_elapsed_time(self):
        """Test that elapsed time is formatted correctly."""
        config = TUIConfig()
        status_bar = StatusBar(config, "/test/workspace")

        # Test 0 seconds
        status_bar.update_elapsed_time(timedelta(seconds=0))
        assert status_bar._format_elapsed_time() == "00:00"

        # Test 90 seconds (1:30)
        status_bar.update_elapsed_time(timedelta(seconds=90))
        assert status_bar._format_elapsed_time() == "01:30"

        # Test 2 hours 15 minutes 45 seconds
        status_bar.update_elapsed_time(timedelta(hours=2, minutes=15, seconds=45))
        assert status_bar._format_elapsed_time() == "02:15:45"
