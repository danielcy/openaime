"""
Planner Component - Dynamic planning for AIME framework.

According to the AIME paper, the Planner is a dynamic planner that:
- Takes the overall goal and current progress
- Uses LLM to decide what to do next
- Can dispatch subtasks
- Can replan when failures occur
- Works with the progress module to track what's done
"""
import re
import asyncio
import logging
import json
from typing import Optional, List, Dict, Any, Callable
from aime.base.types import PlannerOutput, Task, TaskStatus, ChatMessage
from aime.base.llm import BaseLLM, Message
from aime.base.config import PlannerConfig
from aime.base.events import EventType
from aime.components.progress_module import ProgressModule

logger = logging.getLogger(__name__)


class Planner:
    """
    Dynamic planner component that uses LLM to decide what to do next based on
    the current goal and progress.

    Attributes:
        base_llm: The LLM to use for planning
        config: Configuration for the planner
        goal: The root goal to achieve
    """

    def __init__(
        self,
        base_llm: BaseLLM,
        config: PlannerConfig,
        emit_event: None | Callable[[EventType, dict[str, Any]], None] = None,
    ):
        """
        Initialize the Planner component.

        Args:
            base_llm: The LLM to use for planning
            config: Configuration from aime.base.config
            emit_event: Optional callback to emit events (used for real-time streaming).
        """
        self.base_llm = base_llm
        self.config = config
        self.emit_event = emit_event
        self.goal: Optional[str] = None
        self._lock = asyncio.Lock()
        self._chat_history: list[ChatMessage] = []

    async def initialize(self, goal: str, progress: ProgressModule) -> None:
        """
        Initialize the planner with the root goal.
        If already initialized, appends goal to chat history and keeps existing tasks.

        Args:
            goal: The overall goal to achieve
            progress: ProgressModule instance to track task progress
        """
        is_initializing = self.goal is None

        async with self._lock:
            if is_initializing:
                self.goal = goal

        # Add goal to chat history
        self.add_user_message(goal)

        if is_initializing:
            logger.info("Planner initializing with initial task decomposition")
            # Use LLM to do initial task decomposition
            initial_prompt = self._build_initial_decomposition_prompt(goal)
            messages = [
                Message(
                    role="system",
                    content=initial_prompt
                )
            ]
            logger.debug(f"Sending initial decomposition prompt, length: {len(initial_prompt)}")
            response = await self.base_llm.complete(messages, temperature=self.config.temperature)
            response_content = response.content or ""
            logger.debug(f"LLM initial decomposition response:\n{response_content}")

            # Parse subtasks from response
            subtasks = self._parse_initial_decomposition(response_content, goal)
            logger.info(f"Initial decomposition created {len(subtasks)} subtasks")

            # Add subtasks to progress
            for subtask in subtasks:
                description = subtask.get("description", "")
                completion_criteria = subtask.get("completion_criteria", description)
                logger.debug(f"Adding initial subtask: {description}")
                await progress.add_task(
                    description=description,
                    completion_criteria=completion_criteria,
                    parent_id=None,
                )
        else:
            logger.info("Planner already initialized, appending goal to chat history")

    async def plan_step(self, progress: ProgressModule) -> PlannerOutput:
        """
        Plan the next step based on current progress.

        Args:
            progress: Current progress module with task status information

        Returns:
            PlannerOutput indicating the next action (dispatch_subtask, complete_goal, wait, or mutation)
        """
        logger.debug("Starting planning step")
        async with self._lock:
            if self.goal is None:
                raise RuntimeError("Planner not initialized. Call initialize() first.")
            current_goal = self.goal

        # Get all tasks with their status
        tasks = await progress.get_all_tasks()
        logger.debug(f"Planning based on {len(tasks)} tasks")
        tasks_status = "\n".join([
            f"- {task.id}: {task.description} ({task.status.value})"
            for task in tasks
        ])

        # System prompt template
        prompt = self._build_system_prompt(current_goal, tasks_status)

        # Get LLM response
        messages = [
            Message(
                role="system",
                content=prompt
            )
        ]
        logger.debug(f"Sending planning prompt to LLM, prompt length: {len(prompt)} chars")

        response = await self.base_llm.complete(messages, temperature=self.config.temperature)

        # Parse the response to get action
        response_content = response.content or ""
        logger.debug(f"LLM raw response:\n{response_content}")

        # Parse all actions from the response (could have multiple mutations)
        parsed_actions = self._parse_response(response_content)
        if not parsed_actions:
            logger.warning("No valid action parsed, defaulting to wait")
            return PlannerOutput(action=PlannerOutput.Action.WAIT)

        # Emit planner thought
        if self.emit_event is not None:
            self.emit_event(EventType.PLANNER_STEP_STARTED, {
                "iteration": None,
            })
            self.emit_event(EventType.PLANNER_THOUGHT, {
                "raw_output": response_content,
            })

        # Process all mutation actions first
        dispatch_action: Optional[PlannerOutput] = None
        final_action: Optional[PlannerOutput] = None

        for plan_output in parsed_actions:
            logger.info(f"Planner action: {plan_output.action.value}")

            # Handle mutation actions immediately
            if plan_output.action == PlannerOutput.Action.ADD_SUBTASK:
                if plan_output.description:
                    logger.info(f"Adding subtask: {plan_output.description}")
                    task = await progress.add_task(
                        description=plan_output.description,
                        completion_criteria=plan_output.completion_criteria or plan_output.description,
                        parent_id=None,
                    )
                    plan_output.task_id = task.id
                    plan_output.subtask_id = task.id
                    if self.emit_event is not None:
                        self.emit_event(EventType.PLANNER_TASK_ADDED, {
                            "task_id": task.id,
                            "description": task.description,
                            "completion_criteria": task.completion_criteria,
                        })

            elif plan_output.action == PlannerOutput.Action.MODIFY_SUBTASK:
                if plan_output.task_id:
                    logger.info(f"Modifying task {plan_output.task_id}")
                    await progress.modify_task(
                        task_id=plan_output.task_id,
                        description=plan_output.description,
                        completion_criteria=plan_output.completion_criteria,
                    )
                    if self.emit_event is not None:
                        self.emit_event(EventType.PLANNER_TASK_MODIFIED, {
                            "task_id": plan_output.task_id,
                            "description": plan_output.description,
                            "completion_criteria": plan_output.completion_criteria,
                        })

            elif plan_output.action == PlannerOutput.Action.DELETE_SUBTASK:
                if plan_output.task_id:
                    logger.info(f"Deleting task {plan_output.task_id}")
                    await progress.delete_task(task_id=plan_output.task_id)
                    if self.emit_event is not None:
                        self.emit_event(EventType.PLANNER_TASK_DELETED, {
                            "task_id": plan_output.task_id,
                        })

            elif plan_output.action == PlannerOutput.Action.MARK_FAILED:
                if plan_output.task_id:
                    logger.info(f"Marking task {plan_output.task_id} as failed: {plan_output.message}")
                    await progress.update_task_status(
                        task_id=plan_output.task_id,
                        status=TaskStatus.FAILED,
                        message=plan_output.message,
                    )
                    if self.emit_event is not None:
                        self.emit_event(EventType.PLANNER_TASK_MARKED_FAILED, {
                            "task_id": plan_output.task_id,
                            "reason": plan_output.message,
                        })

            elif plan_output.action == PlannerOutput.Action.DISPATCH_SUBTASK:
                # Save dispatch for after mutations are done
                dispatch_action = plan_output

            elif plan_output.action in [PlannerOutput.Action.COMPLETE_GOAL, PlannerOutput.Action.WAIT]:
                final_action = plan_output

        # If we have a dispatch action, process it now
        if dispatch_action:
            # If task_id specified in dispatch, try to use it
            if dispatch_action.task_id:
                task = await progress.get_task(dispatch_action.task_id)
                if task and task.status == TaskStatus.PENDING:
                    logger.info(f"Dispatching specified task: {task.id} - {task.description}")
                    if self.emit_event is not None:
                        self.emit_event(EventType.PLANNER_TASK_DISPATCHED, {
                            "task_id": task.id,
                        })
                    return PlannerOutput(
                        action=PlannerOutput.Action.DISPATCH_SUBTASK,
                        subtask_id=task.id,
                        summary=task.description,
                    )

            # Fall back to finding next dispatchable task
            next_task = await self._find_next_dispatchable_task(progress)
            if next_task:
                logger.info(f"Dispatching next task: {next_task.id} - {next_task.description}")
                if self.emit_event is not None:
                    self.emit_event(EventType.PLANNER_TASK_DISPATCHED, {
                        "task_id": next_task.id,
                    })
                return PlannerOutput(
                    action=PlannerOutput.Action.DISPATCH_SUBTASK,
                    subtask_id=next_task.id,
                    summary=next_task.description,
                )
            else:
                logger.debug("No dispatchable tasks found, waiting")
                return PlannerOutput(action=PlannerOutput.Action.WAIT)

        # If we have a final action (complete_goal or wait), use that
        if final_action:
            if final_action.action == PlannerOutput.Action.COMPLETE_GOAL:
                if self.emit_event is not None:
                    self.emit_event(EventType.PLANNER_GOAL_COMPLETED, {
                        "summary": final_action.summary or "Goal completed",
                    })
            return final_action

        # Default to wait
        return PlannerOutput(action=PlannerOutput.Action.WAIT)

    def _build_system_prompt(self, goal: str, tasks_status: str) -> str:
        """
        Build the system prompt for planning.

        Args:
            goal: The current overall goal
            tasks_status: Current tasks with their status

        Returns:
            Formatted system prompt
        """
        # Build history section
        history_section = ""
        if self._chat_history:
            history_section = "# 历史对话\n"
            for message in self._chat_history:
                history_section += f"**{message.role.upper()}:** {message.content}\n"
            history_section += "\n"

        return (
            "# Role\n"
            "You are an expert dynamic planner for the AIME autonomous agent framework. "
            "Your job is to continuously monitor the progress of the overall goal and decide what to do next.\n\n" +
            history_section +
            "# Current Goal\n"
            f"{goal}\n\n"
            "# Current Progress\n"
            f"{tasks_status or 'No tasks have been created yet'}\n\n"
            "# Decision Rules\n"
            "Analyze the current situation carefully and choose ONE or MORE of the following seven actions. "
            "Mutation actions (add, modify, delete, mark_failed) can be combined together, "
            "optionally followed by one terminal action (dispatch, complete, or wait).\n\n"
            "## 1. add_subtask\n"
            "Choose this action when:\n"
            "- You need to create a new subtask to work toward the goal\n"
            "- An existing task has failed and you need to create a new subtask to fix it\n"
            "- There are still tasks that need to be done that haven't been created yet\n"
            "\n"
            "When you choose this action, you MUST provide the subtask description and completion criteria in JSON format after the action.\n\n"
            "## 2. modify_subtask\n"
            "Choose this action when:\n"
            "- You need to change the description or completion criteria of an existing task\n"
            "- The task's purpose has evolved based on new information\n"
            "\n"
            "When you choose this action, you MUST provide the task ID and new information in JSON format after the action.\n\n"
            "## 3. delete_subtask\n"
            "Choose this action when:\n"
            "- A task is no longer needed to achieve the overall goal\n"
            "- The task's purpose has been invalidated by new information\n"
            "\n"
            "When you choose this action, you MUST provide the task ID in JSON format after the action.\n\n"
            "## 4. mark_failed\n"
            "Choose this action when:\n"
            "- A task has failed and cannot be completed successfully\n"
            "- You need to explicitly record the failure and move on\n"
            "\n"
            "When you choose this action, you MUST provide the task ID and failure message in JSON format after the action.\n\n"
            "## 5. dispatch_subtask\n"
            "Choose this action when:\n"
            "- There is an existing pending subtask that is ready to be executed\n"
            "- All dependencies of the task have been completed\n"
            "\n"
            "When you choose this action, you MUST provide the task ID in JSON format after the action.\n\n"
            "## 6. complete_goal\n"
            "Choose this action when:\n"
            "- All required subtasks have been completed\n"
            "- The overall goal has been fully achieved\n"
            "- No more work needs to be done\n\n"
            "## 7. wait\n"
            "Choose this action when:\n"
            "- There are already tasks that have been dispatched and are currently in progress\n"
            "- You need to wait for those tasks to finish before making your next decision\n"
            "- No new tasks need to be created right now\n\n"
            "# Important Guidelines\n"
            "- **Decompose wisely**: Break the work into logical subtasks. Each subtask should do one thing only.\n"
            "- **Handle failures**: If a task fails, you can mark it as failed and revise the plan accordingly.\n"
            "- **Check dependencies**: Make sure tasks are done in the correct order.\n"
            "- **Be patient**: Don't rush to complete the goal. Wait for ongoing tasks to finish.\n"
            "- **Revise plans dynamically**: Don't hesitate to modify or delete tasks based on new information.\n"
            "- **Combine actions**: You can specify multiple mutation actions (add/modify/delete/mark_failed) in sequence, "
            "followed by at most one terminal action (dispatch/complete/wait).\n\n"
            "# Output Format\n"
            "- For add_subtask: `add_subtask {\"description\": \"...\", \"completion_criteria\": \"...\"}`\n"
            "- For modify_subtask: `modify_subtask {\"task_id\": \"task-id\", \"description\": \"...\", \"completion_criteria\": \"...\"}`\n"
            "- For delete_subtask: `delete_subtask {\"task_id\": \"task-id\"}`\n"
            "- For mark_failed: `mark_failed {\"task_id\": \"task-id\", \"message\": \"reason for failure\"}`\n"
            "- For dispatch_subtask: `dispatch_subtask {\"task_id\": \"task-id\"}`\n"
            "- For complete_goal: `complete_goal`\n"
            "- For wait: `wait`\n"
            "\n"
            "Each action should be on its own line.\n\n"
            "# Examples\n"
            "add_subtask {\"description\": \"Read the README file to understand the project structure\", \"completion_criteria\": \"File content has been read and available as artifact\"}\n"
            "dispatch_subtask {\"task_id\": \"task-123\"}\n"
            "mark_failed {\"task_id\": \"task-456\", \"message\": \"API call failed due to network error\"}\n"
            "add_subtask {\"description\": \"Fix network configuration\", \"completion_criteria\": \"Network is accessible\"}\n"
            "delete_subtask {\"task_id\": \"task-789\"}\n"
            "modify_subtask {\"task_id\": \"task-abc\", \"description\": \"Updated description\", \"completion_criteria\": \"Updated criteria\"}"
        )

    def _parse_response(self, response: str) -> List[PlannerOutput]:
        """
        Parse LLM response to extract all actions and their parameters.

        Args:
            response: Raw LLM response

        Returns:
            List of PlannerOutput with parsed actions
        """
        response = response.strip()
        results: List[PlannerOutput] = []

        # Split response into lines and process each line
        lines = response.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match action patterns
            match = re.search(r'\b(add_subtask|modify_subtask|delete_subtask|mark_failed|dispatch_subtask|complete_goal|wait)\b', line.lower())
            if not match:
                continue

            action = match.group(1)

            try:
                if action == "add_subtask":
                    json_match = re.search(r'\{[^}]*\}', line)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        description = parsed.get("description", "")
                        completion_criteria = parsed.get("completion_criteria", description)
                        results.append(PlannerOutput(
                            action=PlannerOutput.Action.ADD_SUBTASK,
                            description=description,
                            completion_criteria=completion_criteria,
                        ))

                elif action == "modify_subtask":
                    json_match = re.search(r'\{[^}]*\}', line)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        task_id = parsed.get("task_id")
                        description = parsed.get("description")
                        completion_criteria = parsed.get("completion_criteria")
                        if task_id:
                            results.append(PlannerOutput(
                                action=PlannerOutput.Action.MODIFY_SUBTASK,
                                task_id=task_id,
                                description=description,
                                completion_criteria=completion_criteria,
                            ))

                elif action == "delete_subtask":
                    json_match = re.search(r'\{[^}]*\}', line)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        task_id = parsed.get("task_id")
                        if task_id:
                            results.append(PlannerOutput(
                                action=PlannerOutput.Action.DELETE_SUBTASK,
                                task_id=task_id,
                            ))

                elif action == "mark_failed":
                    json_match = re.search(r'\{[^}]*\}', line)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        task_id = parsed.get("task_id")
                        message = parsed.get("message", "Task failed")
                        if task_id:
                            results.append(PlannerOutput(
                                action=PlannerOutput.Action.MARK_FAILED,
                                task_id=task_id,
                                message=message,
                            ))

                elif action == "dispatch_subtask":
                    json_match = re.search(r'\{[^}]*\}', line)
                    task_id = None
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            task_id = parsed.get("task_id")
                        except Exception:
                            pass
                    results.append(PlannerOutput(
                        action=PlannerOutput.Action.DISPATCH_SUBTASK,
                        task_id=task_id,
                    ))

                elif action == "complete_goal":
                    results.append(PlannerOutput(action=PlannerOutput.Action.COMPLETE_GOAL))

                elif action == "wait":
                    results.append(PlannerOutput(action=PlannerOutput.Action.WAIT))

            except Exception as e:
                logger.warning(f"Failed to parse action line '{line}': {e}")
                continue

        return results

    def _build_initial_decomposition_prompt(self, goal: str) -> str:
        """
        Build the prompt for initial task decomposition.

        Args:
            goal: The overall user goal

        Returns:
            Formatted prompt string
        """
        return (
            "You are the dynamic planner for the AIME framework. "
            "Decompose the overall goal into a list of subtasks that can be executed "
            "in order to achieve the goal.\n\n"
            f"Overall Goal: {goal}\n\n"
            "Instructions:\n"
            "1. **Decompose ONLY when necessary**: If the goal is simple and self-contained (e.g., 'write a quicksort algorithm', 'add a login button'), keep it as a SINGLE subtask. DO NOT decompose into multiple unnecessary subtasks.\n"
            "2. Only break into multiple subtasks when the goal is complex and requires distinct steps that can be worked on independently\n"
            "3. For each subtask, provide a clear description and completion criteria\n"
            "4. Output the list as JSON array\n"
            "5. Each subtask must have 'description' and 'completion_criteria' fields\n\n"
            "Output format:\n"
            "```json\n"
            "[\n"
            "  {\"description\": \"First subtask description\", \"completion_criteria\": \"How to tell it's done\"}\n"
            "]\n"
            "```\n"
        )

    def _parse_initial_decomposition(self, response: str, goal: str) -> list[dict]:
        """
        Parse the initial decomposition response from LLM.

        Args:
            response: LLM response
            goal: Original goal (fallback if parsing fails)

        Returns:
            List of subtask dicts with description and completion_criteria
        """
        try:
            # Find JSON block in response
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', response, re.DOTALL)
            if not json_match:
                json_match = re.search(r'(\[\s*\{.*\}\s*\])', response, re.DOTALL)

            if json_match:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, list) and len(parsed) > 0:
                    # Validate each subtask
                    valid_subtasks = []
                    for item in parsed:
                        if isinstance(item, dict) and 'description' in item:
                            if 'completion_criteria' not in item:
                                item['completion_criteria'] = item['description']
                            valid_subtasks.append(item)
                    if valid_subtasks:
                        return valid_subtasks

        except Exception as e:
            logger.warning(f"Failed to parse initial decomposition: {e}")

        # Fallback: just one task with the whole goal
        logger.info("Falling back to single task decomposition")
        return [{
            'description': f"Achieve goal: {goal}",
            'completion_criteria': "The overall goal is fully completed",
        }]

    async def _find_next_dispatchable_task(self, progress: ProgressModule) -> Optional[Task]:
        """
        Find the next task that is ready for execution:
        - Status is PENDING
        - All dependencies are completed

        Args:
            progress: Progress module with all tasks

        Returns:
            The next task to dispatch, or None if none ready
        """
        pending_tasks = await progress.get_pending_tasks()
        # get_pending_tasks already filters dependencies
        # just pick the first one
        if pending_tasks:
            # Return the first pending task
            return pending_tasks[0]
        return None

    def add_user_message(self, content: str) -> None:
        """
        Add a user message to the chat history.

        Args:
            content: The content of the user message
        """
        self._chat_history.append(ChatMessage(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """
        Add an assistant message to the chat history.

        Args:
            content: The content of the assistant message
        """
        self._chat_history.append(ChatMessage(role="assistant", content=content))
