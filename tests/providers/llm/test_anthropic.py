"""Tests for AnthropicLLM provider."""

from unittest.mock import MagicMock, AsyncMock
import pytest

from aime.providers.llm.anthropic import AnthropicLLM
from aime.base.llm import BaseLLM, Message, ToolCall


class TestAnthropicLLM:
    """Tests for AnthropicLLM class."""

    def test_anthropic_llm_instantiation(self):
        """Test that AnthropicLLM can be instantiated."""
        llm = AnthropicLLM(api_key="test-key", model="claude-3-opus-20240229")
        assert isinstance(llm, AnthropicLLM)

    def test_anthropic_llm_inheritance(self):
        """Test that AnthropicLLM inherits from BaseLLM."""
        llm = AnthropicLLM(api_key="test-key")
        assert isinstance(llm, BaseLLM)

    def test_anthropic_llm_default_model(self):
        """Test that AnthropicLLM uses claude-3-5-sonnet-20241022 as default model."""
        llm = AnthropicLLM(api_key="test-key")
        assert llm.model == "claude-3-5-sonnet-20241022"

    def test_anthropic_llm_custom_model(self):
        """Test that AnthropicLLM accepts custom model parameter."""
        model_name = "claude-3-opus-20240229"
        llm = AnthropicLLM(api_key="test-key", model=model_name)
        assert llm.model == model_name

    def test_anthropic_llm_has_client(self):
        """Test that AnthropicLLM initializes the client correctly."""
        llm = AnthropicLLM(api_key="test-key")
        assert hasattr(llm, "client")

    @pytest.mark.asyncio
    async def test_anthropic_llm_temperature_parameter_passed(self):
        """Test that temperature parameter is correctly passed to Anthropic."""
        llm = AnthropicLLM(api_key="test-key")
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock()
        llm.client = mock_client

        messages = [Message(role="user", content="Hello")]
        await llm.complete(messages, temperature=0.5)
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_anthropic_llm_parse_text_content(self):
        """Test that text content is correctly parsed from Anthropic response."""
        llm = AnthropicLLM(api_key="test-key")

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Hello, this is a response"

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        llm.client = mock_client

        messages = [Message(role="user", content="Hello")]
        result = await llm.complete(messages)

        assert result.content == "Hello, this is a response"
        assert len(result.tool_calls) == 0

    @pytest.mark.asyncio
    async def test_anthropic_llm_parse_tool_calls(self):
        """Test that tool calls are correctly parsed from Anthropic response."""
        llm = AnthropicLLM(api_key="test-key")

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "I'll search for that"

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search"
        mock_tool_block.input = {"query": "test"}

        mock_response = MagicMock()
        mock_response.content = [mock_text_block, mock_tool_block]

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        llm.client = mock_client

        messages = [Message(role="user", content="search for test")]
        result = await llm.complete(messages)

        assert result.content == "I'll search for that"
        assert len(result.tool_calls) == 1
        tool_call = result.tool_calls[0]
        assert isinstance(tool_call, ToolCall)
        assert tool_call.name == "search"
        assert tool_call.parameters == {"query": "test"}
