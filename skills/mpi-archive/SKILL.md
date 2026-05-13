---
name: mpi-archive
description: Archive entries from the MPI kanban board into rotating archive markdown files. Use when the user says "archive completed kanban entries", "archive completed entries", "archive kanban entry <title>", "archive entry <title>", "/mpi-kanban:mpi-archive", or asks to move old/completed kanban entries out of kanban.md.
---

# mpi-archive Skill

Archive entries out of `.claude/mpi-kanban/kanban.md` into
`.claude/mpi-kanban/archived.md` or the next incrementing archive file.

This skill removes entries from the active board only after preserving their
full entry blocks in an archive file.

## Inputs

- `completed` / `completed kanban entries`: archive every entry under
  `## COMPLETED`.
- A specific entry title: archive the exact matching `### <title>` entry from
  any column.

If the user says only "archive kanban entries" without saying `completed` or
giving a title, ask which entries to archive.

## Checklist

Lib pointers:

- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/archive.md` - archive file selection,
  rotation, and move procedure.
- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/find.md` - `findKanban`.
- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/_schema.md` - column and entry block
  shape.
- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/errors.md` - error wording.

Steps:

1. Read `lib/kanban-ops/archive.md`.
2. Determine the selector:
   - User asked for completed entries -> `completed`.
   - User supplied a title -> `title`.
   - Ambiguous request -> ask a concise clarification before editing.
3. Follow `archiveEntries(selector)` exactly.
4. Final response includes:
   - Number of entries archived.
   - Archive file used.
   - Clickable links to `[kanban.md](.claude/mpi-kanban/kanban.md)` and the
     archive file.

## Hard rules

- Do not bootstrap a missing kanban board. If no board exists, report that
  there is nothing to archive.
- Do not use fuzzy matching for the final archive target. Ask the user to pick
  an exact title if needed.
- Do not edit archived entry contents; preserve each block verbatim.
- Do not archive to a file with more than 200 lines. Use the next incrementing
  archive filename instead.
