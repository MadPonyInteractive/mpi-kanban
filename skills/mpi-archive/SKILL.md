---
name: mpi-archive
description: MPI workflow pack - Archive completed JSON task-board tasks and legacy kanban entries. Use when the user says "MPI archive", "archive completed tasks", "archive completed kanban entries", "archive completed entries", "archive task <id>", "archive kanban entry <title>", "archive entry <title>", "$mpi-archive", or "/mpi-archive".
---

# mpi-archive Skill

Archive completed work out of the active human board. For JSON-board projects,
the active board is `.agents/mpi-kanban/board.json` plus task workspaces under
`.agents/mpi-kanban/tasks/<id>/`. Legacy `.agents/mpi-kanban/kanban.md`
archives are compatibility behavior only when no JSON board exists.

This skill removes work from the active board only after preserving the task
workspace or legacy entry block and recording what changed.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Inputs

- `completed` / `completed tasks`: archive every task ID under
  `board.columns.done`.
- A specific JSON task ID, such as `MPI-42`: archive that exact `done` task.
- `completed kanban entries`: archive every legacy entry under `## COMPLETED`
  only when no JSON board exists or the user explicitly asks for legacy
  compatibility.
- A specific legacy entry title: archive the exact matching `### <title>` entry
  from any legacy column only when working with a legacy board.

If the user asks only to "archive entries" without saying completed, providing
a task ID, or providing an exact legacy title, ask which tasks to archive.

## Checklist

Lib pointers:

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` - JSON board and task workspace
  contract.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md` - `findBoard`, `loadTask`,
  `listTasks`.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` - `appendEvent` and structured
  board/task writes.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/validate.md` - board validation checks before
  and after archive.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/messages.md` - read relevant unresolved
  messages before removing tasks from the active board.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/kanban-ops/archive.md` - legacy archive file selection,
  rotation, and move procedure.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/kanban-ops/find.md` - legacy `findKanban`.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/kanban-ops/_schema.md` - legacy column and entry block shape.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/kanban-ops/errors.md` - legacy error wording.

Steps:

1. Call `findBoard()`.
2. If `board.json` exists, use the JSON archive path:
   - Determine the selector from the user request: all `done` tasks or one
     exact `MPI-*` ID.
   - Load each selected task with `loadTask(id)`.
   - Read `.agents/mpi-kanban/state/index.json` when present, then load
     `open_messages` that target the selected task IDs, related coordination
     tasks, files, workspace, agent, role, or user. Treat `open`,
     `acknowledged`, and `replied` as unresolved. Surface relevant unresolved
     messages and ask before archiving; do not remove a visible task while an
     unresolved message changes the archive decision. This is an async boundary
     check only, not live interruption or daemon behavior.
   - Refuse to archive a task that is not in `done` unless the user explicitly
     confirms an exceptional archive and any active coordination state is
     closed or released.
   - Read `validation.md` when linked. If a `done` task has no validation
     record, surface that risk and ask before archiving.
   - Preserve the task workspace under an archive location approved by the
     project conventions, keeping `task.json`, checklist, validation, events,
     handoffs, and research together.
   - Remove the task ID from `board.columns.done` only after preservation.
   - Append a task-scoped and global event with type `task.deleted` and a
     summary that identifies the archive location.
   - Do not write long archive notes into `task.json`; preserve them in the
     workspace snapshot.
3. If `board.json` is missing, use the legacy compatibility path:
   - Determine the selector: completed legacy entries or one exact title.
   - Follow `archiveEntries(selector)` exactly.
4. Final response includes:
   - Number of tasks or entries archived.
   - Archive location used.
   - Clickable links to `[board.json](.agents/mpi-kanban/board.json)` and the
     archived task workspace for JSON projects, or to
     `[kanban.md](.agents/mpi-kanban/kanban.md)` and the archive file for
     legacy projects.

## Hard rules

- Do not bootstrap a missing board. If no JSON board or legacy board exists,
  report that there is nothing to archive.
- Do not use fuzzy matching for the final archive target. Ask the user to pick
  an exact task ID or legacy title if needed.
- Do not archive `todo` or `doing` tasks without explicit user confirmation and
  a clear coordination-state check.
- Do not remove a task ID from `board.json` before preserving its workspace.
- Do not edit archived task workspace contents except for the minimal metadata
  needed to identify the archive action.
- Do not treat `.agents/mpi-kanban/state/tasks/` as human task workspaces; that
  path is reserved for UUID coordination task records.
- Do not archive legacy `kanban.md` entries as the primary path when
  `board.json` exists, unless the user explicitly requested legacy
  compatibility.
