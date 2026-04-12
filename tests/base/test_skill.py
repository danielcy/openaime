"""Tests for skill module."""
import os
import tempfile
import time
import pytest
from aime.base.skill import SkillRegistry, SkillMetadata, Skill


def get_test_fixtures_path():
    return os.path.join(os.path.dirname(__file__), "..", "fixtures", "skills")


def test_scan_fixtures():
    """Test scanning skills from fixtures directory."""
    fixtures_path = get_test_fixtures_path()
    registry = SkillRegistry([fixtures_path])

    # First match triggers rescan
    registry._rescan_if_changed()

    assert registry.count_cached_metadata() == 2
    names = [meta.name for meta in registry.get_all_metadata()]
    assert "test-skill-1" in names
    assert "test-skill-2" in names


def test_load_skill():
    """Test loading a full skill."""
    fixtures_path = get_test_fixtures_path()
    registry = SkillRegistry([fixtures_path])
    registry._rescan_if_changed()

    skill = registry.load_skill("test-skill-1")

    assert skill.metadata.name == "test-skill-1"
    assert "A test skill for unit testing" in skill.metadata.description
    assert "Test Skill 1" in skill.instructions
    assert "## Instructions" in skill.instructions
    assert skill.loaded_mtime == skill.metadata.mtime


def test_metadata_fields():
    """Test that frontmatter fields are correctly parsed."""
    fixtures_path = get_test_fixtures_path()
    registry = SkillRegistry([fixtures_path])
    registry._rescan_if_changed()

    meta = registry._metadata_cache["test-skill-1"]
    assert meta.argument_hint == []
    assert meta.user_invocable is True
    assert meta.model == "sonnet"
    assert meta.allowed_tools == ["Read", "Grep"]

    meta2 = registry._metadata_cache["test-skill-2"]
    assert meta2.user_invocable is False


def test_hot_reload_detection():
    """Test that modified files are reloaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a skill
        skill_dir = os.path.join(tmpdir, "hot-reload-test")
        os.mkdir(skill_dir)
        skill_file = os.path.join(skill_dir, "SKILL.md")

        with open(skill_file, 'w') as f:
            f.write("""---
name: hot-reload-test
description: Original description
---
Original instructions
""")

        registry = SkillRegistry([tmpdir])
        registry._rescan_if_changed()
        skill = registry.load_skill("hot-reload-test")
        assert skill.instructions.strip() == "Original instructions"
        assert skill.metadata.description == "Original description"

        # Wait a bit for mtime to change
        time.sleep(0.1)

        # Modify the file
        with open(skill_file, 'w') as f:
            f.write("""---
name: hot-reload-test
description: Updated description
---
Updated instructions
""")

        # Next match should reload
        registry._rescan_if_changed()
        skill2 = registry.load_skill("hot-reload-test")
        assert skill2.instructions.strip() == "Updated instructions"
        assert skill2.metadata.description == "Updated description"


def test_expand_user_path():
    """Test that ~ is expanded in search paths."""
    registry = SkillRegistry(["~/.openaime/skills"])
    # ~ should be expanded
    assert registry._search_paths[0].startswith(os.path.expanduser("~"))
