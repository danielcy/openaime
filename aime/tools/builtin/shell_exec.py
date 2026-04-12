from __future__ import annotations
import asyncio
import subprocess
from typing import Any
from aime.base.tool import BaseTool, ToolResult


class ShellExec(BaseTool):
    """Execute shell commands and return output."""

    @property
    def name(self) -> str:
        return "shell_exec"

    @property
    def description(self) -> str:
        return "Execute shell commands and return combined stdout + stderr output. Supports timeout and working directory options."

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"},
                "cwd": {"type": "string", "description": "Working directory for command execution"}
            },
            "required": ["command"]
        }

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        command = parameters.get("command")
        timeout = parameters.get("timeout", 60)
        cwd = parameters.get("cwd")

        try:
            # Run shell command asynchronously
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=cwd
            )

            # Wait for process to complete with timeout
            try:
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
                output = stdout.decode("utf-8") if stdout else ""
                return_code = process.returncode

                # Consider non-zero exit codes as failure
                success = return_code == 0
                if not success:
                    output = f"Command failed with exit code {return_code}:\n{output}"

                return ToolResult(
                    success=success,
                    content=output.strip()
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    content=f"Command timed out after {timeout} seconds"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                content=f"Error executing command: {str(e)}"
            )
