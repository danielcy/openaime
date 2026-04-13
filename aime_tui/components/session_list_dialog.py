"""Modal dialog for selecting a saved session to load."""

from typing import Callable
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.containers import Vertical
from rich.text import Text
from aime.base import SessionInfo, get_default_session_manager


class SessionListDialog(Screen):
    """Modal dialog for selecting a saved session to load."""

    BINDINGS = [
        ("escape", "dismiss", "Dismiss"),
    ]

    def __init__(
        self,
        on_session_selected: Callable[[str], None],
        *args,
        **kwargs,
    ):
        """Initialize the session list dialog.

        Args:
            on_session_selected: Callback to invoke when a session is selected.
                The callback will receive the session_id as parameter.
        """
        super().__init__(*args, **kwargs)
        self._on_session_selected = on_session_selected

    def compose(self) -> ComposeResult:
        """Compose the dialog UI."""
        with Vertical(id="session_list_dialog"):
            yield Label("Select a session to load:")
            yield ListView(id="session_list")

    async def on_mount(self) -> None:
        """Load and display the list of saved sessions when the dialog mounts."""
        session_list = self.query_one("#session_list", ListView)
        session_manager = get_default_session_manager()
        sessions = session_manager.list_sessions()

        for session in sessions:
            model_name = session.model_name or "Unknown Model"
            session_text = Text.from_markup(
                f"{session.title} - {session.updated_at} - {model_name}"
            )
            session_list.append(ListItem(Label(session_text), id=f"session_{session.session_id}"))

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle session selection from the list view."""
        # Extract session_id from the selected ListItem's id
        selected_item = event.item
        if selected_item and selected_item.id:
            session_id = selected_item.id.replace("session_", "")
            self.dismiss()
            self._on_session_selected(session_id)

    def action_dismiss(self) -> None:
        """Dismiss the dialog."""
        self.dismiss()
