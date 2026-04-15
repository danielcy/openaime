"""
Colored logging utilities for AIME framework.

Provides colored formatter that outputs different colors for different
log levels when running in a terminal.

Controls logging verbosity:
- None: completely silent, no logging output at all
- "verbose": print INFO and above (info, warning, error) from all packages
- "debug": enable DEBUG logging for AIME package only, third-party packages still get INFO+
"""
import logging
import sys
from typing import Literal


class ColoredFormatter(logging.Formatter):
    """Colored formatter for different log levels.

    Uses ANSI color codes only when output is a terminal (TTY).
    """

    # ANSI color codes
    COLORS = {
        logging.DEBUG: '\033[36m',    # Cyan
        logging.INFO: '\033[32m',     # Green
        logging.WARNING: '\033[33m',  # Yellow
        logging.ERROR: '\033[31m',    # Red
        logging.CRITICAL: '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        if sys.stdout.isatty():
            # Only add colors if output is a terminal
            return f"{color}{message}{self.RESET}"
        return message


def configure_logging(log_level: None | Literal["verbose", "debug"] = "verbose", force: bool = True) -> None:
    """Configure logging with colors and appropriate level.

    Args:
        log_level: Logging verbosity:
            - None: completely silent, no output at all
            - "verbose": print info/warning/error messages (default)
            - "debug": enable debug logging for AIME package
        force: If True, reconfigure even if handlers already exist (default: True)
    """
    root_logger = logging.getLogger()

    # Always force reconfigure to ensure our settings take effect
    if force:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    # If completely silent, don't add any handlers
    if log_level is None:
        return

    # Add our colored handler
    handler = logging.StreamHandler()
    formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Root logging level
    if log_level == "debug":
        root_logger.setLevel(logging.INFO)
        aime_level = logging.DEBUG
    else:  # verbose
        root_logger.setLevel(logging.INFO)
        aime_level = logging.INFO

    # Set level for AIME package
    aime_logger = logging.getLogger('aime')
    aime_logger.setLevel(aime_level)
