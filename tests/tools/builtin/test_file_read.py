import pytest
import tempfile
import os
from aime.tools.builtin import Read


@pytest.mark.asyncio
async def test_read_existing_file():
    tool = Read()

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
        test_content = "Hello, World!\nThis is a test file."
        f.write(test_content)
        temp_path = f.name

    try:
        result = await tool.execute({"file_path": temp_path})
        assert result.success is True
        assert result.content == test_content
    finally:
        os.unlink(temp_path)


@pytest.mark.asyncio
async def test_read_nonexistent_file():
    tool = Read()
    result = await tool.execute({"file_path": "/path/that/does/not/exist/file.txt"})
    assert result.success is False
    assert "not found" in result.content.lower()


@pytest.mark.asyncio
async def test_read_with_different_encoding():
    tool = Read()

    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        # Write content in latin-1 encoding
        test_content = "Café: this has special characters"
        f.write(test_content.encode("latin-1"))
        temp_path = f.name

    try:
        # Try with default utf-8 first (should fail)
        result = await tool.execute({"file_path": temp_path})
        assert result.success is False

        # Now try with latin-1 encoding
        result = await tool.execute({"file_path": temp_path, "encoding": "latin-1"})
        assert result.success is True
        assert result.content == test_content
    finally:
        os.unlink(temp_path)


@pytest.mark.asyncio
async def test_read_empty_file():
    tool = Read()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        temp_path = f.name

    try:
        result = await tool.execute({"file_path": temp_path})
        assert result.success is True
        assert result.content == ""
    finally:
        os.unlink(temp_path)


@pytest.mark.asyncio
async def test_read_large_file():
    tool = Read()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        # Write 1000 lines
        for i in range(1000):
            f.write(f"Line {i}\n")
        temp_path = f.name

    try:
        result = await tool.execute({"file_path": temp_path})
        assert result.success is True
        lines = result.content.strip().split("\n")
        assert len(lines) == 1000
        assert lines[0] == "Line 0"
        assert lines[999] == "Line 999"
    finally:
        os.unlink(temp_path)
