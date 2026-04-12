import pytest
import asyncio
import tempfile
import os
from aime.tools.builtin import ShellExec


@pytest.mark.asyncio
async def test_shell_exec_basic_command():
    tool = ShellExec()
    result = await tool.execute({"command": "echo 'Hello, World!'"})
    assert result.success is True
    assert result.content.strip() == "Hello, World!"
    assert result.artifact is None


@pytest.mark.asyncio
async def test_shell_exec_failing_command():
    tool = ShellExec()
    result = await tool.execute({"command": "nonexistent_command_that_will_fail"})
    assert result.success is False
    assert "failed" in result.content.lower()


@pytest.mark.asyncio
async def test_shell_exec_with_timeout():
    tool = ShellExec()
    result = await tool.execute({"command": "sleep 3", "timeout": 1})
    assert result.success is False
    assert "timed out" in result.content.lower()


@pytest.mark.asyncio
async def test_shell_exec_with_cwd():
    tool = ShellExec()

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file in the temporary directory
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Test file content")

        # List directory contents using cwd parameter
        result = await tool.execute({"command": "ls", "cwd": tmpdir})
        assert result.success is True
        assert "test.txt" in result.content


@pytest.mark.asyncio
async def test_shell_exec_complex_command():
    tool = ShellExec()
    result = await tool.execute({"command": "echo 'Line 1'; echo 'Line 2'"})
    assert result.success is True
    lines = result.content.strip().split("\n")
    assert "Line 1" in lines
    assert "Line 2" in lines


@pytest.mark.asyncio
async def test_shell_exec_with_custom_timeout():
    tool = ShellExec()
    result = await tool.execute({"command": "sleep 1", "timeout": 5})
    assert result.success is True
    assert result.content.strip() == ""
