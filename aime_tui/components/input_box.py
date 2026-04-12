"""Input box component for AIME TUI."""

from typing import Any, Callable, Optional
from textual.widgets import Input


class InputBox(Input):
    """Input box for user interaction in the AIME TUI.

    Allows users to:
    - Pause/resume execution
    - Add additional instructions
    - Interrupt current execution

    Inherits from Textual's Input widget and adds a callback for submit handling.
    """

    def __init__(
        self,
        config,
        on_submit: Optional[Callable[[str], None]] = None,
        **kwargs: Any
    ) -> None:
        """Initialize the InputBox.

        Args:
            config: TUI configuration object.
            on_submit: Callback to be called when input is submitted (Enter key pressed).
            **kwargs: Additional keyword arguments passed to Input.
        """
        super().__init__(
            placeholder="Type instructions, pause, resume, or interrupt...",
            **kwargs
        )
        self._config = config
        self._on_submit = on_submit

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission when Enter key is pressed.

        Args:
            event: Textual's Input.Submitted event.
        """
        value = event.value.strip()
        if value and self._on_submit:
            self._on_submit(value)
            self.value = ""  # Clear the input after submission

    def clear(self) -> None:
        """Clear the input value."""
        self.value = ""
