"""Volcengine (Doubao) LLM provider implementation."""

from __future__ import annotations
import json
from typing import Any, Optional, AsyncIterator
from volcenginesdkarkruntime import AsyncArk

from aime.base.llm import BaseLLM, Message, ToolCall, LLMResponse, LLMResponseChunk


class VolcengineLLM(BaseLLM):
    """Volcengine (Doubao) LLM provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "doubao-seed-2-0-lite-260215",
        base_url: Optional[str] = "https://ark.cn-beijing.volces.com/api/v3",
    ):
        """Initialize the Volcengine (Doubao) LLM provider.

        Args:
            api_key: Volcengine API key. If not provided, will use environment variable.
            model: The model to use. Defaults to "doubao-seed-2-0-lite-260215".
            base_url: Optional base URL for the API endpoint.
                Defaults to "https://ark.cn-beijing.volces.com/api/v3".
        """
        self.model = model
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

        kwargs: dict[str, Any] = {"model": self.model, "messages": volc_messages}
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
                    params = json.loads(tc.function.arguments) if tc.function.arguments else {}
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
            "stream": True,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if tools is not None:
            kwargs["tools"] = tools

        stream = await self.client.chat.completions.create(**kwargs)

        async for chunk in stream:
            content = None
            tool_call_delta = None

            if chunk.choices and chunk.choices[0].delta:
                content = chunk.choices[0].delta.content
                if chunk.choices[0].delta.tool_calls:
                    for tc in chunk.choices[0].delta.tool_calls:
                        # Parse JSON arguments to dictionary for tool call delta
                        params = json.loads(tc.function.arguments) if tc.function.arguments else {}
                        tool_call_delta = ToolCall(name=tc.function.name, parameters=params)
                        break  # Only handle one tool call per chunk for simplicity

            is_final = chunk.choices[0].finish_reason is not None if chunk.choices else False

            yield LLMResponseChunk(
                content=content,
                tool_call_delta=tool_call_delta,
                is_final=is_final,
            )
