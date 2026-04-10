#!/usr/bin/env python3
"""Demo script showing how to use AIME TUI."""
import asyncio
import os
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.providers.llm.volcengine import VolcengineLLM
from aime.base.tool import Toolkit, ToolBundle
from aime.tools.builtin import Read, ShellExec, Update, Write
from aime_tui.app import AimeTUI
from aime_tui.config import TUIConfig


async def main():
    # Initialize LLM
    llm = VolcengineLLM(
        api_key=os.environ.get("VOLCENGINE_API_KEY"),
        base_url="https://ark.cn-beijing.volces.com/api/coding/v3",
        model="ark-code-latest"
    )

    # Setup tools
    toolkit = Toolkit()
    toolkit.add_bundle(
        ToolBundle(
            name="Default tools",
            description="Default tools",
            tools=[ShellExec(), Read(), Write(), Update()],
        )
    )

    # Create OpenAime
    aime = OpenAime(
        config=AimeConfig(),
        llm=llm,
        toolkit=toolkit,
        workspace=".demo/workspace",
        log_level=None,  # Disable logging since TUI displays everything
    )

    # Create TUI
    tui = AimeTUI(
        openaime=aime,
        config=TUIConfig(
            theme="claude-code",
            layout="horizontal",
            show_debug_events=True,
        )
    )

    # Get goal from user or use default
    goal = input("Enter your goal: ") or "Write a hello world Python program"

    # Run TUI - this will block until done
    await tui.run_goal(goal)


if __name__ == "__main__":
    asyncio.run(main())