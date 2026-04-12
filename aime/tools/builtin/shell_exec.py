from __future__ import annotations
import asyncio
import subprocess
from typing import Any
from aime.base.tool import BaseTool, ToolResult


class ShellExec(BaseTool):
    """Execute shell commands and return output with improved timeout handling, output limiting, and process cleanup.

    Security Note: Executing arbitrary shell commands can be dangerous. This tool should only be used
    with trusted input as it has full access to the system shell.
    """

    # Default configuration
    DEFAULT_TIMEOUT = 60
    MAX_OUTPUT_BYTES = 10 * 1024 * 1024  # 10MB

    @property
    def name(self) -> str:
        return "shell_exec"

    @property
    def description(self) -> str:
        return (
            "Execute shell commands and return combined stdout + stderr output. "
            "Supports timeout (default: 60s), working directory, and output size limiting (default: 10MB). "
            "Improved timeout handling returns captured output before termination. "
            "More reliable process cleanup kills entire process group."
        )

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "number", "description": "Timeout in seconds (default: 60)"},
                "cwd": {"type": "string", "description": "Working directory for command execution"}
            },
            "required": ["command"]
        }

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        command = parameters.get("command")
        timeout = parameters.get("timeout", self.DEFAULT_TIMEOUT)
        cwd = parameters.get("cwd")

        try:
            # Run shell command asynchronously (create new process group)
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=cwd,
                start_new_session=True  # Create new process group for better cleanup
            )

            captured_output = b""
            output_complete = asyncio.Event()

            # Task to read output incrementally
            async def read_output():
                nonlocal captured_output
                while True:
                    chunk = await process.stdout.read(8192)
                    if not chunk:
                        output_complete.set()
                        break
                    # Check output size limit before adding chunk
                    if len(captured_output) + len(chunk) > self.MAX_OUTPUT_BYTES:
                        # Truncate to max size
                        remaining = self.MAX_OUTPUT_BYTES - len(captured_output)
                        captured_output += chunk[:remaining]
                        output_complete.set()
                        break
                    captured_output += chunk

            # Run output reader task
            reader_task = asyncio.create_task(read_output())

            # Wait for process completion or timeout
            try:
                done, pending = await asyncio.wait(
                    [asyncio.create_task(process.wait()), reader_task],
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )

                if output_complete.is_set():
                    # Output limit reached - check if it's because we hit the limit
                    if len(captured_output) >= self.MAX_OUTPUT_BYTES:
                        # Output truncated - terminate process
                        reader_task.cancel()
                        try:
                            await reader_task
                        except asyncio.CancelledError:
                            pass

                        try:
                            process.kill()
                            await asyncio.wait_for(process.wait(), timeout=5)
                        except Exception:
                            pass

                        # Decode output
                        try:
                            output = captured_output.decode("utf-8")
                        except UnicodeDecodeError:
                            output = captured_output.decode("latin-1")

                        max_mb = self.MAX_OUTPUT_BYTES / (1024 * 1024)
                        output += f"\n\n⚠️ Output was truncated because it exceeded the {max_mb:.0f}MB limit."

                        success = True  # We terminated it, but it was executing successfully before limit
                        return ToolResult(
                            success=success,
                            content=output.strip()
                        )
                    else:
                        # Process completed normally (output_complete was set because EOF)
                        reader_task.cancel()
                        try:
                            await reader_task
                        except asyncio.CancelledError:
                            pass

                        # Decode output
                        try:
                            output = captured_output.decode("utf-8")
                        except UnicodeDecodeError:
                            output = captured_output.decode("latin-1")

                        success = process.returncode == 0
                        if not success:
                            output = f"Command failed with exit code {process.returncode}:\n{output}"

                        return ToolResult(
                            success=success,
                            content=output.strip()
                        )

                elif process.returncode is not None:
                    # Process completed normally with output under limit
                    reader_task.cancel()
                    try:
                        await reader_task
                    except asyncio.CancelledError:
                        pass

                    # Decode output
                    try:
                        output = captured_output.decode("utf-8")
                    except UnicodeDecodeError:
                        output = captured_output.decode("latin-1")

                    success = process.returncode == 0
                    if not success:
                        output = f"Command failed with exit code {process.returncode}:\n{output}"

                    return ToolResult(
                        success=success,
                        content=output.strip()
                    )

                else:
                    # Timeout occurred - terminate process group
                    reader_task.cancel()
                    try:
                        await reader_task
                    except asyncio.CancelledError:
                        pass

                    # Kill entire process group
                    try:
                        process.kill()
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except Exception:
                        pass

                    # Decode captured output
                    try:
                        output = captured_output.decode("utf-8")
                    except UnicodeDecodeError:
                        output = captured_output.decode("latin-1")

                    # Check if we truncated
                    if len(captured_output) >= self.MAX_OUTPUT_BYTES:
                        max_mb = self.MAX_OUTPUT_BYTES / (1024 * 1024)
                        output += f"\n\n⚠️ Output was truncated because it exceeded the {max_mb:.0f}MB limit."

                    # Add timeout message
                    output += f"\n\n⚠️ Command timed out after {timeout} seconds and was terminated."

                    return ToolResult(
                        success=False,
                        content=output.strip()
                    )

            except asyncio.TimeoutError:
                # Additional safeguard for timeout
                reader_task.cancel()
                try:
                    await reader_task
                except asyncio.CancelledError:
                    pass

                try:
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=5)
                except Exception:
                    pass

                try:
                    output = captured_output.decode("utf-8")
                except UnicodeDecodeError:
                    output = captured_output.decode("latin-1")

                if len(captured_output) >= self.MAX_OUTPUT_BYTES:
                    max_mb = self.MAX_OUTPUT_BYTES / (1024 * 1024)
                    output += f"\n\n⚠️ Output was truncated because it exceeded the {max_mb:.0f}MB limit."

                output += f"\n\n⚠️ Command timed out after {timeout} seconds and was terminated."

                return ToolResult(
                    success=False,
                    content=output.strip()
                )

        except Exception as e:
            return ToolResult(
                success=False,
                content=f"Error executing command: {str(e)}"
            )
