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
        store_full_actor_history: bool = False,
        name: str = "",
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
            store_full_actor_history: Whether to store full actor history in chat history
            name: Short human-readable name for this actor
        """
        self.actor_id = actor_id
        self.name = name
        self.role = role
        self.task = task
        self.llm = llm
        self.planner = planner
        self.progress = progress
        self.toolkit = toolkit
        self.knowledge = knowledge
        self.config = config
        self._emit_event = emit_event
        self.store_full_actor_history = store_full_actor_history

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
                "name": self.name,
                "role": self.role,
            })
            # Emit skill loaded event if any skills are loaded
            if self._matched_skills:
                skill_names = [skill.metadata.name for skill in self._matched_skills]
                self._emit_event(EventType.ACTOR_SKILL_LOADED, {
                    "actor_id": self.actor_id,
                    "task_id": self.task.id,
                    "skills": skill_names,
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

        Uses only native tool calling (most reliable).

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
                            "description": "**COMPREHENSIVE SUMMARY** of what you accomplished: include the actual results, key findings, content created, conclusions, and any important details. This summary will be used by subsequent tasks to build on your work - BE SPECIFIC."
                        }
                    },
                    "required": ["summary"]
                }
            }
        })

        iteration = 0
        max_iterations = self.config.max_iterations
        empty_retries = 0
        max_empty_retries = 3

        # Track recent tool calls for repetition detection
        recent_tools: list[str] = []
        max_recent = 6  # Track last 6 tool calls

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

            # Check for native tool calls
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
                # Add thought to global chat history if enabled
                if self.store_full_actor_history and thought:
                    from aime.base.types import ChatMessage
                    self.planner._chat_history.append(ChatMessage(
                        role="assistant",
                        content=f"THOUGHT: {thought}",
                        message_type="thought"
                    ))
            else:
                # No tool calls - increment empty retries
                empty_retries += 1
                logger.warning(f"Actor {self.actor_id} received empty tool calls (retry {empty_retries}/{max_empty_retries})")

                if empty_retries > max_empty_retries:
                    return ActorResult(
                        task_id=self.task.id,
                        status=TaskStatus.FAILED,
                        summary="Received too many empty tool calls without any action"
                    )

                self._history.append(Message(
                    role="system",
                    content="Your response didn't include any tool calls. Please try again and use the appropriate tool to continue working on the task."
                ))
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

            # Detect repetitive loops: if we see the same sequence repeating, add a warning observation
            recent_tools.append(tool_name)
            if len(recent_tools) > max_recent:
                recent_tools.pop(0)

            # Check if we're repeating the same sequence (contains the same set of tools repeated)
            loop_detected = False
            if len(recent_tools) == max_recent:
                # Check if first half equals second half = repeating pair
                half = max_recent // 2
                if recent_tools[:half] == recent_tools[half:]:
                    loop_detected = True

            # Detect the "file not found" loop pattern: multiple file_read calls that all failed
            if tool_name == "file_read" and recent_tools.count("file_read") >= 4:
                loop_detected = True

            if loop_detected:
                # Add a guiding observation to break the loop
                loop_guidance = """
IMPORTANT OBSERVATION: You appear to be stuck in a loop repeatedly checking the same files.
- If the file you need does NOT exist yet, you NEED to CREATE it with the file_write tool.
- Stop checking and GO CREATE the file.
"""
                logger.warning(f"Actor {self.actor_id} detected potential loop, adding guidance to break it")
                self._history.append(Message(
                    role="assistant",
                    content=response.content or ""
                ))
                self._history.append(Message(
                    role="system",
                    content=loop_guidance
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

            # Add action and observation to global chat history if enabled
            if self.store_full_actor_history and tool_name:
                from aime.base.types import ChatMessage
                action_content = f"ACTION: {tool_name} - {json.dumps(parameters)}"
                self.planner._chat_history.append(ChatMessage(
                    role="assistant",
                    content=action_content,
                    message_type="action"
                ))
                self.planner._chat_history.append(ChatMessage(
                    role="user",
                    content=f"OBSERVATION: {observation}",
                    message_type="observation"
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
        - Environment info
        - Simplified native function calling instructions
        - Activated skills

        Returns:
            Formatted system prompt string
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
- **If the file you need to write/modify does NOT exist yet, that means you NEED to CREATE it. Do not keep checking for it - go ahead and create it immediately.**
- Do NOT repeatedly check the same files over and over. If you've already checked a file once, you don't need to check it again - move on to the next step.
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
            "Instructions:\n"
            "You work in an iterative loop:\n"
            "1. Explain your reasoning about what to do next in the response content\n"
            "2. Call the appropriate tool using the native tool calling interface\n"
            "3. You will receive the tool execution result back as an observation\n"
            "4. Repeat until you have completed the task\n\n"
            "When you finish, call the `finish` tool with a comprehensive summary that includes:\n"
            "- Actual results achieved\n"
            "- Content created or modified\n"
            "- Key findings and conclusions\n"
            "- Any important details for downstream tasks\n"
            + skills_section
        )


    def __repr__(self) -> str:
        """Return string representation."""
        return f"DynamicActor(actor_id={self.actor_id}, task_id={self.task.id})"
