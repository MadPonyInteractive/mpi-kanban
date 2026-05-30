# task-board-ops/validate - validation and repair checks

Read this when validating or repairing a JSON task board. Validation reports
problems; repair requires explicit user approval before writing.

---

## Checks

Run these checks against `.agents/mpi-kanban/board.json` when it exists:

- `board.json` parses as JSON.
- `schema` is `mpi-kanban/board/v1`.
- `next_id` is a positive integer.
- Columns are exactly `todo`, `doing`, and `done`.
- Every column value is a list of task IDs.
- Every task ID matches `MPI-[1-9][0-9]*`.
- No task ID appears in more than one column.
- Every listed task has `tasks/<id>/task.json`.
- Every task folder with `task.json` is listed in the board.
- Every `task.json` parses as JSON.
- Task `schema` is `mpi-kanban/task-card/v1`.
- Task `id` matches its folder name.
- Task `column` matches the board column that lists it.
- Required fields exist: `id`, `title`, `column`, `created_at`,
  `updated_at`, and `links`.
- Every relative link stays inside the task folder.
- Existing linked files parse when they are JSON (`files.json`) or JSONL
  (`events.jsonl`).
- Event lines parse as one JSON object per line and use
  `schema: "mpi-kanban/event/v1"`.

For missing linked files, report an actionable warning unless the workflow
requires that file for the task's current state. Examples:

- `doing` task with no `checklist.md`: warning.
- task with `attention.required` and no `brief.md`: warning.
- `done` task with no `validation.md`: warning.

---

## Repair Proposals

Repairs must be proposed, not silently applied.

Safe repairs to propose:

- Create a missing optional linked file with default empty content.
- Add an unlisted task folder to `todo` when its `task.json` is valid.
- Remove a missing task ID from a board column only after preserving the broken
  reference in a repair note.
- Update `next_id` to one greater than the largest existing task ID.
- Fix a task `column` field to match the board when the board placement is
  clearly the intended state.

Unsafe repairs that require a specific user choice:

- Deleting orphaned task folders.
- Choosing between duplicate task IDs.
- Overwriting invalid JSON.
- Moving tasks between columns when task state and board placement disagree.
- Removing unknown files from task folders.

---

## Validation Output Shape

```text
JSON task board validation
Board: .agents/mpi-kanban/board.json
Tasks listed: <n>
Task folders: <n>
Errors: <n>
Warnings: <n>

Errors:
- <actionable error>

Warnings:
- <actionable warning>
```
