"""Tests for AskQuestionDialog component."""

from unittest.mock import Mock
import pytest
from textual.screen import Screen
from aime_tui.components.ask_question_dialog import AskQuestionDialog


class TestAskQuestionDialog:
    """Tests for the AskQuestionDialog component."""

    @pytest.fixture
    def simple_question(self):
        """Fixture for a simple single-choice question."""
        return {
            "questions": [
                {
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
                }
            ]
        }

    @pytest.fixture
    def multi_question(self):
        """Fixture for a multiple-choice question."""
        return {
            "questions": [
                {
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
                }
            ]
        }

    @pytest.fixture
    def single_question_dialog(self, simple_question):
        """Fixture for a dialog with single question."""
        return AskQuestionDialog("123", simple_question["questions"])

    @pytest.fixture
    def multi_question_dialog(self, multi_question):
        """Fixture for a dialog with multiple questions."""
        return AskQuestionDialog("456", multi_question["questions"])

    def test_dialog_initialization(self, single_question_dialog):
        """Test that the dialog initializes correctly."""
        assert single_question_dialog.question_id == "123"
        assert len(single_question_dialog.questions) == 1
        assert single_question_dialog.answers == {}

    def test_initial_disabled_state(self, single_question_dialog):
        """Test that submit button is disabled initially."""
        # Mock the submit button
        single_question_dialog.submit_button = Mock()
        single_question_dialog._update_submit_button_state()
        assert single_question_dialog.submit_button.disabled is True

    def test_parse_widget_id_checkbox(self):
        """Test widget ID parsing for checkboxes."""
        dialog = AskQuestionDialog("123", [])
        question_idx, opt_idx = dialog._parse_widget_id("checkbox-0-1")
        assert question_idx == 0
        assert opt_idx == 1

    def test_parse_widget_id_radio(self):
        """Test widget ID parsing for radio buttons."""
        dialog = AskQuestionDialog("123", [])
        question_idx, opt_idx = dialog._parse_widget_id("radio-2-3")
        assert question_idx == 2
        assert opt_idx == 3

    def test_parse_widget_id_options(self):
        """Test widget ID parsing for question options container."""
        dialog = AskQuestionDialog("123", [])
        question_idx, opt_idx = dialog._parse_widget_id("question-options-1")
        assert question_idx == 1
        assert opt_idx == -1

    def test_other_option_added(self, single_question_dialog):
        """Test that 'Other' option is automatically added to questions."""
        assert any(
            opt.get("label", "").lower() == "other"
            for opt in single_question_dialog.questions[0]["options"]
        )
