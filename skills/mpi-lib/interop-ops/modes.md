# interop-ops/modes - source-of-truth modes

Read this before a skill mutates board lifecycle state or bridges MPI Kanban
with another tracker. Interop state is durable project-local coordination state,
not kanban entry metadata.

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
  `.agents/mpi-kanban/kanban.md` and coordination state directly.
- `nimbalyst` - Nimbalyst sessions and trackers are canonical. MPI skills must
  not update both Nimbalyst and `.agents/mpi-kanban/kanban.md` during normal
  work. Markdown board import/export happens only through explicit sync
  boundaries.

`last_detected_environment.kind` values:

- `generic` - no Nimbalyst-specific tools or session phase support detected.
- `nimbalyst` - Nimbalyst tracker/session capabilities detected.
- `unknown` - detection was attempted but inconclusive.

`id_mappings` is an array. Each item maps one MPI entry to a Nimbalyst tracker
item without adding fields to the Markdown card:

```json
{
  "mpi": {
    "board": ".agents/mpi-kanban/kanban.md",
    "title": "<entry title>",
    "plan_file": "docs/plans/<plan>.md"
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
  Markdown board when their normal gates are satisfied.
- The `VALIDATING` lifecycle remains in force.

In `nimbalyst` mode:

- Nimbalyst tracker items and session phase are the live source of truth.
- MPI workflow skills must not live-update `.agents/mpi-kanban/kanban.md` as a
  competing board.
- File snapshots are allowed only on explicit import/export/sync boundaries.
- If a workflow skill is about to mutate MPI board state, it should stop and
  direct the user to the Nimbalyst tracker/session workflow or an explicit
  `mpi-nimbalyst-sync` command.

When detected environment and recorded mode disagree, do not switch silently.
Surface the mismatch and ask before changing `source_of_truth`.
