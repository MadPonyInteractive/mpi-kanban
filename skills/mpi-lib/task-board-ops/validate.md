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
- Task `maturity`, when present, is one of `idea`, `planned`, `research`,
  `needs-decision`, `blocked`, `deferred`, `in-progress`, `validating`,
  `complete`, or `rejected`.
- Task `maturity` matches the board column: `todo` allows `idea`, `planned`,
  `research`, `needs-decision`, `blocked`, or `deferred`; `doing` allows
  `in-progress` or `validating`; `done` allows `complete` or `rejected`.
- Task `maturity` does not contain process/status labels such as `Validated`,
  `validated`, `validation`, `spec`, `active`, `accepted`, `done`,
  `implementing`, or `implementation`. These are invalid even if they describe
  real work state.
- A `done` task card should not keep `status: "active"` after completion is
  accepted.
- Required fields exist: `id`, `title`, `column`, `created_at`,
  `updated_at`, and `links`.
- Every relative link stays inside the task folder.
- Existing linked files parse when they are JSON (`files.json`) or JSONL
  (`events.jsonl`).
- Event lines parse as one JSON object per line and use
  `schema: "mpi-kanban/event/v1"`.
- If `.agents/mpi-kanban/state/index.json` exists, its `board` field points at
  `.agents/mpi-kanban/board.json`.
- `state/index.json` `active_tasks`, when present, does not list missing or
  `closed` coordination task records.
- Coordination task records listed in `active_tasks` that name a JSON
  `task_card` in `done` are unresolved only (`needs_review`,
  `needs_verification`, or `needs_integration`); completed, verified, or closed
  work must not stay active.
- Every `state/files/<uuid>.json` parses, uses
  `schema: "mpi-kanban/file-claim/v1"`, sets exactly one of `path` (string) or
  `paths` (list of strings), carries a known claim status, and is written
  without a UTF-8 BOM.
- If `.agents/mpi-kanban/state/interop.json` has `source_of_truth: "file"`,
  treat that as the JSON board and task workspaces, not `kanban.md`.
- If `.agents/mpi-kanban/kanban.md` still exists, it is either under
  `.agents/mpi-kanban/legacy/` or has a top-of-file tombstone containing
  `SUPERSEDED` or `DO NOT EDIT`.
- Boot docs (`START-HERE.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, project
  memory indexes, and profile/index read-first docs) do not route active task
  continuation through `kanban.md` when `board.json` exists.

For missing linked files, report an actionable warning unless the workflow
requires that file for the task's current state. Examples:

- `doing` task with no `checklist.md`: warning.
- task with `attention.required` and no `brief.md`: warning.
- `done` task with no `validation.md`: warning.
- retained legacy `kanban.md` without a tombstone: warning.
- boot docs mention `kanban.md` only as legacy/snapshot/migration context:
  allowed.
- boot docs tell agents to read, edit, continue, or boot active work from
  `kanban.md`: warning or repair finding.
- active coordination task records still point at a done card with no
  unresolved status: warning or repair finding.

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
- Replace an invalid or incoherent task `maturity` with the column-coherent MPI
  value after preserving the old label in a repair note when useful:
  `todo` -> `planned`, `idea`, `research`, `needs-decision`, `blocked`, or
  `deferred`; `doing` -> `in-progress` or `validating`;
  `done` -> `complete` or `rejected`.
- Update `state/index.json` `board` to `.agents/mpi-kanban/board.json` when
  `board.json` exists.
- Remove `closed` coordination task records from `active_tasks`.
- Correct a file-claim record's `schema` to `mpi-kanban/file-claim/v1`, strip a
  leading BOM, or fold a stray `paths` array into `path` when it holds one
  entry. These are format repairs; never change which paths a claim covers, and
  never reassign its owner.
- For a coordination task tied to a `done` card, remove it from `active_tasks`
  when its status is `verified`, `completed`, or `closed`, preserving the
  record for archive/cleanup.
- Move a migrated `.agents/mpi-kanban/kanban.md` to
  `.agents/mpi-kanban/legacy/kanban-<timestamp>.md` after preserving a snapshot.
- Replace a retained `.agents/mpi-kanban/kanban.md` with a tombstone after
  approval.
- Replace active boot-doc pointers from `kanban.md` to `board.json` and
  `tasks/<id>/` after approval.

Unsafe repairs that require a specific user choice:

- Deleting orphaned task folders.
- Choosing between duplicate task IDs.
- Overwriting invalid JSON.
- Moving tasks between columns when task state and board placement disagree.
- Removing unknown files from task folders.
- Deleting the only copy of a legacy Markdown board.
- Silently rewriting user-owned boot docs or memory entries.

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
