---
name: mpi-archive
description: MPI workflow pack - Archive completed JSON task-board tasks. Use when the user says "MPI archive", "archive completed tasks", "archive completed entries", "archive task <id>", "archive entry <title>", "$mpi-archive", or "/mpi-archive".
---

# mpi-archive Skill

Take completed work off the active board (`.agents/mpi-kanban/board.json`)
while each task folder stays exactly where it is, under
`.agents/mpi-kanban/tasks/<id>/`. Archiving in place is the default and the
only path: docs, commits, and memory notes link into those folders, and moving
them breaks every link.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Inputs

- `completed` / `completed tasks`: every task ID under `board.columns.done`.
- A specific JSON task ID, such as `MPI-42`: that exact `done` task.

If the user asks only to "archive entries" without saying completed or giving a
task ID, ask which tasks to archive. Never fuzzy-match the final target; ask
for an exact ID.

## Steps

1. No `.agents/mpi-kanban/board.json` -> stop and report there is nothing to
   archive. Never bootstrap a board.
2. Read `.agents/mpi-kanban/state/index.json` when present, then the
   `open_messages` that target the selected task IDs, related coordination
   tasks, files, workspace, agent, role, or user
   (`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/messages.md`).
   Treat `open`, `acknowledged`, and `replied` as unresolved; surface one that
   changes the archive decision and ask before archiving. This is an async
   boundary check only, not live interruption or daemon behavior.
3. A selected card with a linked `validation.md` that does not exist -> surface
   that risk in one line and ask before archiving it.
4. Run the one command - it refuses any card not in `done`, stamps
   `status: "archived"` on each `task.json`, removes the ids from
   `board.columns.done` without reformatting the rest of `board.json`, and
   appends `task.archived` to each task log and the global log:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/task_ops.py" archive MPI-42 MPI-43 --root <project-root>
   python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/task_ops.py" archive --all-done --root <project-root>
   ```

   Never hand-edit `board.json` or `task.json` for this; an id dropped without
   the marker is an orphan that `validate_board.py --fix` puts straight back.
5. Report one line: `Archived <n> card(s) in place; folders kept.`

## Hard rules

- Only `done` cards archive. A `todo` or `doing` card needs the user's explicit
  confirmation and a clear coordination-state check, then a move to `done`
  through `mpi-continue` first.
- Never move, rename, or delete a task folder, and never edit its contents
  beyond what the command writes.
- Do not treat `.agents/mpi-kanban/state/tasks/` as human task workspaces; that
  path is reserved for UUID coordination task records.
