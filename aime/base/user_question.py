"""User Question Manager - Centralized system for managing user questions and answers.

This module provides a singleton registry that tracks pending user questions
and allows the TUI to answer them asynchronously.
"""
import asyncio
import uuid
from typing import Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class PendingQuestion:
    """Represents a pending user question waiting for an answer."""
    question_id: str
    questions: list[dict[str, Any]]
    future: asyncio.Future
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())


class UserQuestionManager:
    """
    Singleton manager for user questions.

    This class provides a centralized registry for pending user questions
    and allows the TUI to answer them asynchronously.
    """
    _instance: Optional['UserQuestionManager'] = None
    _lock: asyncio.Lock
    _pending_questions: dict[str, PendingQuestion] = {}
    _on_question_asked: Optional[Callable[[PendingQuestion], None]] = None
    _emit_event: Optional[Callable[[Any, dict[str, Any]], None]] = None

    def __new__(cls) -> 'UserQuestionManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = asyncio.Lock()
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'UserQuestionManager':
        """Get the singleton instance."""
        return cls()

    def set_emit_event_callback(self, callback: Optional[Callable[[Any, dict[str, Any]], None]]) -> None:
        """
        Set the emit_event callback to use when questions are asked.

        This is typically set by OpenAime to propagate events to the TUI.
        """
        self._emit_event = callback

    def set_on_question_asked_callback(self, callback: Optional[Callable[[PendingQuestion], None]]) -> None:
        """
        Set a callback to be called when a new question is asked.

        This is typically used by the TUI to show a dialog when a question is pending.
        """
        self._on_question_asked = callback

    async def ask_question(self, questions: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Ask a question and wait for the user's answer.

        Args:
            questions: List of question dictionaries as defined by the ask_user_question tool schema

        Returns:
            The user's answer
        """
        question_id = str(uuid.uuid4())
        future = asyncio.Future()

        pending = PendingQuestion(
            question_id=question_id,
            questions=questions,
            future=future
        )

        async with self._lock:
            self._pending_questions[question_id] = pending

        # Emit event if callback is set
        if self._emit_event:
            from aime.base.events import EventType
            self._emit_event(EventType.USER_QUESTION_ASKED, {
                "question_id": question_id,
                "questions": questions
            })

        # Notify callback if set
        if self._on_question_asked:
            self._on_question_asked(pending)

        # Wait for answer
        return await future

    async def answer_question(self, question_id: str, answer: dict[str, Any]) -> bool:
        """
        Answer a pending question.

        Args:
            question_id: The ID of the question to answer
            answer: The user's answer

        Returns:
            True if the question was found and answered, False otherwise
        """
        async with self._lock:
            pending = self._pending_questions.get(question_id)
            if pending and not pending.future.done():
                pending.future.set_result(answer)
                del self._pending_questions[question_id]
                return True
            return False

    async def cancel_question(self, question_id: str) -> bool:
        """
        Cancel a pending question.

        Args:
            question_id: The ID of the question to cancel

        Returns:
            True if the question was found and cancelled, False otherwise
        """
        async with self._lock:
            pending = self._pending_questions.get(question_id)
            if pending and not pending.future.done():
                pending.future.cancel()
                del self._pending_questions[question_id]
                return True
            return False

    def get_pending_questions(self) -> list[PendingQuestion]:
        """Get a list of all pending questions."""
        return list(self._pending_questions.values())

    def clear_all(self) -> None:
        """Clear all pending questions."""
        for pending in list(self._pending_questions.values()):
            if not pending.future.done():
                pending.future.cancel()
        self._pending_questions.clear()
