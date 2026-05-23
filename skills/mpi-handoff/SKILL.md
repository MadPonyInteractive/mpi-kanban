---
name: mpi-handoff
description: Create an MPI handoff. Preserve current MPI work and generate a structured JSON handoff document so a fresh session can resume with mpi-continue. Use when user says "create an MPI handoff", "handoff", "new session", "context is big", "$mpi-handoff", or "/mpi-kanban:mpi-handoff", or when a plan phase just completed and a new one starts.
---

# mpi-handoff Skill

Preserves current MPI work and produces a canonical handoff document at
`.agents/mpi-kanban/state/handoffs/<uuid>.json` that a fresh session can load
to resume with `mpi-continue` without re-explanation.

Shared coordination contract reference:

- `${CLAUDE_PLUGIN_ROOT}/docs/coordination/README.md`
- `${CLAUDE_PLUGIN_ROOT}/docs/coordination/handoff-migration.md`
- `${CLAUDE_PLUGIN_ROOT}/docs/coordination/schemas.md`
- `${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/lifecycle.md`
- `${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/statuses.md`

Invocation: Claude Code users may run `/mpi-kanban:mpi-handoff`; Codex users
may run `$mpi-handoff` or ask naturally to create an MPI handoff. References
using `${CLAUDE_PLUGIN_ROOT}` mean the installed plugin root; Codex resolves
the same files relative to this plugin root.

## When to invoke

- User says "handoff", "new session", "start fresh", "context is big", or runs
  `$mpi-handoff` in Codex or `/mpi-kanban:mpi-handoff` in Claude Code.
- Context usage is high and work is mid-flight.
- A plan phase just completed and a new phase starts next.

## Process

### Step 1 - Gather state from conversation

Extract all of the following from conversation context. **Do NOT run git
commands** because work is mid-flight and uncommitted state is irrelevant.

- What was the user originally trying to accomplish?
- What is complete vs. pending?
- What is the very next action the fresh session should take?
- Key decisions, constraints, or gotchas discovered during this session?
- Which plan file is active, if any?
- Which files were modified or created this session?

### Step 2 - Identify active coordination context

If a plan file exists in `docs/plans/`, read its current state:

- Note the plan file path.
- List completed `[x]` and pending `[ ]` to-dos.
- Identify the next `[ ]` item.

If `.agents/mpi-kanban/state/index.json` exists, read it next. Use it as a
small pointer facade to identify active sessions, tasks, file claims, or prior
handoffs relevant to this handoff.

Read `lib/coordination-ops/lifecycle.md`. If coordination state is active,
renew or identify the current session and task before writing the handoff.

### Step 3 - Look up the active kanban entry

Read `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/find.md` for `findKanban` and
`findEntry`. Then:

1. Call `findKanban()`. If the file does not exist, set `kanban_entry` to
   `null` and continue.
2. Otherwise call `findEntry(e => e.column === "IMPLEMENTING" && e.body matches "Plan file: <activePlan>")`.
3. If a match is found, `kanban_entry = entry.title`. Otherwise, `null`.

### Step 4 - Preservation pass

Before writing the handoff, capture knowledge while the current session still
has context:

- Update the active plan's `## Current State`, `## Plan Drift`, and
  `## Preservation Notes` if they are stale.
- Update active coordination records: mark outgoing session `handoff_ready`,
  mark unfinished file claims `complete`, `needs_integration`, or
  `needs_review` as appropriate, and keep pending-change provenance visible in
  `pending_file_states`.
- If known docs/rules/memory updates can be made accurately, do them now,
  respecting project approval rules for architectural rule files.
- If updates are blocked, need approval, or should wait for completion, record
  them as pending preservation items in the handoff.

Do not commit. Do not run cleanup.

### Step 5 - Write the handoff document

Create file at `.agents/mpi-kanban/state/handoffs/<uuid>.json` and create the
directory if missing. Generate `<uuid>` with `python scripts/new_uuid.py`. Use
the same value for the filename and the JSON `id`.

After writing the handoff, add it to `state/index.json` `active_handoffs` and
update `index.updated_at`.

Use this exact JSON structure:

```json
{
  "schema": "mpi-kanban/handoff/v1",
  "id": "<uuid>",
  "generated_at": "<ISO-8601 timestamp>",
  "from_session": "<state/sessions path, or null>",
  "to_role": "orchestrator | planner | implementer | reviewer | verifier | integrator | docs",
  "status": "open",
  "session": {
    "name": "<best description of the session>",
    "branch": "<current branch from conversation or plan file, NOT a git command>"
  },
  "goal": {
    "original": "<what the user set out to do, verbatim or close paraphrase>",
    "status": "in_progress | blocked | complete",
    "summary": "<1-3 sentence summary of where things stand>"
  },
  "plan": {
    "file": "<path to active plan file, or null>",
    "completed": ["<done item 1>", "<done item 2>"],
    "pending": ["<next item 1>", "<next item 2>"]
  },
  "kanban_entry": "<title of active IMPLEMENTING entry, or null>",
  "allowed_actions": [
    "<actions the next agent may take, e.g. read, continue, verify>"
  ],
  "knowledge_preservation": {
    "completed": [
      "<docs/rules/memory/plan preservation done before handoff>"
    ],
    "pending": [
      "<preservation item the next session or end-session must handle>"
    ]
  },
  "next_action": {
    "description": "<exact instruction for fresh session>",
    "command": "<optional skill or command to run first, e.g. $mpi-continue or /mpi-kanban:mpi-continue>"
  },
  "context": {
    "key_decisions": [
      "<decision 1 and why>",
      "<decision 2 and why>"
    ],
    "constraints": [
      "<constraint or gotcha 1>",
      "<constraint or gotcha 2>"
    ],
    "files_modified": ["<path1>", "<path2>"],
    "files_to_read_first": ["<path1>", "<path2>"]
  },
  "project_knowledge": {
    "profile": "<.agents/mpi-kanban/project-profile.md if present, else null>",
    "knowledge_index": "<.agents/mpi-kanban/project-knowledge-index.md if present, else null>",
    "mode": "<profile mode if present, else null>",
    "relevant_topics": ["<topic block names the fresh session should load first>"]
  },
  "rules_active": [
    "<rule file that must be read>",
    "<rule file 2>"
  ],
  "recent_events": [
    {
      "at": "<ISO-8601 timestamp>",
      "event": "handoff_created"
    }
  ],
  "resume_prompt": "<single paragraph the user can paste into a new session. Second person, present tense. Mentions the handoff file path AND the kanban entry title if not null.>"
}
```

If compatibility with older resume flows is useful, also create a small pointer
file under `docs/handoffs/YYYY-MM-DD-HH-MM-<slug>.json`:

```json
{
  "schema": "mpi-kanban/legacy-handoff-pointer/v1",
  "canonical_handoff": ".agents/mpi-kanban/state/handoffs/<uuid>.json"
}
```

The `.agents/` handoff is canonical. `docs/handoffs/` is legacy compatibility
during migration.

### Step 6 - Print the resume prompt

After writing the file, output to the user and do not dump the full JSON. The
copy/paste block is mandatory:

```text
Handoff saved: .agents/mpi-kanban/state/handoffs/<uuid>.json
Active kanban entry: "<title>"   (or "none" if kanban_entry is null)

To resume in a new session, paste this:
---
Read .agents/mpi-kanban/state/handoffs/<uuid>.json and use $mpi-continue in Codex or /mpi-kanban:mpi-continue in Claude Code to continue from where we left off.
The next action is: <next_action.description>
---
```

## Hard rules

- No git commands; work is mid-flight, and git state is not part of the handoff.
- `resume_prompt` MUST be self-contained. The fresh session has zero memory.
- The final chat output MUST include the copy/paste resume block every time.
- New canonical handoffs MUST be written under `.agents/mpi-kanban/state/handoffs/`.
- `docs/handoffs/` is legacy compatibility, not canonical state.
- `kanban_entry` is required in the JSON; use `null` if no IMPLEMENTING entry
  matches the active plan.
- `allowed_actions` is required in the JSON.
- `files_to_read_first` = files the fresh agent must read before touching code.
- `rules_active` = rule files relevant to the pending work.
- `project_knowledge` = pointer to profile/index and the relevant topic
  blocks the fresh session should load first. Fields are `null` when no
  profile/index exists.
