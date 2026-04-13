#!/usr/bin/env python3
"""
AIME TUI CLI Entry Point.

Command-line interface for starting the AIME Textual User Interface.

Usage:
    aime-tui [OPTIONS] [GOAL]

Options:
    --workspace, -w    Working directory (optional, default: current directory)
    --theme, -t        Theme (optional, default: "claude-code")
    --layout, -l       Layout (optional, default: "horizontal")
    --help, -h         Show this help message

Environment Variables:
    ARK_API_KEY            Volcengine ARK API key
    ANTHROPIC_API_KEY      Anthropic API key
    OPENAI_API_KEY         OpenAI API key
    LLM_MODEL              LLM model name (optional)
    LLM_BASE_URL           LLM base URL (optional)
"""

import argparse
import json
import os
import sys
from typing import Optional, Any

from aime.tools.builtin.bundles import default_tool_bundle
from aime_tui.app import AimeTUI
from aime_tui.config import TUIConfig
from aime.aime import OpenAime
from aime.base.config import AimeConfig
from aime.providers.llm.volcengine import VolcengineLLM
from aime.providers.llm.anthropic import AnthropicLLM
from aime.providers.llm.openai import OpenAILLM
from aime.base.tool import Toolkit


def _ensure_default_config() -> None:
    """Ensure ~/.openaime directory and openaime.json exists, create if not."""
    config_dir = os.path.expanduser("~/.openaime")
    config_file = os.path.join(config_dir, "openaime.json")

    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir, exist_ok=True)
        except OSError:
            return  # If we can't create it, just skip

    if not os.path.exists(config_file):
        # Create default config
        default_config = {
            "llm_provider": "ark",
            "api_key": "",
            "model": "ep-20250405065610-23jvu",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3"
        }
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default config file: {config_file}")
            print("Please edit it to add your API key before running again.\n")
        except OSError:
            pass  # If we can't write, just skip


def _load_llm_from_config() -> Optional[object]:
    """
    Load LLM from ~/.openaime/openaime.json config file, then fallback to environment variables.

    Returns:
        BaseLLM instance or None if no valid LLM configuration found
    """
    # First try to load from config file
    config_dir = os.path.expanduser("~/.openaime")
    config_file = os.path.join(config_dir, "openaime.json")

    config: dict[str, Any] = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            config = {}

    # Get from config, then fallback to environment
    def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
        return config.get(key) or os.getenv(key.upper()) or os.getenv(f"LLM_{key.upper()}") or default

    # Try Volcengine ARK
    llm_provider = get_config("llm_provider") or "ark"
    api_key = get_config("api_key") or get_config("ark_api_key") or get_config("ark_api-key")

    if llm_provider == "ark" and api_key:
        model = get_config("model", "ep-20250405065610-23jvu")
        base_url = get_config("base_url", "https://ark.cn-beijing.volces.com/api/v3")
        return VolcengineLLM(
            api_key=api_key,
            model=model,
            base_url=base_url
        )

    if llm_provider == "anthropic" and api_key:
        model = get_config("model", "claude-3-sonnet-20250219")
        base_url = get_config("base_url")
        if base_url:
            return AnthropicLLM(
                api_key=api_key,
                model=model,
                base_url=base_url
            )
        return AnthropicLLM(
            api_key=api_key,
            model=model
        )

    if llm_provider == "openai" and api_key:
        model = get_config("model", "gpt-4o")
        base_url = get_config("base_url")
        if base_url:
            return OpenAILLM(
                api_key=api_key,
                model=model,
                base_url=base_url
            )
        return OpenAILLM(
            api_key=api_key,
            model=model
        )

    # Fallback to environment variables if config doesn't work
    # Try Volcengine ARK
    ark_api_key = os.getenv("ARK_API_KEY")
    if ark_api_key:
        model = os.getenv("LLM_MODEL", "ep-20250405065610-23jvu")
        base_url = os.getenv("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        return VolcengineLLM(
            api_key=ark_api_key,
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

    # Optional positional argument - goal can be provided later in TUI
    parser.add_argument("goal", nargs="?", help="The goal to achieve (optional, can be input in TUI)")

    # Optional arguments
    parser.add_argument(
        "--workspace", "-w",
        required=False,
        default=".",
        help="Working directory where the agent will operate (default: current directory)"
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

    # Ensure config file exists, create default if not
    _ensure_default_config()

    # Load LLM from config file or environment variables
    llm = _load_llm_from_config()
    if llm is None:
        config_file = os.path.expanduser("~/.openaime/openaime.json")
        print("Error: No valid LLM configuration found")
        print()
        print("Configuration is loaded from:")
        print(f"  1. {config_file} (recommended)")
        print("  2. Environment variables (fallback)")
        print()
        print("Please edit ~/.openaime/openaime.json to configure your LLM provider.")
        print()
        print("Example config:")
        print('  {')
        print('    "llm_provider": "ark",')
        print('    "api_key": "your-api-key-here",')
        print('    "model": "ep-20250405065610-23jvu",')
        print('    "base_url": "https://ark.cn-beijing.volces.com/api/v3"')
        print('  }')
        print()
        sys.exit(1)

    # Validate workspace
    if not os.path.exists(args.workspace):
        print(f"Error: Workspace directory not found: {args.workspace}")
        sys.exit(1)
    if not os.path.isdir(args.workspace):
        print(f"Error: Workspace must be a directory: {args.workspace}")
        sys.exit(1)

    # Get absolute workspace path
    workspace = os.path.abspath(args.workspace)

    # Create configurations
    aime_config = AimeConfig()
    tui_config = TUIConfig(
        theme=args.theme,
        layout=args.layout
    )

    toolkit = Toolkit()
    toolkit.add_bundle(
        default_tool_bundle()
        )

    # Create OpenAime instance
    openaime = OpenAime(
        config=aime_config,
        llm=llm,
        toolkit=toolkit,
        workspace=workspace,
        log_level="info"
    )

    # Create TUI app
    app = AimeTUI(
        tui_config=tui_config,
        openaime=openaime,
        initial_goal=args.goal
    )

    # Run the TUI app
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nAIME TUI stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
