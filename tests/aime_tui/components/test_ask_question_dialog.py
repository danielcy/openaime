"""Tests for AskQuestionDialog component."""

from unittest.mock import Mock
import pytest
from aime_tui.components.ask_question_dialog import AskQuestionDialog


class TestAskQuestionDialog:
    """Tests for the AskQuestionDialog component."""

    @pytest.fixture
    def single_choice_question(self):
        """Fixture for a single single-choice question."""
        return [{
            "header": "Choices",
            "question": "What is your favorite color?",
            "options": [
                {
                    "label": "Red",
                    "description": "Red color",
                    "preview": "A vibrant red"
                },
                {
                    "label": "Blue",
                    "description": "Blue color",
                    "preview": "A calming blue"
                }
            ],
            "multiSelect": False
        }]

    @pytest.fixture
    def multi_choice_question(self):
        """Fixture for a single multiple-choice question."""
        return [{
            "header": "Skills",
            "question": "Which programming languages do you know?",
            "options": [
                {
                    "label": "Python",
                    "description": "Python programming language",
                    "preview": "Python logo"
                },
                {
                    "label": "JavaScript",
                    "description": "JavaScript programming language",
                    "preview": "JavaScript logo"
                },
                {
                    "label": "Java",
                    "description": "Java programming language",
                    "preview": "Java logo"
                }
            ],
            "multiSelect": True
        }]

    @pytest.fixture
    def single_choice_dialog(self, single_choice_question):
        """Fixture for a dialog with single choice question."""
        return AskQuestionDialog("123", single_choice_question)

    @pytest.fixture
    def multi_choice_dialog(self, multi_choice_question):
        """Fixture for a dialog with multiple choice question."""
        return AskQuestionDialog("456", multi_choice_question)

    def test_dialog_initialization(self, single_choice_dialog):
        """Test that the dialog initializes correctly."""
        assert single_choice_dialog.question_id == "123"
        assert "header" in single_choice_dialog.question
        assert len(single_choice_dialog.question.get("options", [])) == 3  # +1 for Other
        assert single_choice_dialog.answers == []

    def test_initial_disabled_state(self, single_choice_dialog):
        """Test that submit button is disabled initially."""
        # Mock the submit button
        single_choice_dialog.submit_button = Mock()
        single_choice_dialog._update_submit_button_state()
        assert single_choice_dialog.submit_button.disabled is True

    def test_parse_widget_id_checkbox(self, single_choice_dialog):
        """Test widget ID parsing for checkboxes."""
        question_idx, opt_idx = single_choice_dialog._parse_widget_id("checkbox-0-1")
        assert question_idx == 0
        assert opt_idx == 1

    def test_parse_widget_id_radio(self, single_choice_dialog):
        """Test widget ID parsing for radio buttons."""
        dialog = AskQuestionDialog("123", [])
        question_idx, opt_idx = dialog._parse_widget_id("radio-0-2")
        assert question_idx == 0
        assert opt_idx == 2

    def test_other_option_added(self, single_choice_dialog):
        """Test that 'Other' option is automatically added to questions."""
        options = single_choice_dialog.question.get("options", [])
        assert any(
            opt.get("label", "").lower() == "other"
            for opt in options
        )

    def test_other_option_already_preserved(self):
        """Test that 'Other' is not added twice."""
        question = [{
            "header": "Test",
            "question": "Test?",
            "options": [
                {"label": "A", "description": "A"},
                {"label": "Other", "description": "Other option"}
            ],
            "multiSelect": False
        }]
        dialog = AskQuestionDialog("123", question)
        options = dialog.question.get("options", [])
        other_count = sum(1 for opt in options if opt.get("label", "").lower() == "other")
        assert other_count == 1  # Only one Other, not duplicated
