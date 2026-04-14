"""AskUserQuestion Tool - Interactive user question with multiple choice options.

Allows Actors to prompt users with multiple-choice questions to get their decision.
The tool emits an event that the TUI listens for and responds to via a dialog.
"""
import asyncio
import json
from typing import Any
from aime.base.tool import BaseTool, ToolResult
from aime.base.events import EventType
from aime.base.user_question import UserQuestionManager


class AskUserQuestion(BaseTool):
    """Ask the user a multiple-choice question to get their decision."""

    @property
    def name(self) -> str:
        return "ask_user_question"

    @property
    def description(self) -> str:
        return "Ask the user a multiple-choice question to get their decision. Use this when you need user input to choose between different options."

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The complete question text ending with question mark"
                },
                "header": {
                    "type": "string",
                    "maxLength": 12,
                    "description": "Short label for the question (max 12 characters)"
                },
                "options": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 6,
                    "description": "List of available options",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Short option label"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the option"
                            },
                            "preview": {
                                "type": "string",
                                "description": "Optional preview text for the option"
                            }
                        },
                        "required": ["label", "description"]
                    }
                },
                "multiSelect": {
                    "type": "boolean",
                    "default": False,
                    "description": "Allow multiple selection (default: false)"
                }
            },
            "required": ["question", "header", "options"]
        }

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Execute the tool: emit question event and wait for user answer."""
        # Get single question from parameters
        question_data = {
            "question": parameters.get("question", ""),
            "header": parameters.get("header", ""),
            "options": parameters.get("options", []),
            "multiSelect": parameters.get("multiSelect", False),
        }

        # Wrap as single question list for compatibility with manager
        questions = [question_data]

        try:
            # Use UserQuestionManager to ask the question and wait for answer
            manager = UserQuestionManager.get_instance()
            result = await manager.ask_question(questions)

            return ToolResult(
                success=True,
                content=json.dumps(result, indent=2, ensure_ascii=False)
            )
        except asyncio.CancelledError:
            return ToolResult(
                success=False,
                content="Question cancelled"
            )
        except Exception as e:
            logger.exception(f"Error asking question: {str(e)}")
            return ToolResult(
                success=False,
                content=f"Error asking question: {str(e)}"
            )
