# interop-ops/modes - source-of-truth modes

Read this before a skill mutates board lifecycle state or bridges MPI Kanban
with another tracker. Interop state is durable project-local coordination state,
not task-card metadata.

## State File

The interop state file lives at:

```text
<project-root>/.agents/mpi-kanban/state/interop.json
```

If the file is missing, treat the project as `file` mode until a sync skill or
explicit mode-switch flow creates it.

## Schema

```json
{
  "schema": "mpi-kanban/interop/v1",
  "updated_at": "<ISO-8601 timestamp>",
  "source_of_truth": "file",
  "last_detected_environment": {
    "kind": "generic",
    "detected_at": "<ISO-8601 timestamp>",
    "signals": []
  },
  "last_sync_at": null,
  "last_export_at": null,
  "id_mappings": []
}
```

`source_of_truth` values:

- `file` - portable default. MPI workflow skills mutate
  `.agents/mpi-kanban/board.json`, task workspaces, passive event logs, and
  coordination state directly. Once `board.json` exists, legacy
  `.agents/mpi-kanban/kanban.md` files are migration inputs or compatibility
  snapshots, not a second live board.
- `nimbalyst` - Nimbalyst sessions and trackers are canonical. MPI skills must
  not update both Nimbalyst and the JSON task board during normal work. Board
  import/export happens only through explicit sync boundaries.

`last_detected_environment.kind` values:

- `generic` - no Nimbalyst-specific tools or session phase support detected.
- `nimbalyst` - Nimbalyst tracker/session capabilities detected.
- `unknown` - detection was attempted but inconclusive.

`id_mappings` is an array. Each item maps one MPI task to a Nimbalyst tracker
item without adding fields to the task card:

```json
{
  "mpi": {
    "board": ".agents/mpi-kanban/board.json",
    "task_id": "MPI-42",
    "title": "<task title>",
    "task_file": ".agents/mpi-kanban/tasks/MPI-42/task.json"
  },
  "nimbalyst": {
    "tracker_id": "<tracker item id>",
    "session_id": "<session id or null>"
  },
  "last_synced_at": "<ISO-8601 timestamp>",
  "last_mpi_fingerprint": "<stable hash or null>",
  "last_nimbalyst_fingerprint": "<stable hash or null>"
}
```

## Mode Rules

In `file` mode:

- Non-Nimbalyst environments keep the normal MPI workflow behavior.
- Planning, continue, handoff, cleanup, and end-session skills may mutate the
  JSON board and task workspaces when their normal gates are satisfied.
- Legacy Markdown board mutation is allowed only before JSON-board migration or
  during an explicit migration/snapshot boundary. If `board.json` exists,
  workflows must treat it and `.agents/mpi-kanban/tasks/<id>/` as canonical.

In `nimbalyst` mode:

- Nimbalyst tracker items and session phase are the live source of truth.
- MPI workflow skills must not live-update `.agents/mpi-kanban/board.json` as a
  competing board.
- File snapshots are allowed only on explicit import/export/sync boundaries.
- Snapshot writes must produce the locked JSON board columns `todo`, `doing`,
  and `done`; they must not recreate legacy MPI lifecycle columns.
- If a workflow skill is about to mutate MPI board state, it should stop and
  direct the user to the Nimbalyst tracker/session workflow or an explicit
  `mpi-nimbalyst-sync` command.

## Boundary Mapping

Nimbalyst phases cross the file boundary as task-card state, not as extra MPI
board columns:

| Nimbalyst phase | MPI JSON column | MPI task-card preservation |
|---|---|---|
| `backlog` | `todo` | use `maturity` / `status` badges for backlog detail |
| `planning` | `todo` | use `maturity` / `status` badges and `links.plan` |
| `implementing` | `doing` | use `status`, checklist links, and active session context |
| `validating` | `doing` | use `status`, validation links, and attention when needed |
| `complete` | `done` | use `status` and validation/archive links |

Mapping state, including Nimbalyst tracker IDs, session IDs, sync times, and
fingerprints, stays in `state/interop.json` `id_mappings`. Do not copy that
metadata into `.agents/mpi-kanban/tasks/<id>/task.json`.

When detected environment and recorded mode disagree, do not switch silently.
Surface the mismatch and ask before changing `source_of_truth`.
