---
name: mpi-cleanup
description: Review and clean MPI workflow artifacts such as old plans, handoffs, and archives. Use when the user says cleanup MPI files, garbage collect plans, clean handoffs, archive workflow artifacts, or after ending a completed MPI session.
---

# mpi-cleanup Skill

## Purpose

Conservatively clean workflow artifacts so `docs/plans/`, legacy
`docs/handoffs/`, `.claude/mpi-kanban/`, and eventually
`.agents/mpi-kanban/state/` do not become stale junk drawers.

This skill proposes cleanup first and waits for approval before editing or
deleting anything.

## Classification

Scan:

- `docs/plans/*.md`
- `docs/handoffs/*.json` as legacy compatibility handoffs or pointers
- `.agents/mpi-kanban/state/index.json`
- `.agents/mpi-kanban/state/handoffs/*.json`
- `.claude/mpi-kanban/archived*.md`
- `.claude/mpi-kanban/kanban.md`

Classify artifacts:

- **Active:** referenced by a PLANNING or IMPLEMENTING kanban entry.
- **Completed:** referenced by a COMPLETED kanban entry.
- **Orphaned:** not referenced by any kanban entry or handoff.
- **Superseded handoff:** older handoff for the same active plan when a newer
  handoff exists.
- **Stale:** older than the chosen threshold and not active.

Default stale threshold: 60 days.

## Proposal

Print a cleanup proposal grouped by action:

- keep active,
- archive completed,
- delete superseded handoffs,
- review orphaned,
- leave uncertain.

Ask for approval before any mutation:

```text
Approve this cleanup? Reply "yes" to apply, or tell me what to change.
```

## Actions

Approved cleanup may:

- move completed/orphaned plans and handoffs to `docs/archive/mpi-kanban/`,
- delete superseded handoffs,
- leave active and uncertain files untouched.

Never delete active files. Never delete archives by default.

Phase 1 note: `.agents/mpi-kanban/state/` is the canonical machine state root,
but automated state garbage collection is deferred. For now, classify state
artifacts and propose actions, but do not delete coordination-state files unless
the user explicitly approves those exact paths.

## Final output

Report:

- files kept,
- files archived,
- files deleted,
- files left for manual review.
