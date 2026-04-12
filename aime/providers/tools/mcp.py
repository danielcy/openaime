"""MCP (Model Context Protocol) tool integration.

This module implements MCP tool integration that:
1. Creates MCPClient to connect to MCP servers over stdio or HTTP
2. Exposes MCP tools as AIME BaseTool instances
3. Handles tool listing from MCP server
4. Handles tool execution via MCP protocol
5. Provides comprehensive error handling

Uses the official MCP Python SDK (mcp package).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional
from mcp.client.session_group import (
    ClientSessionGroup,
    StdioServerParameters,
    StreamableHttpParameters,
    SseServerParameters,
)
from mcp.types import Tool, CallToolRequestParams, ListToolsResult, CallToolResult
from aime.base.tool import BaseTool, ToolResult, ToolBundle, Toolkit
from aime.base.types import ArtifactReference


class MCPTool(BaseTool):
    """A wrapper around MCP tool to expose it as an AIME BaseTool instance."""

    def __init__(self, client: MCPClient, group: ClientSessionGroup, tool_info: Tool):
        """Initialize an MCPTool instance.

        Args:
            client: The MCPClient that owns this tool
            group: The ClientSessionGroup instance to use for execution
            tool_info: The Tool object containing tool metadata
        """
        self._client = client
        self._group = group
        self._tool_info = tool_info

    @property
    def name(self) -> str:
        """Get the tool name from MCP server."""
        return self._tool_info.name

    @property
    def description(self) -> str:
        """Get the tool description from MCP server."""
        return self._tool_info.description

    def get_input_schema(self) -> dict[str, Any]:
        """Get the tool input schema from MCP server (JSON Schema)."""
        if self._tool_info.inputSchema:
            return self._tool_info.inputSchema
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Execute the MCP tool with given parameters.

        Args:
            parameters: The parameters to pass to the tool

        Returns:
            ToolResult containing the execution result
        """
        if not self._client.is_connected():
            return ToolResult(
                success=False,
                content=f"Cannot execute tool {self.name}: client not connected",
                artifact=None,
            )

        try:
            return await self._client.execute_tool(self._tool_info.name, parameters)
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"Error executing tool {self.name}: {str(e)}",
                artifact=None,
            )


class MCPClient:
    """Client for connecting to MCP servers and executing tools.

    Supports HTTP and SSE transport for MCP protocol communication.
    For stdio transport, use MCPStdioClient instead.
    """

    def __init__(self, transport: str = "http", url: Optional[str] = None):
        """Initialize an MCP client.

        Args:
            transport: Transport type to use - "http" or "sse"
            url: URL for HTTP or SSE transport (required)
        """
        # Only validate for direct instantiation - allow subclasses like MCPStdioClient to use stdio
        if self.__class__ is MCPClient and transport not in ["http", "sse"]:
            raise ValueError("Transport must be 'http' or 'sse'. For stdio transport, use MCPStdioClient")

        if transport in ["http", "sse"] and not url:
            raise ValueError("URL is required for HTTP or SSE transport")

        self._transport = transport
        self._url = url
        self._group: Optional[ClientSessionGroup] = None
        self._connected: bool = False
        self._tools: Optional[list[Tool]] = None
        self._tools_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to the MCP server.

        Raises:
            ConnectionError: If connection fails
        """
        if self._connected:
            return

        try:
            self._group = ClientSessionGroup()
            server_params = self._create_server_parameters()

            await self._group.connect_to_server(server_params)
            self._connected = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MCP server: {str(e)}")

    def is_connected(self) -> bool:
        """Check if the client is currently connected.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    async def disconnect(self) -> None:
        """Disconnect from the MCP server and clean up resources.

        Does nothing if already disconnected.
        """
        if not self._connected or self._group is None:
            return

        try:
            await self._group.close()
        except Exception:
            # Even if close fails, we still mark as disconnected
            pass

        self._connected = False
        self._tools = None
        self._group = None

    def _create_server_parameters(self):
        """Create server parameters based on transport type."""
        if self._transport == "http":
            return StreamableHttpParameters(url=self._url)
        elif self._transport == "sse":
            return SseServerParameters(url=self._url)
        else:
            raise ValueError("Unsupported transport type")

    async def list_tools(self) -> list[Tool]:
        """List all available tools from the MCP server.

        Returns:
            List of Tool objects describing available tools

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            await self.connect()

        async with self._tools_lock:
            if self._tools:
                return self._tools

            try:
                self._tools = list(self._group.tools.values())
                return self._tools
            except Exception as e:
                raise ConnectionError(f"Failed to list tools: {str(e)}")

    async def create_tool_bundle(self) -> ToolBundle:
        """Create a ToolBundle containing all MCP tools.

        Returns:
            ToolBundle containing all available MCP tools
        """
        tools_info = await self.list_tools()
        tools = [MCPTool(self, self._group, tool_info) for tool_info in tools_info]
        return ToolBundle(
            name="mcp_tools",
            description="Tools available from connected MCP server",
            tools=tools,
        )

    async def create_toolkit(self) -> Toolkit:
        """Create a Toolkit containing all MCP tools.

        Returns:
            Toolkit with all MCP tools organized in a single bundle
        """
        toolkit = Toolkit()
        bundle = await self.create_tool_bundle()
        toolkit.add_bundle(bundle)
        return toolkit

    async def execute_tool(self, tool_name: str, parameters: dict[str, Any]) -> ToolResult:
        """Execute a tool directly by name.

        Args:
            tool_name: The name of the tool to execute
            parameters: The parameters to pass to the tool

        Returns:
            ToolResult containing the execution result
        """
        if not self._connected:
            await self.connect()

        try:
            result = await self._group.call_tool(tool_name, parameters)
            return self._parse_mcp_result(result, tool_name)
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"Error executing tool {tool_name}: {str(e)}",
                artifact=None,
            )

    def _parse_mcp_result(self, result: Any, tool_name: str) -> ToolResult:
        """Parse MCP server response to ToolResult.

        Args:
            result: The response from MCP server
            tool_name: The name of the executed tool

        Returns:
            ToolResult containing the parsed result
        """
        # Check for CallToolResult structure from mcp.types
        if hasattr(result, "content"):
            # Join all content blocks into a single string
            content_text = ""
            for block in result.content:
                if hasattr(block, "text"):
                    content_text += block.text

            return ToolResult(
                success=True,
                content=content_text,
                artifact=None,
            )

        try:
            # Handle dictionary responses
            if isinstance(result, dict):
                if "success" in result:
                    return ToolResult(
                        success=result["success"],
                        content=result.get("content", str(result)),
                        artifact=self._parse_artifact(result.get("artifact")),
                    )
                return ToolResult(
                    success=True,
                    content=json.dumps(result, ensure_ascii=False, indent=2),
                    artifact=None,
                )

            # Handle string responses
            if isinstance(result, str):
                return ToolResult(
                    success=True,
                    content=result,
                    artifact=None,
                )

            # Fallback for other types
            return ToolResult(
                success=True,
                content=str(result),
                artifact=None,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content=f"Error parsing tool {tool_name} result: {str(e)}",
                artifact=None,
            )

    def _parse_artifact(self, artifact_data: Optional[dict]) -> Optional[ArtifactReference]:
        """Parse artifact data from tool response.

        Args:
            artifact_data: The artifact data dictionary

        Returns:
            ArtifactReference or None
        """
        if not artifact_data or not isinstance(artifact_data, dict):
            return None

        try:
            artifact_type = artifact_data.get("type", "file")
            artifact_path = artifact_data.get("path", "")
            artifact_description = artifact_data.get("description", "")

            if artifact_type and artifact_path:
                return ArtifactReference(
                    type=artifact_type,
                    path=artifact_path,
                    description=artifact_description,
                )

            return None
        except Exception as e:
            return None


class MCPStdioClient(MCPClient):
    """Client for connecting to MCP servers over stdio transport."""

    def __init__(self, command: str, args: list[str] = None):
        """Initialize an MCP stdio client.

        Args:
            command: The command to execute
            args: Optional arguments to pass to the command
        """
        super().__init__(transport="stdio")
        self._command = command
        self._args = args or []

    async def connect(self) -> None:
        """Connect to the MCP server over stdio.

        Raises:
            ConnectionError: If connection fails
        """
        if self._connected:
            return

        try:
            self._group = ClientSessionGroup()
            server_params = StdioServerParameters(
                command=self._command,
                args=self._args,
            )

            await self._group.connect_to_server(server_params)
            self._connected = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MCP server: {str(e)}")
