---
name: mpi-archive
description: MPI workflow pack - Archive entries from the MPI kanban board into rotating archive markdown files. Use when the user says "MPI archive", "archive completed kanban entries", "archive completed entries", "archive kanban entry <title>", "archive entry <title>", "$mpi-archive", or "/mpi-archive".
---

# mpi-archive Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`
Archive entries out of `.agents/mpi-kanban/kanban.md` into
`.agents/mpi-kanban/archived.md` or the next incrementing archive file.

This skill removes entries from the active board only after preserving their
full entry blocks in an archive file.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Inputs

- `completed` / `completed kanban entries`: archive every entry under
  `## COMPLETED`.
- A specific entry title: archive the exact matching `### <title>` entry from
  any column.

If the user says only "archive kanban entries" without saying `completed` or
giving a title, ask which entries to archive.

## Checklist

Lib pointers:

- `<mpi-lib-root>/kanban-ops/archive.md` - archive file selection,
  rotation, and move procedure.
- `<mpi-lib-root>/kanban-ops/find.md` - `findKanban`.
- `<mpi-lib-root>/kanban-ops/_schema.md` - column and entry block
  shape.
- `<mpi-lib-root>/kanban-ops/errors.md` - error wording.

Steps:

1. Read `<mpi-lib-root>/kanban-ops/archive.md`.
2. Determine the selector:
   - User asked for completed entries -> `completed`.
   - User supplied a title -> `title`.
   - Ambiguous request -> ask a concise clarification before editing.
3. Follow `archiveEntries(selector)` exactly.
4. Final response includes:
   - Number of entries archived.
   - Archive file used.
   - Clickable links to `[kanban.md](.agents/mpi-kanban/kanban.md)` and the
     archive file.

## Hard rules

- Do not bootstrap a missing kanban board. If no board exists, report that
  there is nothing to archive.
- Do not use fuzzy matching for the final archive target. Ask the user to pick
  an exact title if needed.
- Do not edit archived entry contents; preserve each block verbatim.
- Do not archive to a file with more than 200 lines. Use the next incrementing
  archive filename instead.




