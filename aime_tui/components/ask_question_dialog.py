"""Modal dialog for asking user multiple-choice questions."""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import (
    Static,
    Button,
    Input,
    Checkbox,
    RadioSet,
    Label,
    RadioButton
)
from textual.containers import Container
from textual.reactive import reactive
from aime.base.user_question import UserQuestionManager


class AskQuestionDialog(Screen):
    """Modal dialog for asking a single multiple-choice question."""

    BINDINGS = [
        ("escape", "dismiss", "Dismiss"),
    ]

    question_id = reactive("")
    question = reactive({})
    answers = reactive([])

    def __init__(
        self,
        question_id: str,
        questions: list[dict],
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.question_id = question_id
        # We only take the first question since we now support only one
        self.question = questions[0] if questions else {}
        self.answers = []

        # Add "Other" option if not already present
        options = self.question.get("options", [])
        if not any(opt.get("label", "").lower() == "other" for opt in options):
            options.append({
                "label": "Other",
                "description": "Specify your own answer",
                "preview": "",
                "isOther": True
            })

    def compose(self) -> ComposeResult:
        """Compose the dialog UI."""
        with Container(id="dialog-container"):
            with Container(id="dialog-content"):
                # Header
                yield Static("Question", id="dialog-title")

                # Question header
                yield Static(self.question.get("header", "Question"), classes="question-chip")

                # Question text
                yield Label(self.question.get("question", ""), id="question-text")

                # Options container
                with Container(id="question-options"):
                    # We'll render options in on_mount
                    pass

                # Preview pane
                with Container(id="preview-pane"):
                    yield Static("Preview")
                    yield Static("", id="preview-content")

                # Buttons
                with Container(id="dialog-buttons"):
                    yield Button("Cancel", id="cancel-button")
                    yield Button("Submit", variant="primary", id="submit-button", disabled=True)

    def on_mount(self) -> None:
        """Mount the options when dialog is mounted."""
        container = self.query_one("#question-options", Container)
        is_multi = self.question.get("multiSelect", False)
        options = self.question.get("options", [])

        if is_multi:
            # Multiple choice - use Checkbox
            for opt_idx, option in enumerate(options):
                checkbox = Checkbox(
                    option["label"],
                    value=False,
                    id=f"checkbox-0-{opt_idx}"
                )
                container.mount(checkbox)

            # "Other" input field
            other_input = Input(
                placeholder="Please specify...",
                id="other-input-0",
                classes="other-input hidden"
            )
            container.mount(other_input)
        else:
            # Single choice - use RadioSet
            radio_set = RadioSet(id="question-options-0")
            container.mount(radio_set)

            for opt_idx, option in enumerate(options):
                radio_button = RadioButton(
                    option["label"],
                    value=False,
                    id=f"radio-0-{opt_idx}",
                )
                radio_set.mount(radio_button)

            # "Other" input field
            other_input = Input(
                placeholder="Please specify...",
                id="other-input-0",
                classes="other-input hidden"
            )
            container.mount(other_input)

        # Initial preview update
        self._update_preview(-1)
        self._update_submit_button_state()

    def _update_preview(self, option_idx: int) -> None:
        """Update the preview pane with the selected option's preview."""
        preview_content = self.query_one("#preview-content", Static)
        options = self.question.get("options", [])

        if 0 <= option_idx < len(options):
            preview = options[option_idx].get("preview", "")
            preview_content.update(preview)
        else:
            preview_content.update("")

    def _update_submit_button_state(self) -> None:
        """Update submit button state based on having an answer."""
        # Submit enabled if we have any answer
        has_answer = len(self.answers) > 0

        try:
            submit_button = self.query_one("#submit-button", Button)
            submit_button.disabled = not has_answer
        except Exception:
            pass

        # Also support test mocking
        if hasattr(self, "submit_button"):
            self.submit_button.disabled = not has_answer

    def _parse_widget_id(self, widget_id: str) -> tuple[int, int]:
        """Parse widget ID to extract question and option indices."""
        parts = widget_id.split("-")
        if parts[0] in ["checkbox", "radio"]:
            return int(parts[1]), int(parts[2])
        return -1, -1

    async def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle single choice radio button changes."""
        option_idx = event.index if event.index is not None else -1

        # Update answer
        if option_idx >= 0:
            self.answers = [option_idx]
        else:
            self.answers = []

        # Check if "Other" is selected
        if option_idx >= 0:
            options = self.question.get("options", [])
            option = options[option_idx]
            other_input = self.query_one("#other-input-0", Input)
            if option.get("isOther", False):
                other_input.remove_class("hidden")
            else:
                other_input.add_class("hidden")

        # Update preview and submit button
        self._update_preview(option_idx)
        self._update_submit_button_state()

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes (for multiple choice)."""
        question_idx, opt_idx = self._parse_widget_id(event.control.id)

        # Update answer
        if event.value:
            if opt_idx not in self.answers:
                self.answers.append(opt_idx)
        else:
            if opt_idx in self.answers:
                self.answers.remove(opt_idx)

        # Check if "Other" is selected
        options = self.question.get("options", [])
        other_input = self.query_one("#other-input-0", Input)
        has_other = any(
            options[idx].get("isOther", False) for idx in self.answers
        )
        if has_other:
            other_input.remove_class("hidden")
        else:
            other_input.add_class("hidden")

        # Update preview and submit button
        if opt_idx >= 0 and event.value:
            self._update_preview(opt_idx)
        self._update_submit_button_state()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.control.id == "cancel-button":
            await UserQuestionManager.get_instance().cancel_question(self.question_id)
            self.dismiss()
        elif event.control.id == "submit-button":
            await self._submit_answers()

    async def _submit_answers(self) -> None:
        """Submit the answers to UserQuestionManager."""
        final_answers = {}
        question_idx = 0
        question_id = f"question-{question_idx}"
        final_answers[question_id] = []

        options = self.question.get("options", [])
        for opt_idx in self.answers:
            option = options[opt_idx]
            if option.get("isOther", False):
                other_input = self.query_one("#other-input-0", Input)
                if other_input.value.strip():
                    final_answers[question_id].append(other_input.value.strip())
            else:
                final_answers[question_id].append(option["label"])

        # Call the user question manager
        await UserQuestionManager.get_instance().answer_question(
            self.question_id,
            final_answers
        )

        self.dismiss()

    def action_dismiss(self) -> None:
        """Dismiss the dialog."""
        self.dismiss()
