"""Claude Code inspired color theme for AIME TUI."""

from textual.app import Theme


CLAUDE_CODE_THEME = Theme(
    name="claude-code",
    primary="#58A6FF",
    secondary="#3FB950",
    warning="#D29922",
    error="#F85149",
    background="#0D1117",
    surface="#161B22",
    panel="#21262D",
    foreground="#C9D1D9",
    accent="#58A6FF",
    variables={
        "text_muted": "#8B949E"
    }
)


def get_theme(theme_name: str = "claude-code") -> Theme:
    """Get a theme by name.

    Args:
        theme_name: Name of the theme to get. Defaults to "claude-code".

    Returns:
        Theme: The requested theme.
    """
    if theme_name == "claude-code":
        return CLAUDE_CODE_THEME
    raise ValueError(f"Unknown theme: {theme_name}")
