---
name: mpi-archive
description: MPI workflow pack - Archive completed JSON task-board tasks. Use when the user says "MPI archive", "archive completed tasks", "archive completed entries", "archive task <id>", "archive entry <title>", "$mpi-archive", or "/mpi-archive".
---

# mpi-archive Skill

Archive completed work out of the active human board: `.agents/mpi-kanban/board.json`
plus task workspaces under `.agents/mpi-kanban/tasks/<id>/`.

This skill removes work from the active board only after preserving the task
workspace and recording what changed.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Inputs

- `completed` / `completed tasks`: archive every task ID under
  `board.columns.done`.
- A specific JSON task ID, such as `MPI-42`: archive that exact `done` task.

If the user asks only to "archive entries" without saying completed or
providing a task ID, ask which tasks to archive.

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
3. If `board.json` is missing, stop and report that there is no board to
   archive from.
4. Final response includes:
   - Number of tasks archived.
   - Archive location used.
   - Clickable links to `[board.json](.agents/mpi-kanban/board.json)` and the
     archived task workspace.

## Hard rules

- Do not bootstrap a missing board. If no board exists, report that there is
  nothing to archive.
- Do not use fuzzy matching for the final archive target. Ask the user to pick
  an exact task ID if needed.
- Do not archive `todo` or `doing` tasks without explicit user confirmation and
  a clear coordination-state check.
- Do not remove a task ID from `board.json` before preserving its workspace.
- Do not edit archived task workspace contents except for the minimal metadata
  needed to identify the archive action.
- Do not treat `.agents/mpi-kanban/state/tasks/` as human task workspaces; that
  path is reserved for UUID coordination task records.
