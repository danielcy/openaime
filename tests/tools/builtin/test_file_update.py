import pytest
import tempfile
import os
from aime.tools.builtin import Update


@pytest.mark.asyncio
async def test_update_append():
    tool = Update()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Original line\n")
        file_path = f.name

    try:
        append_content = "Appended line\n"
        result = await tool.execute({
            "file_path": file_path,
            "content": append_content,
            "mode": "append"
        })
        assert result.success is True
        assert "appended" in result.content.lower()

        with open(file_path, "r") as f:
            content = f.read()
            assert content == "Original line\nAppended line\n"
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_update_replace():
    tool = Update()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Original content")
        file_path = f.name

    try:
        new_content = "Completely new content"
        result = await tool.execute({
            "file_path": file_path,
            "content": new_content,
            "mode": "replace"
        })
        assert result.success is True
        assert "replaced" in result.content.lower()

        with open(file_path, "r") as f:
            assert f.read() == new_content
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_update_search_replace():
    tool = Update()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Hello, World! World is great.")
        file_path = f.name

    try:
        result = await tool.execute({
            "file_path": file_path,
            "search_text": "World",
            "replace_text": "Universe",
            "mode": "search_replace"
        })
        assert result.success is True
        assert "Replaced 2" in result.content

        with open(file_path, "r") as f:
            assert f.read() == "Hello, Universe! Universe is great."
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_update_search_replace_not_found():
    tool = Update()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Hello, World!")
        file_path = f.name

    try:
        result = await tool.execute({
            "file_path": file_path,
            "search_text": "Nonexistent",
            "replace_text": "Something",
            "mode": "search_replace"
        })
        assert result.success is False
        assert "not found" in result.content.lower()
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_update_nonexistent_file():
    tool = Update()
    result = await tool.execute({
        "file_path": "/path/that/does/not/exist/file.txt",
        "content": "test",
        "mode": "append"
    })
    assert result.success is False
    assert "not found" in result.content.lower()


@pytest.mark.asyncio
async def test_update_invalid_mode():
    tool = Update()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        file_path = f.name

    try:
        result = await tool.execute({
            "file_path": file_path,
            "content": "test",
            "mode": "invalid_mode"
        })
        assert result.success is False
        assert "invalid mode" in result.content.lower()
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_update_missing_content_for_append():
    tool = Update()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        file_path = f.name

    try:
        result = await tool.execute({
            "file_path": file_path,
            "mode": "append"
            # Missing content parameter
        })
        assert result.success is False
        assert "content parameter is required" in result.content
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_update_missing_search_text():
    tool = Update()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        file_path = f.name

    try:
        result = await tool.execute({
            "file_path": file_path,
            "replace_text": "replacement",
            "mode": "search_replace"
            # Missing search_text
        })
        assert result.success is False
        assert "search_text and replace_text" in result.content
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_update_default_mode_is_append():
    tool = Update()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Original")
        file_path = f.name

    try:
        # Mode not specified - should default to append
        result = await tool.execute({
            "file_path": file_path,
            "content": "Appended"
        })
        assert result.success is True

        with open(file_path, "r") as f:
            assert f.read() == "OriginalAppended"
    finally:
        os.unlink(file_path)
