---
name: mpi-handoff
description: MPI workflow pack - Hand the work to a fresh session in under two minutes. Commits and pushes the session's files, writes a handoff JSON from the running notes already in the active plan, and prints a paste-ready resume block. Use when the user says "handoff", "hand off", "create a handoff", "new session", "start fresh", "context is big", "I'm running out of context", "switch sessions", "$mpi-handoff", or "/mpi-handoff", and when one plan phase just ended with more phases pending. This is NOT close-out - when the work is finished, use mpi-end-session instead.
---

# mpi-handoff Skill

Save the thread and get out of the way. **Budget: under two minutes, under
~20k tokens** - a commit and a file write. Taking longer means something here
grew that should not have; that is why this skill exists apart from
`mpi-end-session`.

The user said the work is finished, not paused -> stop and route to
`mpi-end-session`; handing off finished work leaves the card open forever.

**Never here** (close-out's job, once per finished job): rule/doc impact pass,
project-knowledge drift check, knowledge healing, memory pass, board
validation, consolidation sweep, `validating` sweep, any sub-agent
(`claim-auditor` included), any edit to rules, docs, or memory - an obvious gap
goes in `context.constraints`. Never move, close, or re-mature the card. Never
edit files under the installed plugin root.

## 1. Top up the running notes

The handoff body comes from the active plan's `## Current State`,
`## Plan Drift`, and `## Preservation Notes`, which `mpi-continue` keeps current.
Read them; do not reconstruct a session from a large context. Add only the
delta since the last note - a few lines. No plan file -> skip; the JSON carries
the state.

Notes missing, empty, or older than the work on disk -> reconstruct from
`git diff --stat HEAD` plus context, and say so; a silent fallback hides the
skipped cheap path:
`Note: plan running notes were stale; handoff reconstructed from context. Slower than it should be.`

## 2. Commit and push

Running this skill IS the request to commit. Do not ask again, and do not
report "did not commit" - an uncommitted tree is invisible to the next session.

- `git status --short`, `git add` new files by name - never `-A` or `.` - then
  `git commit --only <paths>`. A bare commit commits the whole INDEX, so a
  peer's staged files ride along: `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/git-ops/commit.md`.
- Message in the repo's recent conventional style; the subject says why.
- Push per `push_policy` in `.agents/mpi-kanban/project-profile.md`
  frontmatter; absent means `auto`. `ask` - one line, push on approval.
  `never` - say the branch is unpushed.
- Rejected push: `git fetch`, `git merge --ff-only`, retry once. Still failing
  -> report it and stop. Never force, never auto-rebase a shared tree.

Worker sub-agents never commit or push, whatever the policy says.

## 3. Find the card, leave it in `doing`

`findBoard()` then `findTask()` from
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md`, by task ID,
linked plan, or required attention in `doing`. No JSON board -> `task_card`
is null.

## 4. Write the handoff

`.agents/mpi-kanban/state/handoffs/<uuid>.json` (create the directory if
missing; `docs/handoffs/` is legacy, never canonical). `<uuid>` from
`python ${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/new_uuid.py`, or
`python -c "import uuid; print(uuid.uuid4())"` if missing; same value in the
filename and `id`.

```json
{
  "schema": "mpi-kanban/handoff/v1",
  "id": "<uuid>",
  "generated_at": "<ISO-8601>",
  "status": "open",
  "from_session": ".agents/mpi-kanban/state/sessions/<claude-session-id>.json",
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

`resume_prompt` must stand alone: the fresh session remembers none of this.
Keep `context` tight - three constraints it would rediscover beat fifteen it
knows. Older keys (`to_role`, `allowed_actions`, `knowledge_preservation`,
`project_knowledge`, `rules_active`) stay legal to read and are simply absent.
`from_session` is NOT optional: it is the only thing tying an abandoned file
claim back to the session that walked away.

Card exists -> also write `.agents/mpi-kanban/tasks/<id>/handoffs/<uuid>.json`
as `{"schema": "mpi-kanban/task-handoff-pointer/v1", "canonical_handoff":
".agents/mpi-kanban/state/handoffs/<uuid>.json"}`; never duplicate the body
there. Add the handoff to `active_handoffs` in
`.agents/mpi-kanban/state/index.json` (parse as `utf-8-sig` - a BOM is common
and plain `utf-8` `json.load` dies on it), update `index.updated_at`, and
resolve any handoff this one supersedes.

Release this session's file claims, or the next session is locked out of its
own card: `python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/task_ops.py" release`.

## 5. Report

Print these four lines as-is, then the paste block, nothing else. Line 1 is
word for word `Nothing breaking`, `Not checked: <why>` or `BREAKS USERS: ...`,
never a paraphrase. The paste block gets its own fence so the app shows a copy
button; a link or a path alone is never the handoff.

```text
BREAKS USERS: <what> - <fixed, or "card MPI-n made"> | Nothing breaking | Not checked: <why>
Committed: <subject> (<n> files) - pushed | not pushed (<policy>)
Card: <MPI-* id and title> stays in doing   (or "no board card")
Handoff: <path> - <n> claim(s) released
```

Tab name: when the harness can read this tab's title (Claude Desktop:
`get_session`, session_id `self`, a deferred tool loaded via ToolSearch) and
it ends in a number, the paste block's first line names the next tab;
otherwise drop that line.

```text
Name this tab "<title with the number + 1>".      (only when known)
Read .agents/mpi-kanban/state/handoffs/<uuid>.json and use mpi-continue to continue from where we left off.
The next action is: <next_action.description>
```
