from __future__ import annotations
import logging
import os
import aiofiles
from typing import Any
from aime.base.tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class Write(BaseTool):
    """Create and write content to a new text file."""

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return "Create and write content to a text file. Creates parent directories if needed. Overwrites if file exists."

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Content to write to the file"},
                "encoding": {"type": "string", "description": "File encoding (default: utf-8)"}
            },
            "required": ["file_path", "content"]
        }

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        file_path = parameters.get("file_path")
        content = parameters.get("content")
        encoding = parameters.get("encoding", "utf-8")

        # Check required parameters
        if file_path is None:
            return ToolResult(
                success=False,
                content="Missing required parameter 'file_path'",
            )
        if content is None:
            return ToolResult(
                success=False,
                content="Missing required parameter 'content'",
            )

        try:
            # Create parent directories if they don't exist
            directory = os.path.dirname(file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            # Write file content asynchronously
            async with aiofiles.open(file_path, mode="w", encoding=encoding) as f:
                await f.write(content)

            return ToolResult(
                success=True,
                content=f"File written successfully to {file_path}"
            )

        except Exception as e:
            logger.exception(f"Error writing file: {str(e)}")
            return ToolResult(
                success=False,
                content=f"Error writing file: {str(e)}"
            )
