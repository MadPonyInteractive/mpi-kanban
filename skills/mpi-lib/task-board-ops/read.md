# task-board-ops/read - find and load the JSON task board

Read this when a workflow needs to find the active board, allocate a task ID,
or load visible task cards. For the schema, read `_schema.md` first.

---

## `findBoard()`

1. Resolve path: `<project-root>/.agents/mpi-kanban/board.json`.
2. Try `Read`.
3. If found, parse JSON and return path plus data.
4. If missing, return `null`. The caller decides whether to bootstrap,
   migrate from legacy Markdown, or surface a setup notice.

If both `board.json` and `kanban.md` exist, use `board.json` as canonical.
Do not write to `kanban.md` as a live board. Treat `source_of_truth: "file"` as
the local JSON/file-backed board when `board.json` exists; it is not permission
to use the old Markdown board.

---

## `ensureBoard()`

Use only for workflows that are allowed to create a board, such as `mpi-init`
or an approved migration.

1. Call `findBoard()`.
2. If found, return it.
3. If missing:
   - Read `<mpi-lib-root>/templates/board.json`.
   - Write it to `<project-root>/.agents/mpi-kanban/board.json`.
   - Create an empty `<project-root>/.agents/mpi-kanban/events.jsonl`.
   - Create `<project-root>/.agents/mpi-kanban/tasks/`.
4. If legacy `.agents/mpi-kanban/kanban.md` exists, tell the user it remains
   a legacy migration source or snapshot. Propose running `mpi-project-refresh`
   to move it under `.agents/mpi-kanban/legacy/` or replace it with a tombstone
   after approval. Do not delete or overwrite it silently.

---

## `allocateTaskId(board)`

1. Read `board.next_id`.
2. Build `MPI-<next_id>`.
3. Increment `next_id` by 1 in `board.json` before writing the task folder.
4. If any existing task ID has a numeric suffix greater than or equal to
   `next_id`, set `next_id` to one more than the largest suffix before
   allocating.

Never accept a user-supplied task ID for a new task.

---

## `loadTask(id)`

1. Validate `id` against `^MPI-[1-9][0-9]*$`.
2. Read `.agents/mpi-kanban/tasks/<id>/task.json`.
3. Parse JSON and confirm:
   - `schema` is `mpi-kanban/task-card/v1`;
   - `id` matches the folder and requested ID;
   - `column` is `todo`, `doing`, or `done`;
   - when present, `maturity` is exactly `idea`, `planned`, `research`,
     `needs-decision`, `blocked`, `deferred`, `in-progress`, `validating`,
     `complete`, or `rejected`, and matches the task's column.
4. Return the parsed task plus paths to linked workspace files.

If `maturity` is invalid or incoherent, report it as board drift before using
the task. Do not preserve labels such as `Validated`, `spec`, `active`, `done`,
`implementing`, or `implementation` as maturity values during the next write;
use `<mpi-lib-root>/task-board-ops/mutate.md` to correct them.

---

## `listTasks(column)`

1. Read `board.json`.
2. Select the ordered ID array for `column`.
3. Load each task with `loadTask(id)`.
4. Preserve board order in the returned list.

---

## `findTask(predicate)`

Search in this order:

1. `doing`
2. `todo`
3. `done`

Common predicates:

- `task.id === <id>` for direct user references.
- `task.links.plan` points at a plan path.
- `task.attention.state === "required"` for active user decisions.
- `task.title === <title>` only when no duplicate title exists.
