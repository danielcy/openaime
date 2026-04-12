"""Anthropic LLM provider implementation."""

from __future__ import annotations
from typing import Any, Optional, AsyncIterator
from anthropic import AsyncAnthropic

from aime.base.llm import BaseLLM, Message, ToolCall, LLMResponse, LLMResponseChunk


class AnthropicLLM(BaseLLM):
    """Anthropic LLM provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        base_url: Optional[str] = None,
    ):
        """Initialize the Anthropic LLM provider.

        Args:
            api_key: Anthropic API key. If not provided, will use ANTHROPIC_API_KEY
                environment variable.
            model: The model to use. Defaults to "claude-3-5-sonnet-20241022".
            base_url: Optional base URL for Anthropic-compatible API endpoints.
        """
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key, base_url=base_url)

    async def complete(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        tools: Optional[List[dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Complete a non-streaming request.

        Args:
            messages: List of chat messages.
            temperature: Optional temperature parameter.
            tools: Optional list of tool definitions for native tool calling.

        Returns:
            LLMResponse containing the model's response.
        """
        anthropic_messages = []
        for msg in messages:
            anthropic_role = msg.role if msg.role in ["user", "assistant"] else "user"
            anthropic_messages.append({"role": anthropic_role, "content": msg.content})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if tools is not None:
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        content = None
        tool_calls: list[ToolCall] = []

        if response.content:
            for block in response.content:
                if block.type == "text":
                    content = block.text if content is None else content + block.text
                elif block.type == "tool_use":
                    tool_calls.append(
                        ToolCall(name=block.name, parameters=block.input)
                    )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            raw_response=response,
        )

    async def complete_stream(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        tools: Optional[List[dict[str, Any]]] = None,
    ) -> AsyncIterator[LLMResponseChunk]:
        """Stream the response.

        Args:
            messages: List of chat messages.
            temperature: Optional temperature parameter.
            tools: Optional list of tool definitions for native tool calling.

        Yields:
            LLMResponseChunk for each streaming chunk.
        """
        anthropic_messages = []
        for msg in messages:
            anthropic_role = msg.role if msg.role in ["user", "assistant"] else "user"
            anthropic_messages.append({"role": anthropic_role, "content": msg.content})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "stream": True,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if tools is not None:
            kwargs["tools"] = tools

        stream = await self.client.messages.create(**kwargs)

        async for chunk in stream:
            content = None
            tool_call_delta = None
            is_final = False

            if chunk.type == "content_block_delta":
                if hasattr(chunk.delta, "text"):
                    content = chunk.delta.text
                elif hasattr(chunk.delta, "input"):
                    # Handle tool call delta (input JSON for tool use)
                    name = chunk.delta.name if hasattr(chunk.delta, "name") else ""
                    tool_call_delta = ToolCall(name=name, parameters=chunk.delta.input)
            elif chunk.type == "message_delta":
                is_final = chunk.delta.stop_reason is not None
            elif chunk.type == "message_stop":
                is_final = True

            yield LLMResponseChunk(
                content=content,
                tool_call_delta=tool_call_delta,
                is_final=is_final,
            )
