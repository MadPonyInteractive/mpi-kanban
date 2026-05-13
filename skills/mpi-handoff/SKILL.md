---
name: mpi-handoff
description: Preserve current MPI work and generate a structured JSON handoff document so a fresh session can resume with mpi-continue. Use when user says "handoff", "new session", "context is big", or "/mpi-kanban:mpi-handoff", or when a plan phase just completed and a new one starts.
---

# mpi-handoff Skill

Preserves current MPI work and produces a handoff document at
`docs/handoffs/YYYY-MM-DD-HH-MM-<slug>.json` that a fresh session can load to
resume with `mpi-continue` — no re-explanation needed.

## When to invoke

- User says "handoff", "new session", "start fresh", "context is big", or runs
  `/mpi-kanban:mpi-handoff`.
- Context usage is high and work is mid-flight.
- A plan phase just completed and a new phase starts next.

## Process

### Step 1 — Gather state from conversation

Extract all of the following from conversation context. **Do NOT run git
commands** — work is mid-flight and uncommitted, git state is irrelevant.

- What was the user originally trying to accomplish?
- What is complete vs. pending?
- What is the very next action the fresh session should take?
- Key decisions, constraints, or gotchas discovered during this session?
- Which plan file is active (if any)?
- Which files were modified or created this session?

### Step 2 — Identify the active plan

If a plan file exists in `docs/plans/`, read its current state:

- Note the plan file path.
- List completed `[x]` and pending `[ ]` to-dos.
- Identify the next `[ ]` item.

### Step 3 — Look up the active kanban entry

Read `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/find.md` for `findKanban` +
`findEntry`. Then:

1. Call `findKanban()`. If the file does not exist, set `kanban_entry` to
   `null` and continue.
2. Otherwise call `findEntry(e => e.column === "IMPLEMENTING" && e.body matches "Plan file: <activePlan>")`.
3. If a match is found → `kanban_entry = entry.title`. Otherwise → `null`.

### Step 4 — Preservation pass

Before writing the handoff, capture knowledge while the current session still
has context:

- Update the active plan's `## Current State`, `## Plan Drift`, and
  `## Preservation Notes` if they are stale.
- If known docs/rules/memory updates can be made accurately, do them now,
  respecting project approval rules for architectural rule files.
- If updates are blocked, need approval, or should wait for completion, record
  them as pending preservation items in the handoff.

Do not commit. Do not run cleanup.

### Step 5 — Write the handoff document

Create file at `docs/handoffs/YYYY-MM-DD-HH-MM-<slug>.json` (create the
`docs/handoffs/` directory if missing).

`<slug>` is 2-3 words from the goal, hyphenated (e.g., `video-history-support`).

Use this exact JSON structure:

```json
{
  "schema": "mpi-handoff/v1",
  "generated_at": "<ISO-8601 timestamp>",
  "session": {
    "name": "<best description of the session>",
    "branch": "<current git branch — from conversation or plan file, NOT a git command>"
  },
  "goal": {
    "original": "<what the user set out to do — verbatim or close paraphrase>",
    "status": "in_progress | blocked | complete",
    "summary": "<1-3 sentence summary of where things stand>"
  },
  "plan": {
    "file": "<path to active plan file, or null>",
    "completed": ["<done item 1>", "<done item 2>"],
    "pending": ["<next item 1>", "<next item 2>"]
  },
  "kanban_entry": "<title of active IMPLEMENTING entry, or null>",
  "knowledge_preservation": {
    "completed": [
      "<docs/rules/memory/plan preservation done before handoff>"
    ],
    "pending": [
      "<preservation item the next session or end-session must handle>"
    ]
  },
  "next_action": {
    "description": "<exact instruction for fresh session — be precise>",
    "command": "<optional: skill or command to run first, e.g. /mpi-kanban:mpi-continue>"
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
  "rules_active": [
    "<rule file that must be read>",
    "<rule file 2>"
  ],
  "resume_prompt": "<single paragraph the user can paste into a new session. Second person, present tense. Mentions the handoff file path AND the kanban entry title (if not null).>"
}
```

### Step 6 — Print the resume prompt

After writing the file, output to the user (and ONLY this — do not dump the
full JSON). The copy/paste block is mandatory:

```
Handoff saved: docs/handoffs/<filename>.json
Active kanban entry: "<title>"   (or "none" if kanban_entry is null)

To resume in a new session, paste this:
---
Read docs/handoffs/<filename>.json and use /mpi-kanban:mpi-continue to continue from where we left off.
The next action is: <next_action.description>
---
```

## Hard rules

- No git commands — work is mid-flight, git state is not part of the handoff.
- `resume_prompt` MUST be self-contained. The fresh session has zero memory.
- The final chat output MUST include the copy/paste resume block every time.
- `kanban_entry` is required in the JSON — `null` if no IMPLEMENTING entry
  matches the active plan.
- `files_to_read_first` = files the fresh agent must read before touching code.
- `rules_active` = rule files relevant to the pending work.
