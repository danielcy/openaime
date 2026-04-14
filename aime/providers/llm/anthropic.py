"""Anthropic LLM provider implementation."""

from __future__ import annotations
import json
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
        max_tokens: int = 32000,
    ):
        """Initialize the Anthropic LLM provider.

        Args:
            api_key: Anthropic API key. If not provided, will use ANTHROPIC_API_KEY
                environment variable.
            model: The model to use. Defaults to "claude-3-5-sonnet-20241022".
            base_url: Optional base URL for Anthropic-compatible API endpoints.
            max_tokens: Maximum number of tokens to generate. Defaults to 32000.
        """
        self.model = model
        self.max_tokens = max_tokens
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
            "max_tokens": self.max_tokens,
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
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if tools is not None:
            kwargs["tools"] = tools

        stream = await self.client.messages.create(**kwargs)

        # Accumulator for tool call input: accumulated input JSON
        _tool_input_accum = ""
        _tool_name: Optional[str] = None

        async for chunk in stream:
            content = None
            tool_call_delta = None
            is_final = False

            if chunk.type == "content_block_start":
                # content_block_start contains the name for tool_use blocks
                if hasattr(chunk.content_block, "type") and chunk.content_block.type == "tool_use":
                    if hasattr(chunk.content_block, "name"):
                        _tool_name = chunk.content_block.name
            elif chunk.type == "content_block_delta":
                if hasattr(chunk.delta, "text"):
                    content = chunk.delta.text
                elif hasattr(chunk.delta, "input"):
                    # Handle tool call delta (input JSON for tool use)
                    # Accumulate the incremental input
                    if hasattr(chunk.delta, "input"):
                        _tool_input_accum += chunk.delta.input

                    # Only try to parse when we have some content
                    if _tool_input_accum:
                        try:
                            params = json.loads(_tool_input_accum)
                            if _tool_name is not None:
                                tool_call_delta = ToolCall(name=_tool_name, parameters=params)
                                # Reset after successful parse for next tool call
                                _tool_input_accum = ""
                                _tool_name = None
                        except json.JSONDecodeError:
                            # JSON is still incomplete, continue accumulating in next chunk
                            pass
            elif chunk.type == "content_block_stop":
                # End of a content block - if we have accumulated input and name, try to parse it
                if _tool_input_accum and _tool_name is not None:
                    try:
                        params = json.loads(_tool_input_accum) if _tool_input_accum else {}
                        tool_call_delta = ToolCall(name=_tool_name, parameters=params)
                        _tool_input_accum = ""
                        _tool_name = None
                    except json.JSONDecodeError:
                        # If we can't parse even at the end, leave as is
                        pass
            elif chunk.type == "message_delta":
                is_final = chunk.delta.stop_reason is not None
            elif chunk.type == "message_stop":
                is_final = True

            yield LLMResponseChunk(
                content=content,
                tool_call_delta=tool_call_delta,
                is_final=is_final,
            )
