from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, AsyncIterator, List


@dataclass
class Message:
    """Represents a chat message with role and content."""
    role: str
    content: str


@dataclass
class ToolCall:
    """Represents a tool call with name and parameters."""
    name: str
    parameters: dict[str, Any]


@dataclass
class LLMResponse:
    """Represents a complete LLM response."""
    content: Optional[str]
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_response: Any = None


@dataclass
class LLMResponseChunk:
    """Represents a streaming chunk from an LLM."""
    content: Optional[str] = None
    tool_call_delta: Optional[ToolCall] = None
    is_final: bool = False


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        tools: Optional[List[dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Complete a non-streaming request.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature
            tools: Optional list of tool definitions for native tool calling
        """
        pass

    @abstractmethod
    async def complete_stream(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
    ) -> AsyncIterator[LLMResponseChunk]:
        """Stream the response."""
        pass
