---
name: mpi-nimbalyst-sync
description: MPI workflow pack - Coordinate MPI Kanban and Nimbalyst source-of-truth mode, detection, import/export dry runs, and tracker mapping. Use when user says "MPI Nimbalyst sync", "nimbalyst sync", "detect Nimbalyst", "switch to Nimbalyst mode", "export to Nimbalyst", or "snapshot from Nimbalyst".
---

# mpi-nimbalyst-sync Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find
the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve
as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the
user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Coordinate explicit boundaries between MPI Kanban's Markdown board and
Nimbalyst's native tracker/session workflow.

This skill owns interop mode detection, mode-switch proposals, dry-run import
and export planning, and ID mapping guidance. It must avoid live dual-writing:
in `nimbalyst` mode, Nimbalyst trackers and sessions are canonical and
`.agents/mpi-kanban/kanban.md` is updated only on explicit sync boundaries.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## References

Read only what the command needs:

- `<mpi-lib-root>/interop-ops/modes.md` - source-of-truth mode contract.
- `<mpi-lib-root>/kanban-ops/_schema.md` - MPI board columns and entry shape.
- `<mpi-lib-root>/kanban-ops/find.md` - locate the MPI board.
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
- `import to Nimbalyst` - produce a dry-run plan for converting MPI board
  entries into Nimbalyst tracker items. Do not mutate either system without
  explicit approval.
- `export from Nimbalyst` or `snapshot from Nimbalyst` - produce a dry-run plan
  for writing a schema-valid MPI Markdown board snapshot from Nimbalyst
  trackers/sessions. Do not overwrite `kanban.md` without explicit approval.

If the user asks for an import/export without saying dry run, do the dry run
first and ask for approval before any mutation.

## Detection

Detection is evidence-based. Nimbalyst is detected only when at least one of
these signals is visible:

- MCP tools or connectors whose names clearly indicate Nimbalyst tracker
  operations.
- Session phase support with phases compatible with `backlog`, `planning`,
  `implementing`, `validating`, and `complete`.
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

Switch source of truth to <target>? In file mode, MPI updates .agents/mpi-kanban/kanban.md directly. In nimbalyst mode, Nimbalyst trackers/sessions are canonical and the Markdown board updates only through explicit import/export snapshots.
```

If the user declines, keep the current mode and continue in that mode's rules.

## Import Dry Run: File To Nimbalyst

1. Require or assume `file` mode. If current mode is `nimbalyst`, explain that
   Nimbalyst is already canonical and ask what boundary the user wants.
2. Read the MPI board and parse entries across `BACKLOG`, `PLANNING`,
   `IMPLEMENTING`, `VALIDATING`, and `COMPLETED`.
3. Map each entry using `docs/nimbalyst-interop.md`.
4. Print a summary grouped by target Nimbalyst phase.
5. Identify missing fields, existing ID mappings, and possible conflicts.
6. Ask for approval before creating or updating any Nimbalyst tracker items.

Dry-run output shape:

```text
Nimbalyst import dry run
Source mode: file
Source board: .agents/mpi-kanban/kanban.md
Entries scanned: <n>
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
- create "<title>" -> phase <phase>, priority <priority>, tags <tags>
- update "<title>" / tracker <id> -> <field summary>

Conflicts:
- <conflict summary and choices>
```

Import algorithm:

1. Read `.agents/mpi-kanban/state/interop.json`; if missing, use default
   `file` mode with empty mappings.
2. Refuse live import when `source_of_truth` is `nimbalyst` unless the user
   explicitly asks for a boundary snapshot from file to Nimbalyst.
3. Parse each MPI entry into `{title, column, priority, tags, body,
   plan_file, steps}`. Missing optional fields become `null`; unsupported
   metadata fields are conflicts.
4. Compute an MPI fingerprint for each entry from title, column, priority,
   tags, body text, and plan file. Ignore `defaultExpanded` and checklist state
   unless the target tracker explicitly supports them.
5. Match each entry to an existing mapping by `title + plan_file`, then by
   title alone only when there is no ambiguity.
6. For unmapped entries, propose tracker creation.
7. For mapped entries, compare the current MPI fingerprint with
   `last_mpi_fingerprint`:
   - unchanged -> report no tracker update unless the user requests a resync;
   - changed and Nimbalyst side unchanged -> propose tracker update;
   - changed on both sides -> report conflict.
8. Do not write Nimbalyst trackers or update `id_mappings` during the dry run.

## Export Dry Run: Nimbalyst To File

1. Require Nimbalyst tracker/session data. If unavailable, stop with a clear
   message and keep `file` mode unchanged.
2. Map tracker items to MPI board entries using `docs/nimbalyst-interop.md`.
3. Produce a proposed five-column Markdown snapshot.
4. Compare it against existing `kanban.md` and known `id_mappings`.
5. Ask for approval before writing the board snapshot or changing mode.

Dry-run output shape:

```text
Nimbalyst export dry run
Source mode: nimbalyst
Target board: .agents/mpi-kanban/kanban.md
Trackers scanned: <n>
Board entries proposed: <n>
Creates: <n>
Updates: <n>
Removals from active board: <n>
Conflicts: <n>

Proposed board snapshot:
- BACKLOG: <titles>
- PLANNING: <titles>
- IMPLEMENTING: <titles>
- VALIDATING: <titles>
- COMPLETED: <titles>

Conflicts:
- <conflict summary and choices>
```

Export algorithm:

1. Detect or require visible Nimbalyst tracker/session data. If the current
   agent cannot access it, stop and ask the user to run this from a Nimbalyst
   environment or paste/export the tracker data.
2. Read `.agents/mpi-kanban/state/interop.json`; if missing, assume `file` mode
   with empty mappings but do not switch modes silently.
3. Map each tracker item to `{title, column, priority, tags, body, plan_file}`
   using `docs/nimbalyst-interop.md`.
4. Generate only locked MPI metadata fields: `tags`, `priority`,
   `defaultExpanded`, optional `due`, optional `workload`, and optional
   `steps` when preserving an existing IMPLEMENTING or VALIDATING entry.
5. Preserve an existing MPI entry body and steps when the mapped Nimbalyst item
   has no replacement content for those fields.
6. Compute a Nimbalyst fingerprint for each tracker from title, phase, priority,
   tags, description, plan file, tracker ID, and session reference.
7. Compare tracker fingerprints and MPI fingerprints against `id_mappings`.
8. Produce a complete five-column Markdown proposal but do not write
   `.agents/mpi-kanban/kanban.md` during the dry run.

## Conflict Handling

Refuse silent overwrite when:

- An MPI entry and mapped Nimbalyst tracker both changed since
  `last_sync_at`/`last_export_at`.
- Two MPI entries map to the same tracker ID.
- A tracker phase cannot map to a locked MPI column.
- A proposed board snapshot would introduce unsupported metadata fields.
- A dry-run would remove an MPI entry from the active board without preserving
  it in the proposed snapshot or an explicit archive action.
- A tracker item lacks enough information to form a stable MPI title.

Report conflicts as a short proposal with choices: keep MPI, keep Nimbalyst,
split into new entries, or abort.

Conflict output shape:

```text
Conflict: <title or tracker id>
Reason: <why automatic sync is unsafe>
Choices:
1. keep MPI
2. keep Nimbalyst
3. split into separate entries
4. abort this sync
```

When any conflict exists, do not apply non-conflicting changes in the same run
unless the user explicitly approves a partial sync list.

## Hard Rules

- Do not live-update both systems during normal work.
- Do not add metadata fields to MPI board entries.
- Do not overwrite `kanban.md` without explicit approval.
- Do not switch `source_of_truth` silently.
- Dry run first for import and export.
