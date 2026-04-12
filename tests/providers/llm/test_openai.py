"""Tests for OpenAILLM provider."""

from unittest.mock import MagicMock, AsyncMock
import pytest

from aime.providers.llm.openai import OpenAILLM
from aime.base.llm import BaseLLM, Message, ToolCall


class TestOpenAILLM:
    """Tests for OpenAILLM class."""

    def test_openai_llm_instantiation(self):
        """Test that OpenAILLM can be instantiated."""
        llm = OpenAILLM(api_key="test-key", model="gpt-4o-mini")
        assert isinstance(llm, OpenAILLM)

    def test_openai_llm_inheritance(self):
        """Test that OpenAILLM inherits from BaseLLM."""
        llm = OpenAILLM(api_key="test-key")
        assert isinstance(llm, BaseLLM)

    def test_openai_llm_default_model(self):
        """Test that OpenAILLM uses gpt-4o as default model."""
        llm = OpenAILLM(api_key="test-key")
        assert llm.model == "gpt-4o"

    def test_openai_llm_custom_model(self):
        """Test that OpenAILLM accepts custom model parameter."""
        model_name = "gpt-3.5-turbo"
        llm = OpenAILLM(api_key="test-key", model=model_name)
        assert llm.model == model_name

    def test_openai_llm_has_client(self):
        """Test that OpenAILLM initializes the client correctly."""
        llm = OpenAILLM(api_key="test-key")
        assert hasattr(llm, "client")

    @pytest.mark.asyncio
    async def test_openai_llm_temperature_parameter_passed(self):
        """Test that temperature parameter is correctly passed to OpenAI."""
        llm = OpenAILLM(api_key="test-key")
        # Create a mock client to capture the kwargs
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        llm.client = mock_client

        messages = [Message(role="user", content="Hello")]
        # We just check that the method is called with temperature when provided
        await llm.complete(messages, temperature=0.5)
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_openai_llm_parse_tool_calls(self):
        """Test that tool calls are correctly parsed from OpenAI response."""
        llm = OpenAILLM(api_key="test-key")

        # Create a mock response with a tool call
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "search"
        mock_tool_call.function.arguments = '{"query": "test"}'

        mock_message = MagicMock()
        mock_message.content = "I'll search for that"
        mock_message.tool_calls = [mock_tool_call]

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # Mock the client
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        llm.client = mock_client

        messages = [Message(role="user", content="search for test")]
        result = await llm.complete(messages)

        assert result.content == "I'll search for that"
        assert len(result.tool_calls) == 1
        tool_call = result.tool_calls[0]
        assert isinstance(tool_call, ToolCall)
        assert tool_call.name == "search"
        assert tool_call.parameters == {"query": "test"}
