"""Claude Code inspired color theme for AIME TUI."""

from dataclasses import dataclass


@dataclass
class Theme:
    """Color theme configuration for AIME TUI."""

    primary: str = "#58A6FF"
    secondary: str = "#3FB950"
    warning: str = "#D29922"
    error: str = "#F85149"
    background: str = "#0D1117"
    surface: str = "#161B22"
    panel: str = "#21262D"
    text: str = "#C9D1D9"
    text_muted: str = "#8B949E"
    accent: str = "#58A6FF"


CLAUDE_CODE_THEME = Theme(
    primary="#58A6FF",
    secondary="#3FB950",
    warning="#D29922",
    error="#F85149",
    background="#0D1117",
    surface="#161B22",
    panel="#21262D",
    text="#C9D1D9",
    text_muted="#8B949E",
    accent="#58A6FF",
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
