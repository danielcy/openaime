import pytest
import tempfile
import os
from aime.tools.builtin import Write


@pytest.mark.asyncio
async def test_write_new_file():
    tool = Write()

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        test_content = "Hello, World!\nThis is a test."

        result = await tool.execute({"file_path": file_path, "content": test_content})
        assert result.success is True
        assert "written successfully" in result.content.lower()

        # Verify file was written correctly
        with open(file_path, "r") as f:
            assert f.read() == test_content


@pytest.mark.asyncio
async def test_write_overwrite_existing_file():
    tool = Write()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Original content")
        file_path = f.name

    try:
        new_content = "New content that overwrites"
        result = await tool.execute({"file_path": file_path, "content": new_content})
        assert result.success is True

        with open(file_path, "r") as f:
            assert f.read() == new_content
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_write_with_nested_directories():
    tool = Write()

    with tempfile.TemporaryDirectory() as tmpdir:
        nested_path = os.path.join(tmpdir, "level1", "level2", "level3", "test.txt")
        test_content = "Content in nested directory"

        result = await tool.execute({"file_path": nested_path, "content": test_content})
        assert result.success is True

        with open(nested_path, "r") as f:
            assert f.read() == test_content


@pytest.mark.asyncio
async def test_write_empty_content():
    tool = Write()

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "empty.txt")

        result = await tool.execute({"file_path": file_path, "content": ""})
        assert result.success is True

        with open(file_path, "r") as f:
            assert f.read() == ""


@pytest.mark.asyncio
async def test_write_with_encoding():
    tool = Write()

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "cafe.txt")
        test_content = "Café with special characters"

        # Write with latin-1 encoding
        result = await tool.execute({
            "file_path": file_path,
            "content": test_content,
            "encoding": "latin-1"
        })
        assert result.success is True

        # Read back with latin-1 encoding to verify
        with open(file_path, "r", encoding="latin-1") as f:
            assert f.read() == test_content
