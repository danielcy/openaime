from aime.base.tool import ToolBundle
from aime.tools.builtin import Read, ShellExec, Update, Write, AskUserQuestion



def default_tool_bundle() -> ToolBundle:
    return ToolBundle(
            name="Default tools", 
            description="Default tools, you must use them", 
            tools=[
                ShellExec(),
                Read(),
                Write(),
                Update(),
                AskUserQuestion()
            ],
        )