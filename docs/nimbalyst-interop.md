# Nimbalyst Interop

This document defines the first stable mapping between MPI task-board cards and
Nimbalyst tracker/session state. It is a design contract for
`mpi-nimbalyst-sync` import/export dry runs and future concrete tracker
mutations.

## Source Of Truth

MPI records the active source of truth in:

```text
.agents/mpi-kanban/state/interop.json
```

Modes:

- `file` - MPI JSON task board is canonical:
  `.agents/mpi-kanban/board.json` plus
  `.agents/mpi-kanban/tasks/<id>/`.
- `nimbalyst` - Nimbalyst tracker items and session phase are canonical.

In `nimbalyst` mode, agents must not update both Nimbalyst trackers and
`.agents/mpi-kanban/board.json` during normal work. Board updates are explicit
import/export snapshots. Legacy Markdown board snapshots may be produced only
as compatibility artifacts; once `board.json` exists, `kanban.md` is not a live
source of truth.

## Environment Detection

Nimbalyst availability is detected from visible capability signals:

- MCP tools or connectors whose names clearly expose Nimbalyst tracker
  operations.
- Session phase support compatible with `backlog`, `planning`, `implementing`,
  `validating`, and `complete`. These are Nimbalyst phases, not MPI board
  columns.
- Project instructions that state Nimbalyst sessions or trackers are canonical.

Detection result values:

- `generic` - no Nimbalyst signal is visible.
- `nimbalyst` - tracker/session capabilities are visible.
- `unknown` - partial or conflicting signals are visible.

Detection never changes `source_of_truth` by itself. A mode change requires
explicit user approval.

## User Experience

In VS Code or a generic agent environment:

- Default mode is `file`.
- MPI workflow skills update `.agents/mpi-kanban/board.json`, task folders, and
  event logs directly.
- The VS Code extension renders the JSON task board as the visible work board.
- `mpi-nimbalyst-sync detect` should report `generic` unless Nimbalyst-specific
  capabilities are visible.

In Nimbalyst:

- Recommended mode is `nimbalyst` after explicit user approval.
- Nimbalyst trackers and session phase are canonical during normal work.
- MPI workflow skills must not live-update `board.json`.
- Use `mpi-nimbalyst-sync import to Nimbalyst` or
  `mpi-nimbalyst-sync export from Nimbalyst` for explicit boundary snapshots.

Mode mismatch prompt:

```text
Detected environment: <generic | nimbalyst | unknown>
Current MPI source of truth: <file | nimbalyst>

Switch source of truth to <target>? In file mode, MPI updates .agents/mpi-kanban/board.json, task folders, and event logs directly. In nimbalyst mode, Nimbalyst trackers/sessions are canonical and MPI board snapshots update only through explicit import/export snapshots.
```

## Phase Mapping

| MPI task column | Nimbalyst phase |
|---|---|
| `todo` | `backlog` or `planning` |
| `doing` | `implementing` or `validating` |
| `done` | `complete` |

Exporting from Nimbalyst uses the reverse mapping:

| Nimbalyst phase | MPI task column |
|---|---|
| `backlog` | `todo` |
| `planning` | `todo` |
| `implementing` | `doing` |
| `validating` | `doing` |
| `complete` | `done` |

Use task `maturity`, `status`, checklist links, validation links, and
`attention` to preserve distinctions that no longer have separate board
columns. Unknown Nimbalyst phases are conflicts. Do not invent new MPI columns,
and do not restore `BACKLOG`, `PLANNING`, `IMPLEMENTING`, `VALIDATING`, or
`COMPLETED` as live JSON-board columns.

Nimbalyst phase names are not MPI task-card maturity values. When importing or
exporting the implementation phase, map Nimbalyst `implementing` to MPI
`maturity: "in-progress"` on a `doing` card. Valid MPI maturity values are
`idea`, `planned`, `research`, `needs-decision`, `blocked`, and `deferred` for
`todo`; `in-progress` and `validating` for `doing`; `complete` and `rejected`
for `done`.

## Field Mapping

| MPI field | Nimbalyst field |
|---|---|
| task `title` | tracker title |
| Column | phase |
| `maturity` / `status` | status badges |
| `description` | description/notes |
| `links.plan` | plan file reference |
| board path | source board reference |
| interop `tracker_id` | tracker item ID |
| interop `session_id` | Nimbalyst session reference |

`tracker_id`, `session_id`, fingerprints, and sync timestamps are mapping
state stored in `.agents/mpi-kanban/state/interop.json`. They must not be added
to task-card JSON fields.

MPI-only files such as checklists, validation notes, handoffs, and research are
not Nimbalyst source fields unless a project-specific mapping says otherwise.
Preserve them when exporting a board snapshot if existing MPI state already has
them.

## Dry-Run Operations

Import dry run means MPI JSON task board -> Nimbalyst proposal:

1. Read `board.json` and visible `tasks/<id>/task.json` files.
2. Convert each entry to the phase and field mapping above.
3. Use `interop.json` mappings to decide whether each item is a create, update,
   unchanged mapped item, or conflict.
4. Print the proposed tracker changes and stop for approval.

Export dry run means Nimbalyst -> MPI JSON task board proposal:

1. Read or receive Nimbalyst tracker/session data.
2. Convert every tracker item to a locked-schema MPI task card, mapping phases
   only into `todo`, `doing`, or `done`.
3. Produce a complete `board.json` and task-folder proposal. The proposal must
   not create legacy lifecycle columns.
4. Compare against existing `board.json`, task files, and `interop.json`
   mappings.
5. Print proposed board changes and stop for approval.

Dry runs never mutate Nimbalyst trackers, `.agents/mpi-kanban/board.json`, task
files, or `id_mappings`.

## ID Mappings

`interop.json` stores mappings instead of adding tracker IDs to task cards:

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

Fingerprints are stable summaries of the relevant fields on each side. They are
used to detect changes since the last sync/export boundary.

MPI fingerprint inputs:

- title
- task ID
- column
- maturity
- status
- description
- plan link

Nimbalyst fingerprint inputs:

- tracker ID
- session ID
- title
- phase
- priority
- tags/labels
- description/notes
- plan file reference

## Conflict Rules

Refuse automatic import/export when:

- Both sides changed since the last recorded boundary.
- A mapping points to a missing MPI task or missing Nimbalyst tracker.
- Two MPI tasks map to one Nimbalyst tracker.
- A Nimbalyst tracker maps to an unsupported MPI column or task-card field.
- A proposed snapshot would remove an MPI task without an explicit matching
  Nimbalyst item or archive instruction.
- A tracker item cannot produce a stable MPI task title.

The sync skill should present conflicts as explicit choices and wait for user
approval before mutating either side.
