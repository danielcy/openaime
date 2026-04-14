# Improve Actor Reuse Design

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve actor reuse rate by adding actor name field and optimizing LLM selection prompt to encourage reuse.

**Problem:** Current actor reuse rate is low - LLM almost always decides to create a new actor even when an existing actor is suitable. This is because:
1. Selection prompt has high matching requirement ("must exactly match")
2. No short friendly name for quick identification, only long role and description
3. LLM is inherently biased towards creating new instead of reusing existing

## Solution Architecture

Incremental improvement: add `name` field to ActorRecord, optimize selection prompt to encourage reuse, add name display in TUI.

### Changes:

#### 1. ActorRecord Add name field (`aime/base/types.py`)
- Add `name: str = ""` (empty string default) to `ActorRecord` dataclass
  - Default empty string needed because other fields have defaults (created_at, last_used_at)
- Name is a short ~2-6 word description (e.g., "Python Developer", "fiction Writer", "DevOps Engineer")
- Flexible: LLM can naturally generate the right length, no strict word count enforced
- Makes it easier for LLM to quickly identify what the actor does

#### 2. DynamicActor Add name field (`aime/components/actor.py`)
- Add `name: str` parameter to `DynamicActor.__init__`
- Store name as instance attribute
- Needed so ACTOR_STARTED event can include the name

#### 3. ActorFactory Generate name when creating actor (`aime/components/actor_factory.py`)
- After generating `role` with LLM, generate a short name using the same LLM
- Prompt:
```
Given the role description and selected tool bundles below, generate a short 2-6 word name for this actor that clearly describes its specialization.
Output ONLY the name, no extra text, explanation, or punctuation.

Role: {role}
Tool Bundles: {', '.join(selected_bundle_names)}
```
- Use the same temperature as role generation (0.3)
- Truncate generated name to max 30 characters (just to keep it compact for display)
- Store the generated name in ActorRecord

#### 4. Update _select_actor_for_task prompt (`aime/components/actor_factory.py`)
- New format for displaying existing actors:
```
existing_actors = "\n".join([
    f"- Actor Name: {record.name}\n  Actor ID: {record.actor_id}\n  Role: {record.role}\n  Description: {record.description}\n  Tool Bundles: {', '.join(record.tool_bundles)}\n  Last used: {record.last_used_at.strftime('%Y-%m-%d %H:%M')}"
    for _, record in self._actors.values()
])
```
- Modified instructions to encourage reuse with clearer guidance:
```
# Instructions
Analyze the new task requirements and compare them against the capabilities of each existing actor.
- **Prioritize reusing existing actors when capabilities are ROUGHLY matching** — you do NOT need an exact match.
- **Reuse is more efficient than creating new actors** — only create new when no existing actor is even close.
- If one existing actor is clearly suitable, output ONLY its actor_id in JSON format.
- If no existing actor is suitable (need to create new), output null.
```
- "Roughly matching" example:
  - If existing actor is "Python Developer" and new task is modifying Python code → REUSE
  - If existing actor is "fiction Writer" and new task is writing a blog post → REUSE
  - Only create new when the capability is completely different

#### 5. Backward Compatibility for Loaded Registry (`load_actor_registry` method)
- When loading existing actor records from persistence that don't have the `name` field:
  - Set fallback name: `name = role`
  - If `len(role) > 50`: truncate to 50 chars and add `...`
  - Implemented in `load_actor_registry()` when adding loaded records to `self._actors`

#### 6. Session Persistence
- No changes needed — `ActorRecord` dataclass automatically handles the new field during serialization/deserialization because it has a default value

#### 7. TUI Updates
- **Event emission (`actor.py` ACTOR_STARTED event):** Add `name` to the event payload alongside `actor_id`, `role`, `task_id`
- **EventStream formatting (`event_stream.py` _format_actor_started):** Format the event to display both name and role: `[name] - role`
- **ActorPane (`actor_pane.py` _build_actor_label):** Show actor `name` in the actor list (more compact). If name is empty (backward compatibility), fall back to role.

### Benefits:
- Incremental change - no architecture changes
- Keeps full flexibility of LLM decision making
- Easier for LLM to identify matching actors with short name
- Clearer instructions and encouragement in prompt increases probability of reuse
- Better UX in TUI with names displayed
- Automatic backward compatibility for existing persisted sessions

### Backward Compatibility:
- All existing code works unchanged
- New field `name` has default empty string → no TypeError when deserializing old ActorRecord
- Loading old registry without name gets automatic fallback from role
- No breaking changes

