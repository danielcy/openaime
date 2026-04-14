"""Volcengine (Doubao) LLM provider implementation."""

from __future__ import annotations
import json
import logging
from typing import Any, Optional, AsyncIterator
from volcenginesdkarkruntime import AsyncArk

from aime.base.llm import BaseLLM, Message, ToolCall, LLMResponse, LLMResponseChunk

logger = logging.getLogger(__name__)


class VolcengineLLM(BaseLLM):
    """Volcengine (Doubao) LLM provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "doubao-seed-2-0-lite-260215",
        base_url: Optional[str] = "https://ark.cn-beijing.volces.com/api/v3",
        max_tokens: int = 32000,
    ):
        """Initialize the Volcengine (Doubao) LLM provider.

        Args:
            api_key: Volcengine API key. If not provided, will use environment variable.
            model: The model to use. Defaults to "doubao-seed-2-0-lite-260215".
            base_url: Optional base URL for the API endpoint.
                Defaults to "https://ark.cn-beijing.volces.com/api/v3".
            max_tokens: Maximum number of tokens to generate. Defaults to 32000.
        """
        self.model = model
        self.max_tokens = max_tokens
        self.client = AsyncArk(api_key=api_key, base_url=base_url)

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
        volc_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": volc_messages,
            "max_tokens": self.max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if tools is not None:
            kwargs["tools"] = tools

        response = await self.client.chat.completions.create(**kwargs)

        content = None
        tool_calls: list[ToolCall] = []

        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content
            if response.choices[0].message.tool_calls:
                for tc in response.choices[0].message.tool_calls:
                    # Parse JSON arguments to dictionary
                    params: dict[str, Any] = {}
                    if tc.function.arguments:
                        try:
                            params = json.loads(tc.function.arguments)
                        except (json.JSONDecodeError, ValueError):
                            # If JSON parsing fails, leave params empty
                            logger.warning("Failed to parse tool call arguments from Volcengine: %s", tc.function.arguments[:100])
                    tool_calls.append(
                        ToolCall(name=tc.function.name, parameters=params)
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
        volc_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": volc_messages,
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if tools is not None:
            kwargs["tools"] = tools

        stream = await self.client.chat.completions.create(**kwargs)

        # Accumulator for tool call: {index: (name, accumulated_arguments)}
        _tool_call_info: dict[int, tuple[Optional[str], str]] = {}

        async for chunk in stream:
            content = None
            tool_call_delta = None

            if chunk.choices and chunk.choices[0].delta:
                content = chunk.choices[0].delta.content
                if chunk.choices[0].delta.tool_calls:
                    for tc in chunk.choices[0].delta.tool_calls:
                        index = tc.index
                        # Get or create the accumulated info
                        if index not in _tool_call_info:
                            # First chunk for this tool call - store name and arguments
                            name = tc.function.name if tc.function and hasattr(tc.function, 'name') else None
                            _tool_call_info[index] = (name, tc.function.arguments or "")
                        else:
                            # Subsequent chunk - accumulate arguments, name is already cached
                            current_name, current_args = _tool_call_info[index]
                            _tool_call_info[index] = (current_name, current_args + (tc.function.arguments or ""))

                        # Get current accumulated info
                        name, args = _tool_call_info[index]

                        # Try to parse the accumulated arguments
                        try:
                            if not args:
                                params = {}
                            else:
                                params = json.loads(args)
                            # Only produce tool_call_delta if name is available and we have something
                            # This prevents empty/partial tool calls from being added early to tool_calls list
                            if name is not None and (params or args.strip() in ['{}', '{ }']):
                                tool_call_delta = ToolCall(name=name, parameters=params)
                                break  # Only handle one tool call per chunk for simplicity
                        except json.JSONDecodeError:
                            # JSON is still incomplete, skip this chunk - will be complete in later chunks
                            continue

            is_final = chunk.choices[0].finish_reason is not None if chunk.choices else False

            # On the final chunk, do one last attempt to parse any accumulated tool calls
            # that haven't been successfully parsed yet. This ensures we don't end up
            # with an empty tool_calls list when JSON completes on the last chunk.
            if is_final and tool_call_delta is None:
                for index, (name, args) in _tool_call_info.items():
                    if name is None:
                        continue
                    try:
                        if not args:
                            params = {}
                        else:
                            params = json.loads(args)
                        if params or args.strip() in ['{}', '{ }']:
                            tool_call_delta = ToolCall(name=name, parameters=params)
                            break  # Take first complete tool call as we do for non-final chunks
                    except json.JSONDecodeError:
                        continue

            yield LLMResponseChunk(
                content=content,
                tool_call_delta=tool_call_delta,
                is_final=is_final,
            )
