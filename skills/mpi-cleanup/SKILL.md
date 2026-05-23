---
name: mpi-cleanup
description: Run MPI cleanup. Review and clean MPI workflow artifacts such as old plans, handoffs, archives, and closed coordination state. Use when the user says "MPI cleanup", "run MPI cleanup", "cleanup MPI files", "garbage collect plans", "clean handoffs", "$mpi-cleanup", or after ending a completed MPI session.
---

# mpi-cleanup Skill

## Purpose

Conservatively clean workflow artifacts so `docs/plans/`, legacy
`docs/handoffs/`, `.claude/mpi-kanban/`, and eventually
`.agents/mpi-kanban/state/` do not become stale junk drawers.

This skill proposes cleanup first and waits for approval before editing or
deleting anything.

Invocation: Claude Code users may run `/mpi-kanban:mpi-cleanup`; Codex users
may run `$mpi-cleanup` or ask naturally to run MPI cleanup.

## Classification

Scan:

- `docs/plans/*.md`
- `docs/handoffs/*.json` as legacy compatibility handoffs or pointers
- `.agents/mpi-kanban/state/index.json`
- `.agents/mpi-kanban/state/sessions/*.json`
- `.agents/mpi-kanban/state/tasks/*.json`
- `.agents/mpi-kanban/state/files/*.json`
- `.agents/mpi-kanban/state/handoffs/*.json`
- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`
- `.claude/mpi-kanban/archived*.md`
- `.claude/mpi-kanban/kanban.md`

Classify artifacts:

- **Active:** referenced by a PLANNING or IMPLEMENTING kanban entry.
- **Completed:** referenced by a COMPLETED kanban entry.
- **Orphaned:** not referenced by any kanban entry or handoff.
- **Superseded handoff:** older handoff for the same active plan when a newer
  handoff exists.
- **Stale:** older than the chosen threshold and not active.
- **Active session/task/file claim:** listed in `state/index.json` and not
  closed.
- **Pending file state:** no active writer, but provenance remains for review,
  verification, integration, or final commit summary.
- **Closed coordination state:** status `closed` or completed records no longer
  referenced by active tasks/handoffs.
- **Active project knowledge:** project profile and knowledge index are
  active by default. Never delete or auto-rewrite. Recommend
  `mpi-project-refresh` when the user wants drift cleaned up.

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
- move closed coordination records to `.agents/mpi-kanban/state/archive/`,
- remove closed records from active `index.json` arrays,
- leave active and uncertain files untouched.

Never delete active files. Never delete archives by default.

Coordination-state cleanup is conservative. Propose actions first. Do not delete
coordination-state files unless the user explicitly approves those exact paths.
Prefer moving closed state to archive over deletion.

Never delete `.agents/mpi-kanban/project-profile.md` or
`.agents/mpi-kanban/project-knowledge-index.md`. They are active project
knowledge. If they appear stale, recommend `mpi-project-refresh`.

## Final output

Report:

- files kept,
- files archived,
- files deleted,
- files left for manual review.
