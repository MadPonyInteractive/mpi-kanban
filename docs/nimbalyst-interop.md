# Nimbalyst Interop

This document defines the first stable mapping between MPI Kanban entries and
Nimbalyst tracker/session state. It is a design contract for
`mpi-nimbalyst-sync` import/export dry runs and future concrete tracker
mutations.

## Source Of Truth

MPI records the active source of truth in:

```text
.agents/mpi-kanban/state/interop.json
```

Modes:

- `file` - MPI Markdown board is canonical.
- `nimbalyst` - Nimbalyst tracker items and session phase are canonical.

In `nimbalyst` mode, agents must not update both Nimbalyst trackers and
`.agents/mpi-kanban/kanban.md` during normal work. Board updates are explicit
import/export snapshots.

## Environment Detection

Nimbalyst availability is detected from visible capability signals:

- MCP tools or connectors whose names clearly expose Nimbalyst tracker
  operations.
- Session phase support compatible with `backlog`, `planning`, `implementing`,
  `validating`, and `complete`.
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
- MPI workflow skills update `.agents/mpi-kanban/kanban.md` directly.
- The VS Code extension renders the Markdown board as the visible work board.
- `mpi-nimbalyst-sync detect` should report `generic` unless Nimbalyst-specific
  capabilities are visible.

In Nimbalyst:

- Recommended mode is `nimbalyst` after explicit user approval.
- Nimbalyst trackers and session phase are canonical during normal work.
- MPI workflow skills must not live-update `kanban.md`.
- Use `mpi-nimbalyst-sync import to Nimbalyst` or
  `mpi-nimbalyst-sync export from Nimbalyst` for explicit boundary snapshots.

Mode mismatch prompt:

```text
Detected environment: <generic | nimbalyst | unknown>
Current MPI source of truth: <file | nimbalyst>

Switch source of truth to <target>? In file mode, MPI updates .agents/mpi-kanban/kanban.md directly. In nimbalyst mode, Nimbalyst trackers/sessions are canonical and the Markdown board updates only through explicit import/export snapshots.
```

## Phase Mapping

| MPI column | Nimbalyst phase |
|---|---|
| `BACKLOG` | `backlog` |
| `PLANNING` | `planning` |
| `IMPLEMENTING` | `implementing` |
| `VALIDATING` | `validating` |
| `COMPLETED` | `complete` |

Unknown Nimbalyst phases are conflicts. Do not invent new MPI columns.

## Field Mapping

| MPI field | Nimbalyst field |
|---|---|
| H3 title | tracker title |
| Column | phase |
| `priority` | priority |
| `tags` | labels/tags |
| body fence text | description/notes |
| `Plan file: <path>` body line | plan file reference |
| board path | source board reference |
| interop `tracker_id` | tracker item ID |
| interop `session_id` | Nimbalyst session reference |

MPI-only fields such as `defaultExpanded` and `steps` are not Nimbalyst source
fields. Preserve them when exporting a board snapshot if existing MPI state
already has them.

## Dry-Run Operations

Import dry run means MPI Markdown -> Nimbalyst proposal:

1. Parse all five MPI columns.
2. Convert each entry to the phase and field mapping above.
3. Use `interop.json` mappings to decide whether each item is a create, update,
   unchanged mapped item, or conflict.
4. Print the proposed tracker changes and stop for approval.

Export dry run means Nimbalyst -> MPI Markdown proposal:

1. Read or receive Nimbalyst tracker/session data.
2. Convert every tracker item to a locked-schema MPI entry.
3. Produce a complete five-column Markdown snapshot.
4. Compare against existing `kanban.md` and `interop.json` mappings.
5. Print proposed board changes and stop for approval.

Dry runs never mutate Nimbalyst trackers, `.agents/mpi-kanban/kanban.md`, or
`id_mappings`.

## ID Mappings

`interop.json` stores mappings instead of adding card metadata:

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

Fingerprints are stable summaries of the relevant fields on each side. They are
used to detect changes since the last sync/export boundary.

MPI fingerprint inputs:

- title
- column
- priority
- tags
- body text
- plan file

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
- A mapping points to a missing MPI entry or missing Nimbalyst tracker.
- Two MPI entries map to one Nimbalyst tracker.
- A Nimbalyst tracker maps to an unsupported MPI column or metadata field.
- A proposed snapshot would remove an MPI entry without an explicit matching
  Nimbalyst item or archive instruction.
- A tracker item cannot produce a stable MPI title.

The sync skill should present conflicts as explicit choices and wait for user
approval before mutating either side.
