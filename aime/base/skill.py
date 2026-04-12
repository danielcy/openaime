"""
Skill Registry - Progressive disclosure skills system with hot-reload.

Supports Claude Code compatible skill format:
- Each skill is a directory containing a SKILL.md file
- SKILL.md has YAML frontmatter with metadata
- Progressive disclosure: metadata only scanned by default, full content loaded on match
- Hot-reload: automatically detects file changes and reloads

Skills are discovered from three search paths by default: `~/.openaime/skills`, `{workspace}/skills`, and user-provided extra paths.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional, List
import yaml

from aime.base.llm import BaseLLM, Message


FRONTMATTER_PATTERN = re.compile(
    r'^---\s*\n(.*?)\n---\s*\n',
    re.DOTALL
)


@dataclass
class SkillMetadata:
    """Level 1: Metadata loaded at scan time (progressive disclosure)."""
    name: str
    description: str
    path: str  # Absolute path to skill directory
    skill_file_path: str  # Absolute path to SKILL.md
    mtime: float  # Last modified time of SKILL.md for hot-reload detection

    # Optional frontmatter fields
    argument_hint: Optional[str] = None
    disable_model_invocation: bool = False
    user_invocable: bool = False
    allowed_tools: Optional[List[str]] = None
    model: Optional[str] = None
    context: Optional[str] = None
    agent: Optional[str] = None
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Skill:
    """Full skill after loading (Level 2)."""
    metadata: SkillMetadata
    instructions: str  # Full SKILL.md content after frontmatter
    loaded_mtime: float  # mtime when loaded, for cache invalidation


class SkillRegistry:
    """Registry for managing skills with progressive disclosure and hot-reload.

    Discovery paths (default):
    1. ~/.openaime/skills - User global skills
    2. {workspace}/skills - Workspace specific skills
    3. User-provided additional paths
    """

    def __init__(self, search_paths: List[str]):
        """Initialize registry with search paths.

        Args:
            search_paths: List of directories to search for skills.
                Each directory contains subdirectories which are skills.
        """
        self._search_paths = self._expand_paths(search_paths)
        self._metadata_cache: dict[str, SkillMetadata] = {}
        self._loaded_cache: dict[str, Skill] = {}

    def _expand_paths(self, paths: List[str]) -> List[str]:
        """Expand user ~ in paths."""
        expanded = []
        for path in paths:
            expanded.append(os.path.abspath(os.path.expanduser(path)))
        return expanded

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from SKILL.md content.

        Returns:
            (frontmatter_dict, content_after_frontmatter)
        """
        match = FRONTMATTER_PATTERN.match(content)
        if match:
            try:
                fm = yaml.safe_load(match.group(1))
                content = content[match.end():]
                return fm or {}, content
            except yaml.YAMLError:
                return {}, content
        return {}, content

    def _parse_metadata(self, skill_dir: str, skill_file: str) -> SkillMetadata:
        """Parse metadata from SKILL.md file."""
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        fm, _ = self._parse_frontmatter(content)

        mtime = os.path.getmtime(skill_file)

        return SkillMetadata(
            name=fm.get('name', os.path.basename(skill_dir)),
            description=fm.get('description', ''),
            path=os.path.abspath(skill_dir),
            skill_file_path=os.path.abspath(skill_file),
            mtime=mtime,
            argument_hint=fm.get('argument-hint'),
            disable_model_invocation=fm.get('disable-model-invocation', False),
            user_invocable=fm.get('user-invocable', False),
            allowed_tools=fm.get('allowed-tools'),
            model=fm.get('model'),
            context=fm.get('context'),
            agent=fm.get('agent'),
            license=fm.get('license'),
            compatibility=fm.get('compatibility'),
            metadata=fm.get('metadata', {}),
        )

    def _load_full(self, metadata: SkillMetadata) -> Skill:
        """Load full skill content from disk (Level 2)."""
        with open(metadata.skill_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        _, instructions = self._parse_frontmatter(content)
        instructions = instructions.strip()

        return Skill(
            metadata=metadata,
            instructions=instructions,
            loaded_mtime=metadata.mtime,
        )

    def _rescan_if_changed(self) -> None:
        """Rescan all search paths and reload metadata for modified skills.

        This is called before every match to enable hot-reload.
        """
        for base_path in self._search_paths:
            if not os.path.exists(base_path):
                continue

            if not os.path.isdir(base_path):
                continue

            # Iterate over each subdirectory - each is a skill
            for entry in os.listdir(base_path):
                skill_dir = os.path.join(base_path, entry)
                if not os.path.isdir(skill_dir):
                    continue

                skill_file = os.path.join(skill_dir, "SKILL.md")
                if not os.path.exists(skill_file):
                    continue

                current_mtime = os.path.getmtime(skill_file)

                # Check if we need to reload
                need_reload = False
                if entry not in self._metadata_cache:
                    need_reload = True
                else:
                    cached = self._metadata_cache[entry]
                    if cached.mtime != current_mtime:
                        need_reload = True

                if need_reload:
                    metadata = self._parse_metadata(skill_dir, skill_file)
                    # Use metadata.name as key, not directory name (allows name != dir name)
                    self._metadata_cache[metadata.name] = metadata
                    # Clear from loaded cache if it was loaded
                    if metadata.name in self._loaded_cache:
                        del self._loaded_cache[metadata.name]

    def get_all_metadata(self) -> List[SkillMetadata]:
        """Get all skill metadata."""
        self._rescan_if_changed()
        return list(self._metadata_cache.values())

    def load_skill(self, name: str) -> Skill:
        """Load a full skill by name (manual loading or after matching)."""
        self._rescan_if_changed()

        if name not in self._metadata_cache:
            raise ValueError(f"Skill '{name}' not found in any search path")

        metadata = self._metadata_cache[name]
        current_mtime = metadata.mtime

        # Check cache
        if name in self._loaded_cache:
            loaded = self._loaded_cache[name]
            if loaded.loaded_mtime == current_mtime:
                return loaded

        # Load from disk
        skill = self._load_full(metadata)
        self._loaded_cache[name] = skill
        return skill

    def match(self, llm: BaseLLM, task_description: str, top_k: int = 3) -> List[Skill]:
        """Match skills to task description using LLM.

        Args:
            llm: LLM instance to use for matching
            task_description: Description of the current task
            top_k: Maximum number of skills to return

        Returns:
            List of loaded Skill objects ready for injection into prompt
        """
        self._rescan_if_changed()

        all_metadata = self.get_all_metadata()
        if not all_metadata:
            return []

        # Build prompt for matching
        metadata_list = "\n".join([
            f"- **{meta.name}**: {meta.description}"
            for meta in all_metadata
        ])

        prompt = f"""Given a task description, select the {top_k} most relevant skills that should be activated to help complete the task.

Task Description: {task_description}

Available Skills:
{metadata_list}

Instructions:
- Analyze the task requirements
- Select up to {top_k} skills that are most relevant
- Output ONLY a JSON array of skill names that should be activated
- If no skills are relevant, output an empty array []

Example Output:
["python-code-review", "git-commit-guide"]
"""
        messages = [Message(role="user", content=prompt)]
        response = llm.complete(messages, temperature=0.0)
        content = response.content.strip() if response.content else "[]"

        # Extract JSON from response
        import json
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        try:
            selected_names = json.loads(content)
        except json.JSONDecodeError:
            # Failed to parse, return empty
            return []

        if not isinstance(selected_names, list):
            return []

        # Load selected skills
        matched = []
        for name in selected_names[:top_k]:
            try:
                skill = self.load_skill(name)
                matched.append(skill)
            except ValueError:
                # Skill not found, skip
                continue

        return matched

    def count_cached_metadata(self) -> int:
        """Get number of cached metadata entries."""
        return len(self._metadata_cache)

    def count_loaded(self) -> int:
        """Get number of fully loaded skills."""
        return len(self._loaded_cache)

    def clear_cache(self) -> None:
        """Clear all caches, force full rescan on next match."""
        self._metadata_cache.clear()
        self._loaded_cache.clear()
