# task-board-ops/_schema - JSON task board schema

Reference for skills touching the primary MPI task board. Read this before
creating, moving, or updating board cards.

---

## Primary Files

```text
<project-root>/.agents/mpi-kanban/board.json
<project-root>/.agents/mpi-kanban/events.jsonl
<project-root>/.agents/mpi-kanban/tasks/<id>/task.json
<project-root>/.agents/mpi-kanban/tasks/<id>/events.jsonl
```

Do not use `.agents/mpi-kanban/state/tasks/` for human board cards. That path is
reserved for UUID-based agent coordination task records.

Legacy Markdown boards may exist at `.agents/mpi-kanban/kanban.md` or
`.claude/mpi-kanban/kanban.md`. Once `board.json` exists, treat Markdown boards
as migration inputs or snapshots, not as a second live source of truth.

---

## `board.json`

```json
{
  "schema": "mpi-kanban/board/v1",
  "next_id": 43,
  "columns": {
    "todo": ["MPI-40"],
    "doing": ["MPI-41"],
    "done": ["MPI-42"]
  }
}
```

Rules:

- `schema` is exactly `mpi-kanban/board/v1`.
- `next_id` is the next numeric suffix to allocate for a new `MPI-*` ID.
- Columns are exactly `todo`, `doing`, and `done`, in that order.
- Column arrays store ordered task IDs only.
- Every task ID in a column must have a matching
  `.agents/mpi-kanban/tasks/<id>/task.json`.
- A task ID must appear in exactly one column.
- Do not add planning, validation, agent, or archive columns.

User-facing labels are `To do`, `Doing`, and `Done`.

---

## Task Folder

```text
.agents/mpi-kanban/tasks/MPI-42/
  task.json
  brief.md
  plan.md
  checklist.md
  validation.md
  files.json
  events.jsonl
  handoffs/
  research/
```

Only `task.json` is required at creation. Create linked files when the workflow
needs them. Keep long-form plans, checklists, validation notes, handoffs, and
research outside the card JSON.

---

## `task.json`

```json
{
  "schema": "mpi-kanban/task-card/v1",
  "id": "MPI-42",
  "title": "Short task title",
  "description": "Optional short card summary.",
  "column": "doing",
  "maturity": "in-progress",
  "status": "active",
  "attention": {
    "state": "required",
    "reason": "Needs user decision before validation.",
    "updated_at": "2026-05-30T12:00:00Z"
  },
  "activeSessionTitle": "Codex implementation session",
  "created_at": "2026-05-30T12:00:00Z",
  "updated_at": "2026-05-30T12:30:00Z",
  "links": {
    "brief": "brief.md",
    "plan": "plan.md",
    "checklist": "checklist.md",
    "validation": "validation.md",
    "files": "files.json",
    "events": "events.jsonl",
    "handoffs": "handoffs/",
    "research": "research/"
  }
}
```

Required fields:

- `schema`
- `id`
- `title`
- `column`
- `created_at`
- `updated_at`
- `links`

Optional fields:

- `description`
- `maturity`
- `status`
- `attention`
- `activeSessionTitle`

`column` must match the column containing the task ID in `board.json`.
Canonical `maturity` values are:

| Column  | Values |
| ------- | ------ |
| `todo`  | `idea`, `planned`, `research`, `needs-decision`, `blocked`, `deferred` |
| `doing` | `in-progress`, `validating` |
| `done`  | `complete`, `rejected` |

When to use each `todo` value: `research` — the card needs investigation
before it can be planned; `needs-decision` — the work is understood but a
user/product decision is outstanding; `blocked` — ready in principle but
waiting on another card or an external dependency; `deferred` — deliberately
postponed, not being picked up in the current stretch.

For `done`: `rejected` — closed without being built, kept as a record of the
decision.

Column and maturity must stay coherent:

- `todo` cards use `idea`, `planned`, `research`, `needs-decision`, `blocked`, or `deferred`.
- `doing` cards use `in-progress` or `validating`.
- `done` cards use `complete` or `rejected`.

Nimbalyst `implementing` maps to MPI `in-progress`; it is not a valid
task-card maturity value.

Do not invent process-specific maturity values. Labels such as `active`,
`accepted`, `done`, `implementing`, `implementation`, `validated`,
`Validated`, `validation`, `spec`, `scoped`, `designed`, and `review` are not
valid task-card maturity values. Preserve that meaning in `status`,
`attention`, `description`, or linked task workspace files instead.

`attention.state` is `required` or `cleared` when present.

---

## Events

Events are passive append-only JSON lines for task-board history. They are not
the async message transport and do not require a live daemon, broker, remote
service, or real-time delivery.

```json
{"schema":"mpi-kanban/event/v1","id":"MPI-42","type":"task.moved","at":"2026-05-30T12:30:00Z","actor":"codex","from":"todo","to":"doing","summary":"Moved into active implementation."}
```

Initial event types:

- `task.created`
- `task.updated`
- `task.moved`
- `task.deleted`
- `attention.required`
- `attention.cleared`
- `checklist.updated`
- `checklist.item_checked`
- `checklist.item_unchecked`
- `validation.updated`
- `migration.started`
- `migration.task_imported`
- `migration.completed`

Append card-specific events to `tasks/<id>/events.jsonl`. Also append
matching task-card events to `.agents/mpi-kanban/events.jsonl`, including
creation, movement, deletion, `task.updated`, attention, checklist, validation,
and migration events. The task log gives local card history; the global log
gives board-wide history.
