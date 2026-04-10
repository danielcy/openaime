"""Tests for InputBox component."""

import pytest
from aime_tui.components.input_box import InputBox
from aime_tui.config import TUIConfig


class TestInputBox:
    """Test suite for InputBox component."""

    def test_input_box_initialization(self):
        """Test that InputBox initializes correctly."""
        config = TUIConfig()
        input_box = InputBox(config)

        assert input_box is not None
        assert hasattr(input_box, "on_submit")

    def test_input_box_with_submit_callback(self):
        """Test that InputBox accepts and stores a submit callback."""
        config = TUIConfig()
        callback = lambda: None
        input_box = InputBox(config, on_submit=callback)

        assert hasattr(input_box, "_on_submit")
        assert input_box._on_submit == callback

    def test_input_box_placeholder_text(self):
        """Test that InputBox has appropriate placeholder text."""
        config = TUIConfig()
        input_box = InputBox(config)

        assert input_box.placeholder is not None
        assert len(input_box.placeholder) > 0

    def test_input_box_clear(self):
        """Test that InputBox has a clear method."""
        config = TUIConfig()
        input_box = InputBox(config)

        assert hasattr(input_box, "clear")
