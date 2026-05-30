# task-board-ops/migrate - legacy Markdown board migration

Read this when converting `.agents/mpi-kanban/kanban.md` or
`.claude/mpi-kanban/kanban.md` into the JSON task board. Migration is explicit:
show the user what will be created and wait for approval before writing.

---

## Source And Target

Sources:

```text
.agents/mpi-kanban/kanban.md
.claude/mpi-kanban/kanban.md
```

Targets:

```text
.agents/mpi-kanban/board.json
.agents/mpi-kanban/events.jsonl
.agents/mpi-kanban/tasks/<id>/task.json
.agents/mpi-kanban/tasks/<id>/...
```

If `board.json` already exists, do not import over it automatically. Produce a
merge proposal or stop for user direction.

---

## Column Mapping

Map old workflow columns conservatively:

| Legacy column | JSON column | Suggested maturity/status |
|---|---|---|
| `BACKLOG` | `todo` | `idea` / `active` |
| `PLANNING` | `todo` | `planned` / `active` |
| `IMPLEMENTING` | `doing` | `in-progress` / `active` |
| `VALIDATING` | `doing` | `validating` / `active` |
| `COMPLETED` | `done` | `complete` / `accepted` |

Do not recreate old columns in `board.json`.

---

## Entry Conversion

For each legacy entry:

1. Assign the next stable `MPI-*` ID in board order, starting at `MPI-1` unless
   imported IDs already exist.
2. Use the H3 text as `title`.
3. Use the first short body paragraph as `description`.
4. Preserve old metadata in linked files instead of task-card fields when it
   does not fit the JSON contract.
5. If the body contains `Plan file: <path>`, copy or reference it from
   `links.plan`. If the plan file is outside the task folder, record the
   original path in `plan.md`.
6. Convert legacy `steps` to `checklist.md`.
7. Preserve the full original entry block in `brief.md` under a
   `## Legacy Markdown Entry` heading.
8. Append `migration.task_imported` to global and task event logs.

Set `board.next_id` to one higher than the largest assigned ID.

---

## Legacy Snapshot

Keep the old Markdown board available. Preferred behavior:

1. Copy the source file to
   `.agents/mpi-kanban/legacy/kanban-<YYYY-MM-DD-HHMMSS>.md`.
2. Leave the original file in place unless the user explicitly approves moving
   or deleting it.
3. Do not write future live task changes to the legacy snapshot.

---

## Migration Dry Run Output

Before writing, show:

```text
JSON board migration proposal
Source: <path>
Target board: .agents/mpi-kanban/board.json
Tasks to create: <n>
Legacy snapshot: <path>

Column mapping:
- BACKLOG -> todo: <n>
- PLANNING -> todo: <n>
- IMPLEMENTING -> doing: <n>
- VALIDATING -> doing: <n>
- COMPLETED -> done: <n>

Potential conflicts:
- <conflict or "none">
```

Wait for explicit approval.

---

## Migration Events

Append `migration.started` before writing files and `migration.completed` after
all files are written and validated. If migration fails midway, stop and report
the files that were written; do not delete user data automatically.
