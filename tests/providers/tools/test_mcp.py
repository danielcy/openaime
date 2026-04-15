"""Tests for MCP tool integration.

These tests verify the MCP tool integration functionality, including:
1. MCPClient connection
2. Tool discovery and listing
3. Tool execution
4. Error handling
5. Transport support (stdio and HTTP)
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from mcp.types import Tool
from aime.providers.tools.mcp import MCPClient, MCPTool, MCPStdioClient


class TestMCPClient:
    """Tests for MCPClient class."""

    @pytest.mark.asyncio
    async def test_init_stdio_transport(self):
        """Test initialization with stdio transport (MCPStdioClient)."""
        client = MCPStdioClient(command="mcp-server", args=[])
        assert client is not None

    @pytest.mark.asyncio
    async def test_init_http_transport(self):
        """Test initialization with HTTP transport."""
        client = MCPClient(transport="http", url="http://localhost:8080")
        assert client is not None

    @pytest.mark.asyncio
    async def test_init_sse_transport(self):
        """Test initialization with SSE transport."""
        client = MCPClient(transport="sse", url="http://localhost:8080")
        assert client is not None

    @pytest.mark.asyncio
    async def test_init_invalid_transport(self):
        """Test initialization with invalid transport type."""
        with pytest.raises(ValueError):
            MCPClient(transport="invalid", url="http://localhost:8080")

    @pytest.mark.asyncio
    async def test_init_http_without_url(self):
        """Test HTTP transport initialization without URL."""
        with pytest.raises(ValueError):
            MCPClient(transport="http")

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_connect_http(self, mock_session_group):
        """Test connecting to MCP server via HTTP."""
        mock_group_instance = MagicMock()
        mock_group_instance.tools = {}
        mock_group_instance.connect_to_server = AsyncMock()
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="http", url="http://localhost:8080")
        await client.connect()

        assert hasattr(client, "_group")
        assert client._connected is True

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_connect_sse(self, mock_session_group):
        """Test connecting to MCP server via SSE."""
        mock_group_instance = MagicMock()
        mock_group_instance.tools = {}
        mock_group_instance.connect_to_server = AsyncMock()
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="sse", url="http://localhost:8080")
        await client.connect()

        assert hasattr(client, "_group")
        assert client._connected is True

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_connect_failure(self, mock_session_group):
        """Test connection failure handling."""
        mock_group_instance = MagicMock()
        mock_group_instance.connect_to_server = AsyncMock(side_effect=Exception("Connection failed"))
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="http", url="http://localhost:8080")
        with pytest.raises(ConnectionError):
            await client.connect()

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_list_tools(self, mock_session_group):
        """Test listing available tools from MCP server."""
        mock_group_instance = MagicMock()
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
        )
        mock_group_instance.tools = {"test_tool": mock_tool_info}
        mock_group_instance.connect_to_server = AsyncMock()
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="http", url="http://localhost:8080")
        tools = await client.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "test_tool"

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_create_tool_bundle(self, mock_session_group):
        """Test creating a tool bundle from available tools."""
        mock_group_instance = MagicMock()
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
        )
        mock_group_instance.tools = {"test_tool": mock_tool_info}
        mock_group_instance.connect_to_server = AsyncMock()
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="http", url="http://localhost:8080")
        bundle = await client.create_tool_bundle()

        assert bundle is not None
        assert bundle.name == "mcp_tools"
        assert len(bundle.tools) == 1
        assert bundle.tools[0].name == "test_tool"

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_create_toolkit(self, mock_session_group):
        """Test creating a toolkit from available tools."""
        mock_group_instance = MagicMock()
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
        )
        mock_group_instance.tools = {"test_tool": mock_tool_info}
        mock_group_instance.connect_to_server = AsyncMock()
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="http", url="http://localhost:8080")
        toolkit = await client.create_toolkit()

        assert toolkit is not None
        tools = toolkit.get_all_tools()
        assert len(tools) == 1
        assert tools[0].name == "test_tool"

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_execute_tool(self, mock_session_group):
        """Test executing a tool via MCP client."""
        mock_group_instance = MagicMock()
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
        )

        class MockResult:
            def __init__(self):
                class MockContent:
                    text = "Tool executed successfully"
                self.content = [MockContent()]

        mock_group_instance.tools = {"test_tool": mock_tool_info}
        mock_group_instance.connect_to_server = AsyncMock()
        mock_group_instance.call_tool = AsyncMock(return_value=MockResult())
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="http", url="http://localhost:8080")
        result = await client.execute_tool("test_tool", {"param": "test_value"})

        assert result.success is True
        assert "Tool executed successfully" in result.content

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_execute_tool_error(self, mock_session_group):
        """Test handling tool execution errors."""
        mock_group_instance = MagicMock()
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
        )
        mock_group_instance.tools = {"test_tool": mock_tool_info}
        mock_group_instance.connect_to_server = AsyncMock()
        mock_group_instance.call_tool = AsyncMock(side_effect=Exception("Execution failed"))
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="http", url="http://localhost:8080")
        result = await client.execute_tool("test_tool", {"param": "test_value"})

        assert result.success is False
        assert "Execution failed" in result.content


class TestMCPTool:
    """Tests for MCPTool class."""

    @pytest.mark.asyncio
    async def test_tool_creation(self):
        """Test creating an MCPTool instance."""
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_group = MagicMock()
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
        )

        tool = MCPTool(mock_client, mock_group, mock_tool_info)
        assert tool is not None
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"

    @pytest.mark.asyncio
    async def test_tool_input_schema(self):
        """Test retrieving tool input schema."""
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_group = MagicMock()
        test_schema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}, "param2": {"type": "integer"}},
            "required": ["param1"],
        }
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema=test_schema,
        )

        tool = MCPTool(mock_client, mock_group, mock_tool_info)
        assert tool.get_input_schema() == test_schema

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """Test executing an MCPTool directly."""
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_group = MagicMock()
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.content = "Tool executed successfully"
        mock_result.artifact = None

        mock_client.execute_tool = AsyncMock(return_value=mock_result)

        tool = MCPTool(mock_client, mock_group, mock_tool_info)
        result = await tool.execute({"param": "test"})

        assert result.success is True
        assert "Tool executed successfully" in result.content

    @pytest.mark.asyncio
    async def test_tool_execution_not_connected(self):
        """Test tool execution when client is not connected."""
        mock_client = MagicMock()
        mock_client.is_connected.return_value = False
        mock_group = MagicMock()
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
        )

        tool = MCPTool(mock_client, mock_group, mock_tool_info)
        result = await tool.execute({"param": "test"})

        assert result.success is False
        assert "client not connected" in result.content

    @pytest.mark.asyncio
    async def test_tool_execution_failure(self):
        """Test tool execution failure handling."""
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_group = MagicMock()
        mock_tool_info = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"param": {"type": "string"}}},
        )

        mock_client.execute_tool = AsyncMock(side_effect=Exception("Execution failed"))

        tool = MCPTool(mock_client, mock_group, mock_tool_info)
        result = await tool.execute({"param": "test"})

        assert result.success is False
        assert "Execution failed" in result.content


class TestIntegration:
    """Integration tests for MCP tool integration."""

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_complete_workflow_http(self, mock_session_group):
        """Test complete workflow with HTTP transport."""
        # Create mock MCP group
        mock_group_instance = MagicMock()
        mock_tool_info = Tool(
            name="echo",
            description="Echo tool",
            inputSchema={"type": "object", "properties": {"text": {"type": "string"}}},
        )
        mock_group_instance.tools = {"echo": mock_tool_info}

        class EchoResult:
            def __init__(self):
                class EchoContent:
                    text = "Echo: test message"
                self.content = [EchoContent()]
                self.isError = False

        mock_group_instance.connect_to_server = AsyncMock()

        # MCP SDK uses call_tool, not execute_tool
        mock_group_instance.call_tool = AsyncMock(return_value=EchoResult())
        mock_session_group.return_value = mock_group_instance

        # Test complete workflow
        client = MCPClient(transport="http", url="http://localhost:8080")
        bundle = await client.create_tool_bundle()
        assert len(bundle.tools) == 1

        toolkit = await client.create_toolkit()
        tool = toolkit.get_tool_by_name("echo")
        assert tool is not None

        result = await tool.execute({"text": "test message"})
        assert result.success is True
        assert "Echo: test message" in result.content


class TestEdgeCases:
    """Test edge cases for MCP integration."""

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_no_tools_available(self, mock_session_group):
        """Test behavior when no tools are available from MCP server."""
        mock_group_instance = MagicMock()
        mock_group_instance.tools = {}
        mock_group_instance.connect_to_server = AsyncMock()
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="http", url="http://localhost:8080")
        bundle = await client.create_tool_bundle()
        assert len(bundle.tools) == 0

    @pytest.mark.asyncio
    @patch("aime.providers.tools.mcp.ClientSessionGroup")
    async def test_tool_without_schema(self, mock_session_group):
        """Test tool with no input schema."""
        mock_group_instance = MagicMock()
        mock_tool_info = Tool(
            name="tool_without_schema",
            description="A tool with no schema",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
        mock_group_instance.tools = {"tool_without_schema": mock_tool_info}
        mock_group_instance.connect_to_server = AsyncMock()
        mock_session_group.return_value = mock_group_instance

        client = MCPClient(transport="http", url="http://localhost:8080")
        bundle = await client.create_tool_bundle()
        assert len(bundle.tools) == 1

        tool = bundle.tools[0]
        assert tool.get_input_schema() == {"type": "object", "properties": {}, "required": []}
