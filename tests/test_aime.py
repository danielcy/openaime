"""
Tests for OpenAime class workspace functionality.
"""

import os
import tempfile
import unittest
from unittest.mock import Mock, AsyncMock
import asyncio

from aime.aime import OpenAime
from aime.base.config import AimeConfig


class TestOpenAimeWorkspace(unittest.IsolatedAsyncioTestCase):
    """Tests for OpenAime workspace functionality."""

    async def test_workspace_required_parameter(self):
        """Test that workspace parameter is required."""
        config = AimeConfig()
        llm = Mock()

        # Should raise TypeError when workspace is not provided
        with self.assertRaises(TypeError):
            OpenAime(config, llm)

    async def test_workspace_must_exist(self):
        """Test that OpenAime raises error if workspace doesn't exist."""
        config = AimeConfig()
        llm = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_dir = os.path.join(temp_dir, "non_existent_directory")

            with self.assertRaises(ValueError):
                OpenAime(config, llm, non_existent_dir)

    async def test_workspace_must_be_directory(self):
        """Test that OpenAime raises error if workspace is not a directory."""
        config = AimeConfig()
        llm = Mock()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name

        try:
            with self.assertRaises(ValueError):
                OpenAime(config, llm, temp_file_path)
        finally:
            os.unlink(temp_file_path)

    async def test_workspace_absolute_path_stored(self):
        """Test that workspace is stored as absolute path."""
        config = AimeConfig()
        llm = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            openaime = OpenAime(config, llm, temp_dir)
            self.assertEqual(os.path.abspath(temp_dir), openaime.workspace)

    async def test_run_changes_working_directory(self):
        """Test that run() method changes working directory to workspace."""
        config = AimeConfig()
        llm = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()

            # Create mock components
            planner = Mock()
            planner.plan_step = AsyncMock(side_effect=[
                Mock(action="COMPLETE_GOAL")
            ])

            openaime = OpenAime(config, llm, temp_dir)

            # Mock internal components
            openaime._initialize_components = AsyncMock()
            openaime._wait_for_goal_completion = AsyncMock(return_value="Goal completed")
            openaime._cleanup = AsyncMock()

            await openaime.run("test goal")

            # Verify original working directory is still current
            self.assertEqual(os.getcwd(), original_cwd)

    async def test_run_restores_working_directory_on_error(self):
        """Test that run() restores original working directory even when error occurs."""
        config = AimeConfig()
        llm = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()

            openaime = OpenAime(config, llm, temp_dir)

            # Make initialization fail
            openaime._initialize_components = AsyncMock(side_effect=Exception("Initialization error"))
            openaime._cleanup = AsyncMock()

            with self.assertRaises(Exception):
                await openaime.run("test goal")

            # Verify original working directory is still current
            self.assertEqual(os.getcwd(), original_cwd)


if __name__ == "__main__":
    unittest.main()
