from __future__ import annotations
import logging
import os
import aiofiles
from typing import Any
from aime.base.tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class Update(BaseTool):
    """Update/edit existing text file."""

    @property
    def name(self) -> str:
        return "file_update"

    @property
    def description(self) -> str:
        return "Update/edit existing text file. Supports append mode or replace mode with search/replace patterns."

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file to update"},
                "content": {"type": "string", "description": "Content to write or append"},
                "mode": {"type": "string", "description": "Update mode: 'append' (add to end) or 'replace' (replace entire file) or 'search_replace' (replace specific text). Default: 'append'"},
                "search_text": {"type": "string", "description": "Text to search for (required for 'search_replace' mode)"},
                "replace_text": {"type": "string", "description": "Text to replace with (required for 'search_replace' mode)"},
                "encoding": {"type": "string", "description": "File encoding (default: utf-8)"}
            },
            "required": ["file_path"],
            "oneOf": [
                {"required": ["content"]},
                {"required": ["search_text", "replace_text"]}
            ]
        }

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        file_path = parameters.get("file_path")
        content = parameters.get("content")
        mode = parameters.get("mode", "append")
        search_text = parameters.get("search_text")
        replace_text = parameters.get("replace_text")
        encoding = parameters.get("encoding", "utf-8")

        # Check required parameters
        if file_path is None:
            return ToolResult(
                success=False,
                content="Missing required parameter 'file_path'",
            )

        # Validate mode parameter
        valid_modes = ["append", "replace", "search_replace"]
        if mode not in valid_modes:
            return ToolResult(
                success=False,
                content=f"Invalid mode: {mode}. Must be one of: {', '.join(valid_modes)}"
            )

        # Check if file exists
        if not os.path.exists(file_path):
            return ToolResult(
                success=False,
                content=f"File not found: {file_path}"
            )

        try:
            if mode == "append":
                if content is None:
                    return ToolResult(
                        success=False,
                        content="content parameter is required for append mode"
                    )
                async with aiofiles.open(file_path, mode="a", encoding=encoding) as f:
                    await f.write(content)
                return ToolResult(
                    success=True,
                    content=f"Content appended to {file_path}"
                )

            elif mode == "replace":
                if content is None:
                    return ToolResult(
                        success=False,
                        content="content parameter is required for replace mode"
                    )
                async with aiofiles.open(file_path, mode="w", encoding=encoding) as f:
                    await f.write(content)
                return ToolResult(
                    success=True,
                    content=f"File {file_path} replaced"
                )

            elif mode == "search_replace":
                if search_text is None or replace_text is None:
                    return ToolResult(
                        success=False,
                        content="search_text and replace_text parameters are required for search_replace mode"
                    )

                # Read file content
                async with aiofiles.open(file_path, mode="r", encoding=encoding) as f:
                    file_content = await f.read()

                # Check if search text exists
                if search_text not in file_content:
                    return ToolResult(
                        success=False,
                        content=f"Search text not found in file: {repr(search_text[:100])}{'...' if len(search_text) > 100 else ''}"
                    )

                # Replace occurrences
                new_content = file_content.replace(search_text, replace_text)

                # Write back
                async with aiofiles.open(file_path, mode="w", encoding=encoding) as f:
                    await f.write(new_content)

                count = file_content.count(search_text)
                return ToolResult(
                    success=True,
                    content=f"Replaced {count} occurrence(s) in {file_path}"
                )

        except Exception as e:
            logger.exception(f"Error updating file: {str(e)}")
            return ToolResult(
                success=False,
                content=f"Error updating file: {str(e)}"
            )
