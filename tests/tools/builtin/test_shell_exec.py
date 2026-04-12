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


@pytest.mark.asyncio
async def test_shell_exec_timeout_captures_output():
    """Test that timeout returns captured output before termination."""
    tool = ShellExec()
    # Command that outputs something then sleeps
    result = await tool.execute({
        "command": "echo 'Hello before timeout'; sleep 2",
        "timeout": 1
    })
    assert result.success is False
    assert "timed out" in result.content.lower()
    assert "Hello before timeout" in result.content


@pytest.mark.asyncio
async def test_shell_exec_large_output_truncation():
    """Test that large output is truncated at 10MB limit."""
    tool = ShellExec()
    # Create a command that generates about 1MB of data (repeat 100KB 10 times)
    # We'll use a smaller size for test speed, but enough to verify truncation works
    # Create a script that outputs data in chunks with delays so we can see truncation
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
import sys
import time
# Output 500KB of data
chunk = 'x' * 10240  # 10KB per chunk
for i in range(50):
    print(chunk, end='', flush=True)
    time.sleep(0.01)  # Small delay to allow reading
''')
        temp_script = f.name

    try:
        # Temporarily set max output to 100KB for testing
        original_max = tool.MAX_OUTPUT_BYTES
        tool.MAX_OUTPUT_BYTES = 100 * 1024  # 100KB

        result = await tool.execute({"command": f"python {temp_script}"})

        # Restore original value
        tool.MAX_OUTPUT_BYTES = original_max

        assert result.success is True
        assert "truncated" in result.content
        assert "exceeded" in result.content
    finally:
        os.unlink(temp_script)


@pytest.mark.asyncio
async def test_shell_exec_unicode_output():
    """Test that unicode output is handled correctly."""
    tool = ShellExec()
    result = await tool.execute({"command": "echo 'Hello 世界 🌍'"})
    assert result.success is True
    assert "Hello" in result.content
    assert "世界" in result.content
    assert "🌍" in result.content


@pytest.mark.asyncio
async def test_shell_exec_binary_output_fallback():
    """Test that binary output falls back to latin-1 decoding."""
    tool = ShellExec()
    # Create a command that outputs binary data
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.bin', delete=False) as f:
        f.write(b'\x80\x81\x82\x83')  # Non-UTF-8 bytes
        temp_file = f.name

    try:
        result = await tool.execute({"command": f"cat {temp_file}"})
        # Should not crash with UnicodeDecodeError
        assert result.success is True
    finally:
        os.unlink(temp_file)


@pytest.mark.asyncio
async def test_shell_exec_timeout_with_continuous_output():
    """Test timeout with continuous streaming output."""
    tool = ShellExec()
    # Create a script that outputs a line every 0.1s
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
import time
for i in range(20):
    print(f"Line {i}", flush=True)
    time.sleep(0.1)
''')
        temp_script = f.name

    try:
        result = await tool.execute({
            "command": f"python {temp_script}",
            "timeout": 0.5  # Should get about 5 lines
        })

        assert result.success is False
        assert "timed out" in result.content.lower()
        # Should have captured some output
        assert "Line 0" in result.content
    finally:
        os.unlink(temp_script)
