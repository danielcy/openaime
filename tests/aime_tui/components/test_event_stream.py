from aime_tui.components.event_stream import EventStream
from aime_tui.config import TUIConfig
from aime.base.events import AimeEvent, EventType


class TestEventStream:
    def test_event_stream_creation(self):
        """Test that EventStream can be instantiated."""
        config = TUIConfig()
        stream = EventStream(config)
        assert stream is not None

    def test_add_event(self):
        """Test adding events to the stream doesn't raise errors."""
        config = TUIConfig()
        stream = EventStream(config)
        event = AimeEvent(
            event_type=EventType.PLANNER_THOUGHT,
            data={"message": "Test planner event"},
            timestamp="2024-01-01T12:00:00"
        )
        # Just verify it doesn't raise an exception
        stream.add_event(event)

    def test_clear_events(self):
        """Test clearing all events from the stream doesn't raise errors."""
        config = TUIConfig()
        stream = EventStream(config)
        event = AimeEvent(
            event_type=EventType.ACTOR_THOUGHT,
            data={"message": "Test actor event"},
            timestamp="2024-01-01T12:00:00"
        )
        stream.add_event(event)
        # Just verify it doesn't raise an exception
        stream.clear()

    def test_add_multiple_event_types(self):
        """Test that different event types can be added without errors."""
        config = TUIConfig()
        stream = EventStream(config)

        # Add events of different types
        events = [
            AimeEvent(event_type=EventType.PLANNER_THOUGHT, data={"message": "Planner event"}, timestamp="2024-01-01T12:00:01"),
            AimeEvent(event_type=EventType.ACTOR_THOUGHT, data={"message": "Actor event"}, timestamp="2024-01-01T12:00:02"),
            AimeEvent(event_type=EventType.PLANNER_TASK_ADDED, data={"task": "New task"}, timestamp="2024-01-01T12:00:03"),
            AimeEvent(event_type=EventType.EXECUTION_FINISHED, data={"status": "success"}, timestamp="2024-01-01T12:00:04"),
        ]

        for event in events:
            stream.add_event(event)

    def test_auto_scroll_config(self):
        """Test that auto-scroll can be configured."""
        # Test with auto-scroll enabled
        config_enabled = TUIConfig(auto_scroll=True)
        stream_enabled = EventStream(config_enabled)
        assert stream_enabled.auto_scroll is True

        # Test with auto-scroll disabled
        config_disabled = TUIConfig(auto_scroll=False)
        stream_disabled = EventStream(config_disabled)
        assert stream_disabled.auto_scroll is False

    def test_event_without_message(self):
        """Test that events without message fields can be handled."""
        config = TUIConfig()
        stream = EventStream(config)
        event = AimeEvent(
            event_type=EventType.TASK_STATUS_CHANGED,
            data={"task_id": "123", "status": "in_progress"},
            timestamp="2024-01-01T12:00:00"
        )
        # Just verify it doesn't raise an exception
        stream.add_event(event)

    def test_event_with_empty_data(self):
        """Test that events with empty data can be handled."""
        config = TUIConfig()
        stream = EventStream(config)
        event = AimeEvent(
            event_type=EventType.PLANNER_GOAL_STARTED,
            data={},
            timestamp="2024-01-01T12:00:00"
        )
        # Just verify it doesn't raise an exception
        stream.add_event(event)
