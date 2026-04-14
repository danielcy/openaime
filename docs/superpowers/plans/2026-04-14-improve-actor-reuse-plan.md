# Improve Actor Reuse Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve actor reuse rate by adding actor name field and optimizing LLM selection prompt to encourage reuse, with better TUI display.

**Architecture:** Incremental improvement: add `name` field to ActorRecord/DynamicActor, generate short name when creating actor, improve selection prompt to encourage reuse, update TUI to display name. All backward compatible with existing persisted actors via automatic fallback.

**Tech Stack:** Python, dataclasses, existing LLM abstraction, TUI with Textual.

---

## Files to Modify:
- Modify: `aime/base/types.py` - add name field to ActorRecord
- Modify: `aime/components/actor.py` - add name field to DynamicActor, add name to ACTOR_STARTED event
- Modify: `aime/components/actor_factory.py` - add name generation on create, update existing actors selection prompt, add fallback for loaded registry
- Modify: `aime_tui/components/actor_pane.py` - update actor list display to use name
- Modify: `aime_tui/components/event_stream.py` - update actor started event formatting to show name + role
- Test: `tests/components/test_actor_factory.py` - run existing tests to verify no regressions

---

### Task 1: Add name field to ActorRecord dataclass

**Files:**
- Modify: `aime/base/types.py`

- [ ] **Step 1: Add name field to ActorRecord**

```python
@dataclass
class ActorRecord:
    """Metadata record for a created actor that can be reused."""
    actor_id: str
    name: str = ""  # Short human-readable name (e.g. "Python Developer"), empty string for backward compatibility
    role: str  # actor name/role description (ρ_t from paper)
    description: str  # description of what this actor is good for
    tool_bundles: List[str]  # list of tool bundle names this actor has
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
```

- [ ] **Step 2: Run tests to verify compilation**

```bash
python -m pytest tests/base/test_types.py -v
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add aime/base/types.py
git commit -m "feat: add name field to ActorRecord with default empty string"
```

---

### Task 2: Add name field to DynamicActor

**Files:**
- Modify: `aime/components/actor.py`

- [ ] **Step 1: Add name parameter to __init__ and store as instance attribute**

Find `def __init__(` in `class DynamicActor:`, add:

```python
def __init__(
    self,
    ...
    name: str,
    ...
):
    ...
    self.name = name
    ...
```

Update all callsites where DynamicActor is instantiated (in ActorFactory) to pass the name parameter.

- [ ] **Step 2: Update ACTOR_STARTED event emission to include name**

Find where ACTOR_STARTED (actor_started) event is emitted, add `"name": self.name` to the event data.

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/components/test_actor.py -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add aime/components/actor.py
git commit -m "feat: add name field to DynamicActor and include in ACTOR_STARTED event"
```

---

### Task 3: Update ActorFactory - generate name and improve selection prompt

**Files:**
- Modify: `aime/components/actor_factory.py`

- [ ] **Step 1: Add name generation after role generation**

After line ~354 where role is generated:

```python
# Generate short name for the actor
from aime.base.llm import Message
name_prompt = f"""Given the role description and selected tool bundles below, generate a short 2-6 word name for this actor that clearly describes its specialization.
Output ONLY the name, no extra text, explanation, or punctuation.

Role: {role}
Tool Bundles: {', '.join(selected_bundle_names)}
"""
name_messages = [Message(role="user", content=name_prompt)]
name_response = await self.base_llm.complete(name_messages, temperature=0.3)
name = name_response.content.strip()
name = name.strip('"\'')
# Truncate to keep it compact
if len(name) > 30:
    name = name[:27] + "..."
```

Store name in ActorRecord when creating:

```python
record = ActorRecord(
    actor_id=actor_id,
    name=name,
    role=role,
    description=description,
    tool_bundles=selected_bundle_names,
)
```

- [ ] **Step 2: Update _select_actor_for_task existing actors display**

Update existing format to:

```python
existing_actors = "\n".join([
    f"- Actor Name: {record.name}\n  Actor ID: {record.actor_id}\n  Role: {record.role}\n  Description: {record.description}\n  Tool Bundles: {', '.join(record.tool_bundles)}\n  Last used: {record.last_used_at.strftime('%Y-%m-%d %H:%M')}"
    for _, record in self._actors.values()
])
```

- [ ] **Step 3: Update selection instructions to encourage reuse**

Update instructions in prompt to:

```
# Instructions
Analyze the new task requirements and compare them against the capabilities of each existing actor.
- **Prioritize reusing existing actors when capabilities are ROUGHLY matching** — you do NOT need an exact match.
- **Reuse is more efficient than creating new actors** — only create new when no existing actor is even close.
- If one existing actor is clearly suitable, output ONLY its actor_id in JSON format.
- If no existing actor is suitable (need to create new), output null.

"Roughly matching" examples:
- If existing actor is "Python Developer" and new task is modifying Python code → REUSE
- If existing actor is "fiction Writer" and new task is writing a blog post → REUSE
- Only create new when the capability is completely different

# Output Format
{{"actor_id": "actor-id-or-null"}}
```

- [ ] **Step 4: Add backward compatibility fallback in load_actor_registry**

In `load_actor_registry` method, when loading each record:

```python
# Backward compatibility: if record has no name, generate fallback from role
if not record.name:
    if len(record.role) > 50:
        record.name = record.role[:50] + "..."
    else:
        record.name = record.role
self._actors[record.actor_id] = (None, record)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/components/test_actor_factory.py -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add aime/components/actor_factory.py
git commit -m "feat: add actor name generation on creation, improve selection prompt to encourage reuse"
```

---

### Task 4: Update TUI ActorPane to display name

**Files:**
- Modify: `aime_tui/components/actor_pane.py`

- [ ] **Step 1: Update _build_actor_label to display name**

Change the label building to use name if available, fallback to role:

```python
def _build_actor_label(self, actor_id: str, actor_name: str, actor_role: str) -> Text:
    """Build the label for an actor in the list."""
    display_name = actor_name if actor_name else actor_role
    return Text(display_name)
```

Update the calling code when adding actors to pass the name.

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/aime_tui/components/test_actor_pane.py -v
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add aime_tui/components/actor_pane.py
git commit -m "feat(tui): display actor name in actor pane, fallback to role if empty"
```

---

### Task 5: Update TUI EventStream to display name on actor started

**Files:**
- Modify: `aime_tui/components/event_stream.py` - update `_format_actor_started` method

- [ ] **Step 1: Update _format_actor_started to display both name and role**

Update method:

```python
def _format_actor_started(self, event: AimeEvent) -> Text:
    name = event.data.get("name")
    role = event.data.get("role", "")
    if name and name != role:
        content = f"🚀 {name} - {role}"
    else:
        content = f"🚀 {role}"
    return Text(content, style="bold green")
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/aime_tui/components/test_event_stream.py -v
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add aime_tui/components/event_stream.py
git commit -m "feat(tui): display both name and role in actor started event"
```

---

### Task 6: Full test suite verification

**Files:** None (verify all tests pass

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: All existing tests pass (no regressions)

- [ ] **Step 2: Commit if fixes needed, else done**
