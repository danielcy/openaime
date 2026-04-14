# Switch to Pure Native Function Calling Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch AIME Actor from mixed ReAct text parsing + native function calling to pure native function calling, eliminating JSON parsing errors from truncated long output.

**Architecture:** Fully leverage LLM provider's native tool calling capability. Remove all text parsing logic (regex matching, JSON cleaning heuristics. Simplify system prompt by removing tool descriptions and format instructions. This significantly improves reliability for long tool parameters like writing large files.

**Tech Stack:** Python, asyncio, existing LLM provider abstractions already support native function calling.

---

## File Changes Summary:
- Modify: `aime/components/actor.py` - main changes
  - Update `_build_system_prompt()` - remove tool descriptions, update instructions
  - Update `_react_loop()` - remove text parsing fallback, add empty tool_calls retry
  - Remove `_parse_response()` method
  - Remove `_clean_llm_json()` method
  - Remove duplicate finish tool check

Test: `tests/components/test_actor.py`

---

### Task 1: Update System Prompt - Remove Tool Descriptions and ReAct Instructions

**Files:**
- Modify: `aime/components/actor.py` around line 558-628

- [ ] **Step 1: Remove the tools_description section and ReAct Instructions from _build_system_prompt**

Original code after progress_info has:
```python
progress_info += """
Important Guidance:
...
"""

# Remove the following section that needs to be deleted:
            "Available Tools:\n"
            f"{tools_description}\n\n"
            "ReAct Instructions:\n"
            "You run in a loop of THOUGHT, ACTION, OBSERVATION.\n\n"
            "THOUGHT: Your reasoning about what to do next. Explain your thinking step by step.\n"
            "ACTION: The action to take, in JSON format with 'tool' and 'parameters'.\n"
            "  - To finish the task, use: {"tool": "finish", "parameters": {"summary": "your summary here"}}\n"
            "  - To use a tool, use: {"tool": "tool_name", "parameters": {"key": "value"}}\n\n"
            "Output Format:\n"
            "THOUGHT: <your reasoning>\n"
            "ACTION: <json action>\n\n"
            "Example:\n"
            "THOUGHT: I need to read the README file to understand the project structure.\n"
            "ACTION: {"tool": "file_read", "parameters": {"file_path": "README.md"}}\n"
            + skills_section
```

Replace with just:

```python
progress_info += """
Important Guidance:
- If the work for your task has already been partially or fully completed by other actors, build on top of the existing work instead of repeating it
- Check the artifacts created by previous tasks before starting your work
- Do not re-do what is already done
- **If the file you need to write/modify does NOT exist yet, that means you NEED to CREATE it. Do not keep checking for it - go ahead and create it immediately.**
- Do NOT repeatedly check the same files over and over. If you've already checked a file once, you don't need to check it again - move on to the next step.
- You are already in the workspace directory. Use relative paths directly (e.g., README.md, src/main.py).
- Do NOT prepend /workspace to paths and do NOT add cd /workspace to shell commands - the working directory is already set correctly.

Instructions:
You work in an iterative loop:
1. Explain your reasoning about what to do next in the response content
2. Call the appropriate tool using the native tool calling interface
3. You will receive the tool execution result back as an observation
4. Repeat until you have completed the task

When you finish, call the `finish` tool with a comprehensive summary that includes:
- Actual results achieved
- Content created or modified
- Key findings and conclusions
- Any important details for downstream tasks
"""

+ skills_section
```

Then continue with return statement:
```python
        return (
            f"Role: {self.role}\n\n"
            f"Your Task: {self.task.description}\n"
            f"Completion Criteria: {self.task.completion_criteria}\n\n"
            f"{env_info}\n"
            f"{progress_info}\n\n"
            + skills_section
        )
```

- [ ] **Step 2: Run tests to verify compilation**

```bash
python -m pytest tests/components/test_actor.py -v
```

Expected: All tests still pass (changes are just content changes to the prompt, no behavior change to existing behavior

- [ ] **Step 3: Commit**

```bash
git add aime/components/actor.py
git commit -m "refactor: update system prompt for pure native function calling - remove tool descriptions and ReAct format instructions"
```

---

### Task 2: Update ReAct Loop - Remove Text Parsing Fallback and Add Retry

**Files:**
- Modify: `aime/components/actor.py` around line 279-347

- [ ] **Step 1: Update _react_loop - remove text parsing**

Original code:
```python
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
                # Add thought to global chat history if enabled
                if self.store_full_actor_history and thought:
                    from aime.base.types import ChatMessage
                    self.planner._chat_history.append(ChatMessage(
                        role="assistant",
                        content=f"THOUGHT: {thought}",
                        message_type="thought"
                    ))
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
                        content="Invalid response format. Please use the format: THOUGHT: <your reasoning> ACTION: {"tool": "tool_name", "parameters": {...}}"
                    ))
                    iteration += 1
                    continue

                parsed_thought, parsed_tool_name, parsed_parameters = parsed
                if thought is None:
                    thought = parsed_thought
                tool_name = parsed_tool_name
                parameters = parsed_parameters
                logger.debug(f"Actor {self.actor_id} text parsed selected tool: {tool_name}")
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
                # No content and no tool calls - invalid
                self._history.append(Message(
                    role="system",
                    content="Empty response from model, please try again with a valid response containing either thought/action or tool call."
                ))
                iteration += 1
                continue
```

Replace with:

```python
            # Use native tool calling - we expect tool_calls must be present
            thought: Optional[str] = response.content
            tool_name: Optional[str] = None
            parameters: dict[str, Any] = {}

            if not response.tool_calls:
                # No tool calls - this is invalid, ask to retry
                empty_retries += 1
                if empty_retries >= 3:
                    # Max retries exceeded - fail
                    observation = "Error: 3 consecutive responses with no tool calls. Giving up."
                    logger.error(f"Actor {self.actor_id} {observation}")
                    self._history.append(Message(
                        role="system",
                        content=observation
                    ))
                    return ActorResult(
                        task_id=self.task.id,
                        status=TaskStatus.FAILED,
                        summary=observation,
                        artifacts=self.task.artifacts,
                    )
                self._history.append(Message(
                    role="system",
                    content="Error: Your response did not contain any tool call. Please use the native tool calling interface to call a tool."
                ))
                iteration += 1
                continue

            # Reset empty retries when we get a valid tool call
            empty_retries = 0

            # Take first tool call (we do one step at a time)
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
```

- [ ] **Step 2: Add empty_retries initialization at start of loop**

At line 263-262 before loop:
```python
        # Track recent tool calls for repetition detection
        recent_tools: list[str] = []
        max_recent = 6  # Track last 6 tool calls
        # Track consecutive empty tool calls for retry
        empty_retries = 0
```

- [ ] **Step 3: Remove duplicate finish check**

Original has duplicate check after first check at lines ~350 and ~374. Remove the second duplicate check:

Delete lines 374-385:
```python
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
```

Keep the first check at lines ~350-362 which is in the correct place.

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/components/test_actor.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add aime/components/actor.py
git commit -m "refactor: update react loop for pure native function calling - remove text parsing fallback, add empty retries, remove duplicate finish check"
```

---

### Task 3: Remove Dead Code (_parse_response and _clean_llm_json)

**Files:**
- Modify: `aime/components/actor.py` - remove the two methods

- [ ] **Step 1: Delete entire `_clean_llm_json` method**

Delete lines where the method is defined (currently ~633-666).

- [ ] **Step 2: Delete entire `_parse_response` method**

Delete the whole method (currently ~668-706).

- [ ] **Step 3: Check that no other code calls these methods**

- [ ] **Step 4: Run tests to verify everything still works**

```bash
python -m pytest tests/components/test_actor.py -v
python -m pytest tests/components/ -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add aime/components/actor.py
git commit -m "cleanup: remove dead code _parse_response and _clean_llm_json - no longer needed with pure native function calling"
```

---

### Task 4: Full Test Suite Verification

**Files:** None (no code change)

- [ ] **Step 1: Run full test suite to verify everything still passes**

```bash
python -m pytest tests/ -v
```

Expected: All 236 tests pass.

- [ ] **Step 2: If any test fails, fix them**

- [ ] **Step 3: Commit (if fixes needed, otherwise skip)**
