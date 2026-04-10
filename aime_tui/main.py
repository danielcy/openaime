#!/usr/bin/env python3
"""
AIME TUI CLI Entry Point.

Command-line interface for starting the AIME Textual User Interface.

Usage:
    aime-tui [OPTIONS] GOAL

Options:
    --workspace, -w    Working directory (required)
    --theme, -t        Theme (optional, default: "claude-code")
    --layout, -l       Layout (optional, default: "horizontal")
    --help, -h         Show this help message

Environment Variables:
    VOLCENGINE_API_KEY     Volcengine API key
    ANTHROPIC_API_KEY      Anthropic API key
    OPENAI_API_KEY         OpenAI API key
    LLM_MODEL              LLM model name (optional)
    LLM_BASE_URL           LLM base URL (optional)
"""

import argparse
import os
import sys
from typing import Optional

from aime_tui.app import AimeTUI
from aime_tui.config import TUIConfig
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.providers.llm.volcengine import VolcengineLLM
from aime.providers.llm.anthropic import AnthropicLLM
from aime.providers.llm.openai import OpenAILLM


def _load_llm_from_env() -> Optional[object]:
    """
    Load LLM from environment variables.

    Returns:
        BaseLLM instance or None if no valid LLM configuration found
    """
    # Try Volcengine
    volcengine_api_key = os.getenv("VOLCENGINE_API_KEY")
    if volcengine_api_key:
        model = os.getenv("LLM_MODEL", "ep-20250405065610-23jvu")
        base_url = os.getenv("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        return VolcengineLLM(
            api_key=volcengine_api_key,
            model=model,
            base_url=base_url
        )

    # Try Anthropic
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_api_key:
        model = os.getenv("LLM_MODEL", "claude-3-sonnet-20250219")
        base_url = os.getenv("LLM_BASE_URL")
        if base_url:
            return AnthropicLLM(
                api_key=anthropic_api_key,
                model=model,
                base_url=base_url
            )
        return AnthropicLLM(
            api_key=anthropic_api_key,
            model=model
        )

    # Try OpenAI
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        model = os.getenv("LLM_MODEL", "gpt-4o")
        base_url = os.getenv("LLM_BASE_URL")
        if base_url:
            return OpenAILLM(
                api_key=openai_api_key,
                model=model,
                base_url=base_url
            )
        return OpenAILLM(
            api_key=openai_api_key,
            model=model
        )

    return None


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="aime-tui",
        description="AIME Textual User Interface - Autonomous Interactive Execution Engine"
    )

    # Required arguments
    parser.add_argument("goal", help="The goal to achieve")

    # Optional arguments
    parser.add_argument(
        "--workspace", "-w",
        required=True,
        help="Working directory where the agent will operate"
    )
    parser.add_argument(
        "--theme", "-t",
        default="claude-code",
        choices=["claude-code", "monokai", "default"],
        help="TUI theme (default: claude-code)"
    )
    parser.add_argument(
        "--layout", "-l",
        default="horizontal",
        choices=["horizontal", "vertical"],
        help="TUI layout (default: horizontal)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Load LLM from environment
    llm = _load_llm_from_env()
    if llm is None:
        print("Error: No LLM configuration found in environment variables")
        print("Please set one of the following:")
        print("  - VOLCENGINE_API_KEY")
        print("  - ANTHROPIC_API_KEY")
        print("  - OPENAI_API_KEY")
        sys.exit(1)

    # Validate workspace
    if not os.path.exists(args.workspace):
        print(f"Error: Workspace directory not found: {args.workspace}")
        sys.exit(1)
    if not os.path.isdir(args.workspace):
        print(f"Error: Workspace must be a directory: {args.workspace}")
        sys.exit(1)

    # Create configurations
    aime_config = AimeConfig()
    tui_config = TUIConfig(
        theme=args.theme,
        layout=args.layout
    )

    # Create OpenAime instance
    openaime = OpenAime(
        config=aime_config,
        llm=llm,
        workspace=args.workspace
    )

    # Create TUI app
    app = AimeTUI(
        tui_config=tui_config,
        openaime=openaime
    )

    # Run the TUI app with the goal
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nAIME TUI stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
