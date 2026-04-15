from __future__ import annotations
import logging
import aiofiles
from typing import Any
from aime.base.tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class Read(BaseTool):
    """Read any text file content."""

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return "Read text files with any encoding (default utf-8). Returns file content as string."

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file to read"},
                "encoding": {"type": "string", "description": "File encoding (default: utf-8)"},
            },
            "required": ["file_path"]
        }

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        file_path = parameters.get("file_path")
        encoding = parameters.get("encoding", "utf-8")

        # Check required parameters
        if file_path is None:
            return ToolResult(
                success=False,
                content="Missing required parameter 'file_path'",
            )

        try:
            async with aiofiles.open(file_path, mode="r", encoding=encoding) as f:
                content = await f.read()

            return ToolResult(
                success=True,
                content=content
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                content=f"File not found: {file_path}"
            )
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                content=f"Could not decode file with encoding {encoding}. Try specifying a different encoding."
            )
        except Exception as e:
            logger.exception(f"Error reading file: {str(e)}")
            return ToolResult(
                success=False,
                content=f"Error reading file: {str(e)}"
            )
