---
name: mpi-handoff
description: MPI workflow pack - Hand the work to a fresh session in under two minutes. Commits and pushes the session's files, writes a handoff JSON from the running notes already in the active plan, and prints a paste-ready resume block. Use when the user says "handoff", "hand off", "create a handoff", "new session", "start fresh", "context is big", "I'm running out of context", "switch sessions", "$mpi-handoff", or "/mpi-handoff", and when one plan phase just ended with more phases pending. This is NOT close-out - when the work is finished, use mpi-end-session instead.
---

# mpi-handoff Skill

Save the thread and get out of the way. The session continues in a fresh
window within a minute or two, so nothing here re-derives what is already
written down.

**Budget: under two minutes, under ~20k tokens.** If this skill is taking
longer than a commit and a file write, something in it has grown that should
not have. That is the whole reason it exists apart from `mpi-end-session`.

## What this deliberately does NOT do

None of these run here. They belong to `mpi-end-session`, which runs once when
the work is actually finished, not once per session switch:

- rule/doc impact pass over changed files
- project-knowledge drift check
- knowledge-healing replay
- memory pass
- board validation and the consolidation sweep
- the `validating` card sweep
- `claim-auditor`, or any other sub-agent

A session that hands off is not done. Preserving knowledge into docs, rules,
and memory is close-out work, and paying for it at every switch is what made
handoffs cost more than the work they interrupt. Resist the pull to be
thorough here - thoroughness has a skill, and this is not it.

## The running notes are the source

The handoff body comes from the active plan's `## Current State`,
`## Plan Drift`, and `## Preservation Notes`, which `mpi-continue` keeps
current as each unit of work verifies. Read them, do not reconstruct them:
summarising a whole session from a large context is the most expensive thing
an agent can be asked to do, and it produces a worse answer than notes written
while the details were fresh.

Notes missing, empty, or clearly older than the work on disk? Reconstruct from
`git diff --stat HEAD` plus context, and say so in the report:

```text
Note: plan running notes were stale; handoff reconstructed from context. Slower than it should be.
```

A silent fallback hides that the cheap path was skipped, and the habit never
gets fixed.

## Process

### 1. Top up the running notes

Read the active plan. Update `## Current State` to name where the work stands,
and `## Plan Drift` if reality diverged. Add only the delta since the last
note - a few lines, not a session summary. No plan file? Skip; the handoff
JSON carries the state instead.

### 2. Commit and push

Running this skill IS the request to commit. Do not ask again, and do not
report "did not commit" - getting the work onto the branch is half the point
of handing off, and an uncommitted tree is invisible to the next session.

- `git status`, then stage files by name. Never `git add -A` or `git add .`.
- Commit message follows the repo's recent conventional style
  (`git log --oneline -5` if unsure). Subject says why.
- Push per `push_policy` in `.agents/mpi-kanban/project-profile.md`
  frontmatter; absent means `auto`.
  `ask` - one line, then push on approval. `never` - say the branch is
  unpushed.
- Rejected push: `git fetch`, `git merge --ff-only`, retry once. Still
  failing - report it and stop. Never force, never auto-rebase a shared tree.

Worker sub-agents never commit or push, whatever the policy says.

### 3. Leave the card where it is

The card stays in `doing`. Do not move it, do not close it, do not run a
maturity sweep. The work is not finished - that is why this is a handoff.

Look the card up with `findBoard()` then `findTask()` from
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md`, by task ID,
linked plan path, or required attention in `doing`. Needed for `task_card`
below. No JSON board - set `task_card` to null and continue.

### 4. Write the handoff

Path: `.agents/mpi-kanban/state/handoffs/<uuid>.json`, creating the directory
if missing. Generate `<uuid>` with
`python ${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/new_uuid.py`, or
`python -c "import uuid; print(uuid.uuid4())"` if that script is missing. Same
value for the filename and the `id` field.

```json
{
  "schema": "mpi-kanban/handoff/v1",
  "id": "<uuid>",
  "generated_at": "<ISO-8601>",
  "status": "open",
  "session": { "name": "<what this session was doing>", "branch": "<branch>" },
  "goal": {
    "original": "<what the user set out to do>",
    "status": "in_progress | blocked",
    "summary": "<1-3 sentences on where things stand>"
  },
  "plan": {
    "file": "<active plan path, or null>",
    "completed": ["<done item>"],
    "pending": ["<next item>"]
  },
  "task_card": {
    "id": "<MPI-*, or null>",
    "title": "<title, or null>",
    "column": "doing",
    "workspace": ".agents/mpi-kanban/tasks/<id>/",
    "links": { "plan": "<path>", "checklist": "<path>", "validation": "<path>" }
  },
  "next_action": {
    "description": "<exact first instruction for the fresh session>",
    "command": "mpi-continue"
  },
  "context": {
    "key_decisions": ["<decision and why>"],
    "constraints": ["<gotcha the next session would otherwise rediscover>"],
    "files_to_read_first": ["<path>"]
  },
  "resume_prompt": "<self-contained paragraph naming the handoff path and task ID>"
}
```

Keys earlier handoffs carried but this one omits - `from_session`, `to_role`,
`allowed_actions`, `knowledge_preservation`, `project_knowledge`,
`rules_active` - stay legal to read and are simply absent. `mpi-continue` loads
project knowledge from disk, so restating it cost a paragraph of generation
every switch and bought nothing.

Keep `context` tight. Three constraints the next session would waste time
rediscovering beat fifteen it already knows.

When `task_card.id` exists, also write
`.agents/mpi-kanban/tasks/<id>/handoffs/<uuid>.json`:

```json
{
  "schema": "mpi-kanban/task-handoff-pointer/v1",
  "canonical_handoff": ".agents/mpi-kanban/state/handoffs/<uuid>.json"
}
```

Never duplicate the handoff body into the task workspace. Add the handoff to
`active_handoffs` in `.agents/mpi-kanban/state/index.json`, update
`index.updated_at`, and mark any handoff this one supersedes resolved. Parse
that file as `utf-8-sig` - a BOM is common in the wild and plain `utf-8`
`json.load` dies on it.

### 5. Report

Three lines plus the block. Nothing else - anything worth more than this
belongs in the plan or the handoff, and the user is switching windows right
now.

```text
**COMMITTED:** <subject> (<n> files) - pushed | not pushed (<policy>)
**CARD:** <MPI-* id and title> stays in doing   (or "no board card")
**HANDOFF:** .agents/mpi-kanban/state/handoffs/<uuid>.json

To resume in a new session, paste this:
---
Read .agents/mpi-kanban/state/handoffs/<uuid>.json and use mpi-continue to continue from where we left off.
The next action is: <next_action.description>
---
```

## Hard rules

- Never `git add -A` or `git add .`.
- Never move, close, or re-mature the card. That is close-out.
- Never edit rules, docs, or memory here, even when the gap is obvious. Note it
  in `context.constraints` and let close-out handle it.
- Never spawn a sub-agent.
- `resume_prompt` must stand alone - the fresh session has zero memory of this
  one.
- New handoffs go under `.agents/mpi-kanban/state/handoffs/`. `docs/handoffs/`
  is legacy compatibility, not canonical state.
- Never edit files under the installed plugin root.
- The user said the work is finished, not paused -> stop and route to
  `mpi-end-session`. Handing off finished work leaves the card open forever.

## Success criteria

- Files committed by name, pushed per policy.
- Handoff JSON written, indexed in `active_handoffs`, pointer written when a
  card exists.
- The paste block printed, self-contained.
- The card is still in `doing`.
- No rule, doc, or memory file was touched.
