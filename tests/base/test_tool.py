import pytest
from typing import Any
from aime.base.tool import BaseTool, ToolResult, ToolBundle, Toolkit
from aime.base.types import ArtifactReference


# Test concrete implementation of BaseTool
class ConcreteTool(BaseTool):
    @property
    def name(self) -> str:
        return "test_tool"

    @property
    def description(self) -> str:
        return "A test tool for demonstration purposes"

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"},
                "param2": {"type": "integer", "description": "Second parameter"}
            },
            "required": ["param1"]
        }

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        param1 = parameters.get("param1", "default")
        param2 = parameters.get("param2", 0)
        content = f"Executed test tool with param1={param1}, param2={param2}"
        return ToolResult(
            success=True,
            content=content,
            artifact=ArtifactReference(
                type="file",
                path="/tmp/test_output.txt",
                description="Test output file"
            )
        )


class AnotherConcreteTool(BaseTool):
    @property
    def name(self) -> str:
        return "another_test_tool"

    @property
    def description(self) -> str:
        return "Another test tool for demonstration purposes"

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text input"}
            },
            "required": ["text"]
        }

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        text = parameters.get("text", "")
        return ToolResult(
            success=True,
            content=f"Processed text: {text.upper()}",
            artifact=None
        )


class FailingTool(BaseTool):
    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "A tool that always fails"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        return ToolResult(
            success=False,
            content="This tool always fails",
            artifact=None
        )


def test_tool_result_creation():
    # Test with artifact
    artifact = ArtifactReference("file", "/tmp/test.txt", "Test file")
    result = ToolResult(success=True, content="Test content", artifact=artifact)
    assert result.success is True
    assert result.content == "Test content"
    assert result.artifact == artifact
    assert isinstance(result.artifact, ArtifactReference)

    # Test without artifact
    result = ToolResult(success=False, content="Error message", artifact=None)
    assert result.success is False
    assert result.content == "Error message"
    assert result.artifact is None


def test_tool_bundle_creation():
    tool1 = ConcreteTool()
    tool2 = AnotherConcreteTool()

    bundle = ToolBundle(
        name="test_bundle",
        description="A bundle of test tools",
        tools=[tool1, tool2]
    )

    assert bundle.name == "test_bundle"
    assert bundle.description == "A bundle of test tools"
    assert len(bundle.tools) == 2
    assert tool1 in bundle.tools
    assert tool2 in bundle.tools
    assert all(isinstance(tool, BaseTool) for tool in bundle.tools)


def test_toolkit_creation():
    toolkit = Toolkit()
    assert len(toolkit.get_all_tools()) == 0

    # Add tools via bundles
    tool1 = ConcreteTool()
    tool2 = AnotherConcreteTool()
    bundle1 = ToolBundle("bundle1", "First bundle", [tool1])
    bundle2 = ToolBundle("bundle2", "Second bundle", [tool2])

    toolkit.add_bundle(bundle1)
    toolkit.add_bundle(bundle2)

    all_tools = toolkit.get_all_tools()
    assert len(all_tools) == 2
    assert tool1 in all_tools
    assert tool2 in all_tools


def test_get_tool_by_name():
    toolkit = Toolkit()

    tool1 = ConcreteTool()
    tool2 = AnotherConcreteTool()
    bundle = ToolBundle("test_bundle", "A bundle of test tools", [tool1, tool2])
    toolkit.add_bundle(bundle)

    # Test finding existing tool
    found_tool = toolkit.get_tool_by_name("test_tool")
    assert found_tool is not None
    assert found_tool.name == "test_tool"

    found_tool = toolkit.get_tool_by_name("another_test_tool")
    assert found_tool is not None
    assert found_tool.name == "another_test_tool"

    # Test finding non-existent tool
    assert toolkit.get_tool_by_name("nonexistent_tool") is None


def test_system_prompt_generation():
    toolkit = Toolkit()

    tool1 = ConcreteTool()
    tool2 = AnotherConcreteTool()
    bundle = ToolBundle("test_bundle", "A bundle of test tools", [tool1, tool2])
    toolkit.add_bundle(bundle)

    system_prompt = toolkit.get_system_prompt()

    # Check that prompt contains bundle and tool information
    assert "test_bundle" in system_prompt
    assert "A bundle of test tools" in system_prompt
    assert "test_tool" in system_prompt
    assert "A test tool for demonstration purposes" in system_prompt
    assert "another_test_tool" in system_prompt
    assert "Another test tool for demonstration purposes" in system_prompt


@pytest.mark.asyncio
async def test_concrete_tool_execution():
    tool = ConcreteTool()
    result = await tool.execute({"param1": "hello", "param2": 42})

    assert result.success is True
    assert "Executed test tool with param1=hello, param2=42" in result.content
    assert result.artifact is not None
    assert result.artifact.type == "file"
    assert result.artifact.path == "/tmp/test_output.txt"
    assert "Test output file" in result.artifact.description


@pytest.mark.asyncio
async def test_failing_tool_execution():
    tool = FailingTool()
    result = await tool.execute({})

    assert result.success is False
    assert "This tool always fails" in result.content
    assert result.artifact is None


@pytest.mark.asyncio
async def test_multiple_tool_execution():
    tool1 = ConcreteTool()
    tool2 = AnotherConcreteTool()

    result1 = await tool1.execute({"param1": "test"})
    result2 = await tool2.execute({"text": "test input"})

    assert result1.success
    assert result2.success
    assert "Executed test tool" in result1.content
    assert "Processed text: TEST INPUT" in result2.content
