---
name: mpi-nimbalyst-sync
description: MPI workflow pack - Coordinate MPI Kanban and Nimbalyst source-of-truth mode, detection, import/export dry runs, and tracker mapping. Use when user says "MPI Nimbalyst sync", "nimbalyst sync", "detect Nimbalyst", "switch to Nimbalyst mode", "export to Nimbalyst", or "snapshot from Nimbalyst".
---

# mpi-nimbalyst-sync Skill

## Purpose

Coordinate explicit boundaries between MPI Kanban's JSON task board and
Nimbalyst's native tracker/session workflow.

This skill owns interop mode detection, mode-switch proposals, dry-run import
and export planning, and ID mapping guidance. It must avoid live dual-writing:
in `nimbalyst` mode, Nimbalyst trackers and sessions are canonical and
`.agents/mpi-kanban/board.json` plus task folders are updated only on explicit
sync boundaries. In `file` mode, `.agents/mpi-kanban/board.json` and
`.agents/mpi-kanban/tasks/<id>/` are canonical; legacy `kanban.md` files are
migration or compatibility snapshots once the JSON board exists.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## References

Read only what the command needs:

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/interop-ops/modes.md` - source-of-truth mode contract.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` - JSON task board columns and
  task-card shape.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/kanban-ops/_schema.md` - legacy Markdown board shape for
  migration and snapshots.
- `docs/nimbalyst-interop.md` - Nimbalyst detection and tracker mapping design.

## Commands

Supported natural commands:

- `detect` - inspect whether Nimbalyst tracker/session capabilities appear to
  be available, then update or propose `state/interop.json` environment fields.
- `status` - report current `source_of_truth`, detected environment, last
  sync/export timestamps, and mapping count.
- `switch to file mode` - propose changing `source_of_truth` to `file`.
- `switch to nimbalyst mode` - propose changing `source_of_truth` to
  `nimbalyst` only when Nimbalyst capabilities are detected or the user
  explicitly confirms.
- `import to Nimbalyst` - produce a dry-run plan for converting MPI task-board
  cards into Nimbalyst tracker items. Do not mutate either system without
  explicit approval.
- `export from Nimbalyst` or `snapshot from Nimbalyst` - produce a dry-run plan
  for writing a schema-valid MPI JSON board proposal from Nimbalyst
  trackers/sessions. The proposal uses only `todo`, `doing`, and `done`
  columns. Do not overwrite `board.json` or task files without explicit
  approval.

If the user asks for an import/export without saying dry run, do the dry run
first and ask for approval before any mutation.

## Detection

Detection is evidence-based. Nimbalyst is detected only when at least one of
these signals is visible:

- MCP tools or connectors whose names clearly indicate Nimbalyst tracker
  operations.
- Session phase support with phases compatible with `backlog`, `planning`,
  `implementing`, `validating`, and `complete`. Treat these as Nimbalyst
  phases that map to MPI task-card state, not as MPI board columns.
- Project instructions explicitly naming Nimbalyst trackers as canonical.

If no signal is visible, record or report `generic` and keep `file` mode.
If signals conflict, record or report `unknown` and ask before switching modes.

## Mode Switching

Before changing `source_of_truth`:

1. Read `.agents/mpi-kanban/state/interop.json`; if missing, assume `file`.
2. Run or summarize detection.
3. Show the current mode, detected environment, and consequence of the change.
4. Ask for explicit approval.
5. On approval, update `source_of_truth`, `updated_at`, and
   `last_detected_environment`.

Never switch modes silently because a detected environment changed.

Use this prompt when detected environment and stored mode differ:

```text
Detected environment: <generic | nimbalyst | unknown>
Current MPI source of truth: <file | nimbalyst>

Switch source of truth to <target>? In file mode, MPI updates .agents/mpi-kanban/board.json, task folders, and event logs directly. In nimbalyst mode, Nimbalyst trackers/sessions are canonical and MPI board snapshots update only through explicit import/export snapshots.
```

If the user declines, keep the current mode and continue in that mode's rules.

## Import Dry Run: File To Nimbalyst

1. Require or assume `file` mode. If current mode is `nimbalyst`, explain that
   Nimbalyst is already canonical and ask what boundary the user wants.
2. Read `.agents/mpi-kanban/board.json` and visible
   `.agents/mpi-kanban/tasks/<id>/task.json` files.
3. Map each entry using `docs/nimbalyst-interop.md`, deriving Nimbalyst phases
   from `todo` / `doing` / `done` plus `maturity`, `status`, checklist, and
   validation links.
4. Print a summary grouped by target Nimbalyst phase.
5. Identify missing fields, existing ID mappings, and possible conflicts.
6. Ask for approval before creating or updating any Nimbalyst tracker items.

Dry-run output shape:

```text
Nimbalyst import dry run
Source mode: file
Source board: .agents/mpi-kanban/board.json
Tasks scanned: <n>
Creates: <n>
Updates: <n>
Unchanged mapped items: <n>
Conflicts: <n>

By phase:
- backlog: <titles>
- planning: <titles>
- implementing: <titles>
- validating: <titles>
- complete: <titles>

Proposed tracker changes:
- create "<title>" -> phase <phase>, badges <maturity>/<status>
- update "<title>" / tracker <id> -> <field summary>

Conflicts:
- <conflict summary and choices>
```

Import algorithm:

1. Read `.agents/mpi-kanban/state/interop.json`; if missing, use default
   `file` mode with empty mappings.
2. Refuse live import when `source_of_truth` is `nimbalyst` unless the user
   explicitly asks for a boundary snapshot from file to Nimbalyst.
3. Parse each MPI task into `{id, title, column, maturity, status,
   description, plan_link}`. `column` must be one of `todo`, `doing`, or
   `done`. Missing optional fields become `null`; unsupported task-card fields
   are conflicts.
4. Compute an MPI fingerprint for each task from ID, title, column, maturity,
   status, description, and plan link.
5. Match each task to an existing mapping by task ID first, then by
   `title + plan_link` only when there is no ambiguity.
6. For unmapped tasks, propose tracker creation.
7. For mapped tasks, compare the current MPI fingerprint with
   `last_mpi_fingerprint`:
   - unchanged -> report no tracker update unless the user requests a resync;
   - changed and Nimbalyst side unchanged -> propose tracker update;
   - changed on both sides -> report conflict.
8. Do not write Nimbalyst trackers or update `id_mappings` during the dry run.

## Export Dry Run: Nimbalyst To File

1. Require Nimbalyst tracker/session data. If unavailable, stop with a clear
   message and keep `file` mode unchanged.
2. Map tracker items to MPI task cards using `docs/nimbalyst-interop.md`.
   Nimbalyst phases must collapse into locked MPI columns: `backlog` and
   `planning` -> `todo`, `implementing` and `validating` -> `doing`,
   `complete` -> `done`.
3. Produce a proposed `board.json` and task-folder snapshot.
4. Compare it against existing `board.json`, task files, and known
   `id_mappings`.
5. Ask for approval before writing the board snapshot or changing mode.

Dry-run output shape:

```text
Nimbalyst export dry run
Source mode: nimbalyst
Target board: .agents/mpi-kanban/board.json
Trackers scanned: <n>
Board tasks proposed: <n>
Creates: <n>
Updates: <n>
Removals from active board: <n>
Conflicts: <n>

Proposed board snapshot:
- todo: <task IDs and titles>
- doing: <task IDs and titles>
- done: <task IDs and titles>

Conflicts:
- <conflict summary and choices>
```

Export algorithm:

1. Detect or require visible Nimbalyst tracker/session data. If the current
   agent cannot access it, stop and ask the user to run this from a Nimbalyst
   environment or paste/export the tracker data.
2. Read `.agents/mpi-kanban/state/interop.json`; if missing, assume `file` mode
   with empty mappings but do not switch modes silently.
3. Map each tracker item to `{id, title, column, maturity, status,
   description, plan_link}`
   using `docs/nimbalyst-interop.md`.
4. Generate only locked MPI task-card fields and linked task workspace files.
   Keep tracker IDs, session IDs, sync timestamps, and fingerprints in
   `state/interop.json` `id_mappings`, not in task cards.
5. Preserve existing task workspace files when the mapped Nimbalyst item has no
   replacement content for those fields.
6. Compute a Nimbalyst fingerprint for each tracker from title, phase, priority,
   tags, description, plan file, tracker ID, and session reference.
7. Compare tracker fingerprints and MPI fingerprints against `id_mappings`.
8. Produce a complete JSON board proposal but do not write
   `.agents/mpi-kanban/board.json` or task files during the dry run.

## Conflict Handling

Refuse silent overwrite when:

- An MPI task and mapped Nimbalyst tracker both changed since
  `last_sync_at`/`last_export_at`.
- Two MPI tasks map to the same tracker ID.
- A tracker phase cannot map to a locked MPI column.
- A proposed board snapshot would introduce unsupported task-card fields.
- A proposed board snapshot would recreate legacy lifecycle columns instead of
  `todo`, `doing`, and `done`.
- A dry-run would remove an MPI task from the active board without preserving
  it in the proposed snapshot or an explicit archive action.
- A tracker item lacks enough information to form a stable MPI task title.

Report conflicts as a short proposal with choices: keep MPI, keep Nimbalyst,
split into new tasks, or abort.

Conflict output shape:

```text
Conflict: <title or tracker id>
Reason: <why automatic sync is unsafe>
Choices:
1. keep MPI
2. keep Nimbalyst
3. split into separate tasks
4. abort this sync
```

When any conflict exists, do not apply non-conflicting changes in the same run
unless the user explicitly approves a partial sync list.

## Hard Rules

- Do not live-update both systems during normal work.
- Do not add fields to MPI task cards outside the SPEC contract.
- Do not put Nimbalyst tracker IDs, session IDs, fingerprints, or sync metadata
  in task-card fields.
- Do not restore legacy MPI lifecycle columns as live JSON-board columns.
- Do not overwrite `board.json` or task files without explicit approval.
- Do not switch `source_of_truth` silently.
- Dry run first for import and export.
