"""
DynamicActor Component - Specialized actor for executing a single subtask in AIME.

According to the AIME paper, each DynamicActor:
- Is instantiated by ActorFactory for a specific subtask
- Runs a complete ReAct execution loop: thought → action → observation
- Updates progress in real-time using UpdateProgress tool
- Reports final result back to planner when done
- Has customized role, tools, and knowledge based on task needs
"""
import asyncio
import logging
import os
import re
import json
import platform
from datetime import datetime
from typing import Optional, List, Tuple, Any, Callable

from aime.base.types import Task, TaskStatus, ActorResult, ArtifactReference
from aime.base.tool import ToolResult
from aime.base.llm import BaseLLM, Message
from aime.base.tool import BaseTool, Toolkit
from aime.base.config import ActorConfig
from aime.base.knowledge import BaseKnowledge
from aime.base.skill import Skill
from aime.base.events import EventType
from aime.components.progress_module import ProgressModule
from aime.components.planner import Planner

logger = logging.getLogger(__name__)


class DynamicActor:
    """
    DynamicActor is a specialized actor instantiated for a specific subtask.
    It runs a complete ReAct loop (thought → action → observation) until
    the subtask is completed or fails.

    According to AIME paper: each actor gets exactly the tools, role, and
    knowledge it needs for this specific task - no more, no less.
    """

    def __init__(
        self,
        actor_id: str,
        role: str,
        task: Task,
        llm: BaseLLM,
        planner: Planner,
        progress: ProgressModule,
        toolkit: Toolkit,
        knowledge: BaseKnowledge,
        config: ActorConfig,
        emit_event: None | Callable[[EventType, dict[str, Any]], None] = None,
        matched_skills: list[Skill] = [],
    ):
        """
        Initialize the DynamicActor for a specific subtask.

        Args:
            actor_id: Unique identifier for this actor
            role: Specialized role description for this task
            task: The subtask to execute
            llm: LLM instance to use for this actor
            planner: The planner coordinating overall execution
            progress: Progress module for updating status
            toolkit: Customized toolkit for this task
            knowledge: Knowledge base for retrieval
            config: Actor configuration
            emit_event: Optional callback to emit events (used for real-time streaming).
            matched_skills: List of matched skills to inject into system prompt
        """
        self.actor_id = actor_id
        self.role = role
        self.task = task
        self.llm = llm
        self.planner = planner
        self.progress = progress
        self.toolkit = toolkit
        self.knowledge = knowledge
        self.config = config
        self._emit_event = emit_event

        self._running = False
        self._lock = asyncio.Lock()

        # Conversation history for ReAct
        self._history: List[Message] = []
        self._matched_skills = matched_skills

    async def run(self) -> ActorResult:
        """
        Main entry point: run the complete ReAct execution loop until done.

        Returns:
            ActorResult with final status and result
        """
        async with self._lock:
            if self._running:
                raise RuntimeError(f"Actor {self.actor_id} is already running")
            self._running = True

        logger.info(f"Actor {self.actor_id} starting execution for task: {self.task.description}")
        if self._emit_event is not None:
            self._emit_event(EventType.ACTOR_STARTED, {
                "actor_id": self.actor_id,
                "task_id": self.task.id,
                "role": self.role,
            })
        await self.progress.update_task_status(
            self.task.id, TaskStatus.IN_PROGRESS, f"Actor {self.actor_id} started execution"
        )

        retry_count = 0
        max_retries = self.config.max_retries

        while retry_count <= max_retries:
            try:
                result = await self._react_loop()
                if result.status == TaskStatus.COMPLETED:
                    logger.info(f"Actor {self.actor_id} completed task {self.task.id} successfully")
                    await self.progress.update_task_status(
                        self.task.id, TaskStatus.COMPLETED, result.summary
                    )
                    if self._emit_event is not None:
                        self._emit_event(EventType.ACTOR_FINISHED, {
                            "actor_id": self.actor_id,
                            "task_id": self.task.id,
                            "status": result.status,
                            "summary": result.summary,
                        })
                    async with self._lock:
                        self._running = False
                    return result
                else:
                    logger.warning(f"Actor {self.actor_id} task {self.task.id} failed: {result.summary}")
                    await self.progress.update_task_status(
                        self.task.id, TaskStatus.FAILED, result.summary
                    )
                    if self._emit_event is not None:
                        self._emit_event(EventType.ACTOR_FINISHED, {
                            "actor_id": self.actor_id,
                            "task_id": self.task.id,
                            "status": result.status,
                            "summary": result.summary,
                        })
                    retry_count += 1
                    if retry_count <= max_retries:
                        logger.debug(f"Actor {self.actor_id} retrying (attempt {retry_count}/{max_retries})")
                        await asyncio.sleep(1.0)

            except Exception as e:
                error_msg = f"Exception during execution: {str(e)}"
                logger.error(f"Actor {self.actor_id} {error_msg}")
                await self.progress.update_task_status(
                    self.task.id, TaskStatus.FAILED, error_msg
                )
                retry_count += 1
                if retry_count <= max_retries:
                    logger.debug(f"Actor {self.actor_id} retrying after exception (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(1.0)

        # All retries exhausted
        error_msg = f"Task failed after {max_retries} retries"
        logger.error(f"Actor {self.actor_id} {error_msg}")
        await self.progress.update_task_status(
            self.task.id, TaskStatus.FAILED, error_msg
        )
        if self._emit_event is not None:
            self._emit_event(EventType.ACTOR_FINISHED, {
                "actor_id": self.actor_id,
                "task_id": self.task.id,
                "status": TaskStatus.FAILED,
                "summary": error_msg,
            })
        async with self._lock:
            self._running = False
        return ActorResult(
            task_id=self.task.id,
            status=TaskStatus.FAILED,
            summary=error_msg,
        )

    async def stop(self) -> None:
        """
        Stop the actor gracefully.
        """
        async with self._lock:
            self._running = False

    async def _react_loop(self) -> ActorResult:
        """
        Run the ReAct loop: thought → action → observation → repeat.

        Supports both native tool calling and text-based ReAct parsing:
        - If LLM returns native tool calls, uses them directly (more reliable)
        - Falls back to text parsing if no native tool calls available

        Returns:
            ActorResult with final result
        """
        logger.debug(f"Actor {self.actor_id} starting ReAct loop")

        # Initialize conversation with system prompt
        self._history = [
            Message(
                role="system",
                content=await self._build_system_prompt()
            )
        ]

        # Convert toolkit tools to standard tool definitions for native tool calling
        # OpenAI format: [{ "type": "function", "function": { "name": ..., "description": ..., "parameters": ... } }]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.get_input_schema(),
                }
            }
            for tool in self.toolkit.get_all_tools()
        ]
        # Add the finish tool
        tools.append({
            "type": "function",
            "function": {
                "name": "finish",
                "description": "Finish the current task when it's completed. Use this when you've achieved the subtask goal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Summary of what you accomplished"
                        }
                    },
                    "required": ["summary"]
                }
            }
        })

        iteration = 0
        max_iterations = self.config.max_iterations

        while iteration < max_iterations:
            async with self._lock:
                if not self._running:
                    return ActorResult(
                        task_id=self.task.id,
                        status=TaskStatus.FAILED,
                        summary="Actor stopped by user",
                    )

            logger.debug(f"Actor {self.actor_id} ReAct iteration {iteration + 1}/{max_iterations}")

            # Get LLM prediction with tool definitions
            response = await self.llm.complete(
                self._history, temperature=self.config.temperature, tools=tools
            )

            # Check for native tool calls first (more reliable)
            thought: Optional[str] = response.content
            tool_name: Optional[str] = None
            parameters: dict[str, Any] = {}

            if response.tool_calls:
                # Use native tool call - take first one (we do one step at a time)
                tool_call = response.tool_calls[0]
                tool_name = tool_call.name
                parameters = tool_call.parameters
                logger.debug(f"Actor {self.actor_id} native tool call selected tool: {tool_name}")
                if thought and self._emit_event is not None:
                    self._emit_event(EventType.ACTOR_THOUGHT, {
                        "actor_id": self.actor_id,
                        "thought": thought,
                    })
            elif response.content:
                # No native tool calls - fall back to text parsing
                parsed = self._parse_response(response.content)
                if not parsed:
                    # Invalid response
                    self._history.append(Message(
                        role="assistant",
                        content=response.content or ""
                    ))
                    self._history.append(Message(
                        role="system",
                        content="Invalid response format. Please use the format: THOUGHT: <your reasoning> ACTION: {\"tool\": \"tool_name\", \"parameters\": {...}}"
                    ))
                    iteration += 1
                    continue

                parsed_thought, parsed_tool_name, parsed_parameters = parsed
                if thought is None:
                    thought = parsed_thought
                tool_name = parsed_tool_name
                parameters = parsed_parameters
                logger.debug(f"Actor {self.actor_id} thought: {thought[:100]}{'...' if len(thought) > 100 else ''}")
                if thought and self._emit_event is not None:
                    self._emit_event(EventType.ACTOR_THOUGHT, {
                        "actor_id": self.actor_id,
                        "thought": thought,
                    })
                if tool_name:
                    logger.debug(f"Actor {self.actor_id} text parsed selected tool: {tool_name}")
            else:
                # No content and no tool calls - invalid
                self._history.append(Message(
                    role="system",
                    content="Empty response from model, please try again with a valid response containing either thought/action or tool call."
                ))
                iteration += 1
                continue

            # Check if we're done
            if tool_name == "finish":
                # Finish the task with the current result
                summary = thought or "Task completed"
                if isinstance(parameters.get("summary"), str):
                    summary = parameters["summary"]
                artifacts = self.task.artifacts
                logger.info(f"Actor {self.actor_id} finishing task: {summary}")
                return ActorResult(
                    task_id=self.task.id,
                    status=TaskStatus.COMPLETED,
                    summary=summary,
                    artifacts=artifacts,
                )

            # Execute the tool
            if not tool_name:
                # No tool selected, continue conversation
                self._history.append(Message(
                    role="assistant",
                    content=response.content or ""
                ))
                iteration += 1
                continue

            # Check if we're done
            if tool_name == "finish":
                # Finish the task with the current result
                summary = thought or "Task completed"
                artifacts = self.task.artifacts
                logger.info(f"Actor {self.actor_id} finishing task: {summary}")
                return ActorResult(
                    task_id=self.task.id,
                    status=TaskStatus.COMPLETED,
                    summary=summary,
                    artifacts=artifacts,
                )

            # Execute the tool
            if not tool_name:
                # No tool selected, continue conversation
                self._history.append(Message(
                    role="assistant",
                    content=response.content or ""
                ))
                iteration += 1
                continue

            tool = self.toolkit.get_tool_by_name(tool_name)
            if not tool:
                observation = f"Error: Tool '{tool_name}' not found in toolkit. Available tools: {', '.join([t.name for t in self.toolkit.get_all_tools()])}"
                logger.warning(f"Actor {self.actor_id}: {observation}")
                self._history.append(Message(
                    role="assistant",
                    content=response.content or ""
                ))
                self._history.append(Message(
                    role="system",
                    content=f"OBSERVATION: {observation}"
                ))
                iteration += 1
                continue

            # Execute the tool
            logger.debug(f"Actor {self.actor_id} executing tool {tool_name} with parameters: {parameters}")
            if self._emit_event is not None:
                self._emit_event(EventType.ACTOR_TOOL_CALLED, {
                    "actor_id": self.actor_id,
                    "tool_name": tool_name,
                    "parameters": parameters,
                })
            tool_result = await tool.execute(parameters)

            if tool_result.success:
                observation = tool_result.content
                logger.debug(f"Actor {self.actor_id} tool succeeded: {observation[:100]}{'...' if len(observation) > 100 else ''}")
            else:
                observation = f"Tool execution failed: {tool_result.content}\nTool: {tool_name}\nParameters: {parameters}"
                logger.warning(f"Actor {self.actor_id} {observation}")
            if self._emit_event is not None:
                self._emit_event(EventType.ACTOR_TOOL_FINISHED, {
                    "actor_id": self.actor_id,
                    "tool_name": tool_name,
                    "success": tool_result.success,
                    "content": tool_result.content,
                })

            # Add to conversation history
            self._history.append(Message(
                role="assistant",
                content=response.content or ""
            ))
            self._history.append(Message(
                role="system",
                content=f"OBSERVATION: {observation}"
            ))

            iteration += 1

        # Max iterations reached
        return ActorResult(
            task_id=self.task.id,
            status=TaskStatus.FAILED,
            summary=f"Reached maximum iterations ({max_iterations}) without completing",
        )

    async def _build_system_prompt(self) -> str:
        """
        Build the system prompt for this actor, including:
        - Role (from task specialization)
        - Task description and completion criteria
        - Global progress (all tasks with status) to avoid repeating work
        - Available tools
        - ReAct instructions

        Returns:
            Formatted system prompt string
        """
        tools = self.toolkit.get_all_tools()
        tools_description = "\n".join([
            f"Tool: {tool.name}\nDescription: {tool.description}\nInput Schema: {tool.get_input_schema()}\n"
            for tool in tools
        ])

        # Add special finish tool
        tools_description += """
Special Tool: finish
Description: Finish the current task when it's completed. Use this when you've achieved the subtask goal.
Input Schema: {"type": "object", "properties": {"summary": {"type": "string", "description": "Summary of what you accomplished"}}}
"""

        # Add environment context (ε from paper)
        env_info = f"""Environment Context:
OS: {platform.system()} {platform.release()}
Python Version: {platform.python_version()}
Current Time: {datetime.now().isoformat()}
"""

        # Add global progress context - show all tasks and their current status
        # This prevents the actor from repeating work already done by other actors
        all_tasks = await self.progress.get_all_tasks()
        progress_info = "Global Progress - All Tasks:\n"
        for task in all_tasks:
            status_mark = "✓" if task.status == TaskStatus.COMPLETED else "○"
            progress_info += f"{status_mark} [{task.status.value}] {task.description}"
            if task.status == TaskStatus.COMPLETED and task.message:
                progress_info += f" - Result: {task.message}"
            progress_info += "\n"

        # Add completed task results section
        completed_tasks_with_results = [task for task in all_tasks if task.status == TaskStatus.COMPLETED and task.message]
        if completed_tasks_with_results:
            progress_info += "\n## Completed Task Results\n"
            for task in completed_tasks_with_results:
                progress_info += f"### Task: {task.description}\n\n"
                progress_info += f"{task.message}\n\n"
                progress_info += "---\n"

        progress_info += """
Important Guidance:
- If the work for your task has already been partially or fully completed by other actors, build on top of the existing work instead of repeating it
- Check the artifacts created by previous tasks before starting your work
- Do not re-do what is already done
- You are already in the workspace directory. Use relative paths directly (e.g., README.md, src/main.py).
- Do NOT prepend /workspace to paths and do NOT add cd /workspace to shell commands - the working directory is already set correctly.
"""

        # Inject matched skills instructions if any
        skills_section = ""
        if self._matched_skills:
            skills_section += "\n\n## Activated Skills\n\n"
            for skill in self._matched_skills:
                skills_section += f"### {skill.metadata.name}\n"
                skills_section += f"**Description:** {skill.metadata.description}\n\n"
                # Fix relative resource paths to be absolute
                # This allows actors to correctly read references via tools
                skill_instructions = skill.instructions
                # Replace various forms of quoted relative paths
                skill_instructions = skill_instructions.replace(
                    '"references/',
                    f'"{os.path.join(skill.metadata.path, "references/")}'
                )
                skill_instructions = skill_instructions.replace(
                    "'references/",
                    f"'{os.path.join(skill.metadata.path, 'references/')}"
                )
                skill_instructions = skill_instructions.replace(
                    '`references/',
                    f'`{os.path.join(skill.metadata.path, "references/")}'
                )
                skill_instructions = skill_instructions.replace(
                    '"scripts/',
                    f'"{os.path.join(skill.metadata.path, "scripts/")}'
                )
                skill_instructions = skill_instructions.replace(
                    "'scripts/",
                    f"'{os.path.join(skill.metadata.path, 'scripts/')}"
                )
                skill_instructions = skill_instructions.replace(
                    '`scripts/',
                    f'`{os.path.join(skill.metadata.path, "scripts/")}'
                )
                skills_section += skill_instructions
                skills_section += "\n\n---\n"

        return (
            f"Role: {self.role}\n\n"
            f"Your Task: {self.task.description}\n"
            f"Completion Criteria: {self.task.completion_criteria}\n\n"
            f"{env_info}\n"
            f"{progress_info}\n"
            "Available Tools:\n"
            f"{tools_description}\n\n"
            "ReAct Instructions:\n"
            "You run in a loop of THOUGHT, ACTION, OBSERVATION.\n\n"
            "THOUGHT: Your reasoning about what to do next. Explain your thinking step by step.\n"
            "ACTION: The action to take, in JSON format with 'tool' and 'parameters'.\n"
            "  - To finish the task, use: {\"tool\": \"finish\", \"parameters\": {\"summary\": \"your summary here\"}}\n"
            "  - To use a tool, use: {\"tool\": \"tool_name\", \"parameters\": {\"key\": \"value\"}}\n\n"
            "Output Format:\n"
            "THOUGHT: <your reasoning>\n"
            "ACTION: <json action>\n\n"
            "Example:\n"
            "THOUGHT: I need to read the README file to understand the project structure.\n"
            "ACTION: {\"tool\": \"file_read\", \"parameters\": {\"file_path\": \"README.md\"}}\n"
            + skills_section
        )

    def _parse_response(self, response: str) -> Optional[Tuple[str, Optional[str], dict]]:
        """
        Parse LLM response to extract thought, tool name, and parameters.

        Expected format:
        THOUGHT: <reasoning>
        ACTION: {"tool": "name", "parameters": {...}}

        Returns:
            Tuple (thought, tool_name, parameters), or None if parsing fails
        """
        # Extract thought
        thought_match = re.search(r'THOUGHT:\s*(.*?)(?=\nACTION:|\Z)', response, re.DOTALL | re.IGNORECASE)
        if not thought_match:
            # If no explicit THOUGHT:, take everything before ACTION as thought
            thought_match = re.search(r'(.*?)(?=\nACTION:|\Z)', response, re.DOTALL | re.IGNORECASE)
            if not thought_match:
                return None
        thought = thought_match.group(1).strip()

        # Extract action JSON
        action_match = re.search(r'ACTION:\s*(\{.*\})', response, re.DOTALL | re.IGNORECASE)
        if not action_match:
            # Try to find JSON without ACTION: prefix
            action_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if not action_match:
                return thought, None, {}

        try:
            action_json = action_match.group(1)
            parsed = json.loads(action_json)
            tool_name = parsed.get("tool")
            parameters = parsed.get("parameters", {})
            return thought, tool_name, parameters
        except json.JSONDecodeError:
            return thought, None, {}

    def __repr__(self) -> str:
        """Return string representation."""
        return f"DynamicActor(actor_id={self.actor_id}, task_id={self.task.id})"
