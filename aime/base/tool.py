from __future__ import annotations
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
from .types import ArtifactReference


@dataclass
class ToolResult:
    """Result from executing a tool."""
    success: bool
    content: str
    artifact: Optional[ArtifactReference] = None


@dataclass
class ToolBundle:
    """A collection of related tools with a common description."""
    name: str
    description: str
    tools: list[BaseTool]


class BaseTool(ABC):
    """Abstract base class for tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A description of what the tool does."""
        pass

    @abstractmethod
    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON Schema describing the tool's input parameters."""
        pass

    @abstractmethod
    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Execute the tool with the given parameters."""
        pass


class Toolkit:
    """Manages multiple ToolBundles and provides access to all tools."""

    def __init__(self):
        self._bundles: list[ToolBundle] = []

    def add_bundle(self, bundle: ToolBundle) -> None:
        """Add a bundle to the toolkit."""
        self._bundles.append(bundle)

    def get_all_tools(self) -> list[BaseTool]:
        """Get all tools from all bundles."""
        all_tools = []
        for bundle in self._bundles:
            all_tools.extend(bundle.tools)
        return all_tools

    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """Find a tool by name across all bundles."""
        for tool in self.get_all_tools():
            if tool.name == name:
                return tool
        return None

    def get_system_prompt(self) -> str:
        """Generate a system prompt describing all available tools."""
        if not self._bundles:
            return "No tools available."

        prompt_parts = ["Available tools:"]

        for bundle in self._bundles:
            prompt_parts.append(f"\n## {bundle.name}")
            prompt_parts.append(f"{bundle.description}")

            for tool in bundle.tools:
                prompt_parts.append(f"\n### {tool.name}")
                prompt_parts.append(f"{tool.description}")
                prompt_parts.append("Input Schema:")
                prompt_parts.append(json.dumps(tool.get_input_schema(), indent=2))

        return "\n".join(prompt_parts)
