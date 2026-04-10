"""Tests for Claude Code inspired color theme."""

from aime_tui.theme import get_theme, CLAUDE_CODE_THEME


def test_claude_code_theme():
    theme = get_theme("claude-code")
    assert theme is not None
    assert hasattr(theme, "primary")
    assert hasattr(theme, "background")
