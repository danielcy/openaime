import pytest
from aime.base.llm import Message, ToolCall, LLMResponse, LLMResponseChunk


def test_message_creation():
    """Test that Message objects can be created with correct fields."""
    message = Message(role="user", content="Hello, world!")
    assert message.role == "user"
    assert message.content == "Hello, world!"


def test_tool_call_creation():
    """Test that ToolCall objects can be created with correct fields."""
    tool_call = ToolCall(name="search", parameters={"query": "Python dataclasses"})
    assert tool_call.name == "search"
    assert tool_call.parameters == {"query": "Python dataclasses"}


def test_llm_response_creation():
    """Test that LLMResponse objects can be created with correct fields."""
    response = LLMResponse(
        content="Here's your answer",
        tool_calls=[ToolCall(name="search", parameters={"query": "Python"})],
        raw_response={"full": "response", "data": "here"}
    )
    assert response.content == "Here's your answer"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "search"
    assert response.raw_response == {"full": "response", "data": "here"}


def test_llm_response_chunk_creation():
    """Test that LLMResponseChunk objects can be created with correct fields."""
    chunk = LLMResponseChunk(
        content="Partial response",
        tool_call_delta=ToolCall(name="search", parameters={"query": "test"}),
        is_final=False
    )
    assert chunk.content == "Partial response"
    assert chunk.tool_call_delta.name == "search"
    assert chunk.tool_call_delta.parameters == {"query": "test"}
    assert chunk.is_final is False

    # Test chunk without content
    chunk2 = LLMResponseChunk(
        content=None,
        tool_call_delta=None,
        is_final=True
    )
    assert chunk2.content is None
    assert chunk2.tool_call_delta is None
    assert chunk2.is_final is True
