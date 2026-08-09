---
name: mpi-cleanup
description: MPI workflow pack - Run MPI cleanup. Review and clean MPI workflow artifacts such as old plans, handoffs, archives, and closed coordination state. Use when the user says "MPI cleanup", "run MPI cleanup", "cleanup MPI files", "garbage collect plans", "clean handoffs", "$mpi-cleanup", or after ending a completed MPI session.
---

# mpi-cleanup Skill

## Purpose

Conservatively clean workflow artifacts so task workspaces, `docs/plans/`,
legacy `docs/handoffs/`, `.agents/mpi-kanban/`, and
`.agents/mpi-kanban/state/` do not become stale junk drawers.

This skill proposes cleanup first and waits for approval before editing or
deleting anything.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Classification

Lib pointers:

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` - JSON board and task workspace
  contract.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md` - `findBoard`, `loadTask`,
  `listTasks`.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/validate.md` - validation checks before
  proposing repairs or archive actions.
Scan:

- `.agents/mpi-kanban/board.json`
- `.agents/mpi-kanban/events.jsonl`
- `.agents/mpi-kanban/tasks/*/task.json`
- `.agents/mpi-kanban/tasks/*/checklist.md`
- `.agents/mpi-kanban/tasks/*/validation.md`
- `.agents/mpi-kanban/tasks/*/handoffs/`
- `docs/plans/*.md`
- `docs/handoffs/*.json` as legacy compatibility handoffs or pointers
- `.agents/mpi-kanban/state/index.json`
- `.agents/mpi-kanban/state/sessions/*.json`
- `.agents/mpi-kanban/state/tasks/*.json`
- `.agents/mpi-kanban/state/files/*.json`
- `.agents/mpi-kanban/state/messages/*.json`
- `.agents/mpi-kanban/state/handoffs/*.json`
- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`
- `.agents/mpi-kanban/archived*.md`
- `.agents/mpi-kanban/kanban.md` as a legacy migration source or snapshot

Classify artifacts:

- **Active task workspace:** referenced by a `todo` or `doing` task card, or by
  active coordination state.
- **Completed task workspace:** referenced by a `done` task card with
  validation represented in `validation.md`.
- **Attention-required task:** task card with `attention.state === "required"`;
  keep and surface before archive/delete proposals.
- **Orphaned:** not referenced by any JSON board column, task workspace,
  coordination record, or handoff.
- **Superseded handoff:** older handoff for the same active plan when a newer
  handoff exists.
- **Stale:** older than the chosen threshold and not active.
- **Active session/task/file claim:** listed in `state/index.json` and not
  closed.
- **Pending file state:** no active writer, but provenance remains for review,
  verification, integration, or final commit summary.
- **Open message:** message listed in `state/index.json` `open_messages` or
  message record with status `open`, `acknowledged`, or `replied`. Keep and
  surface before cleanup decisions; messages are async boundary records, not
  live interruptions.
- **Closed/resolved message:** message record with status `resolved`,
  `superseded`, or `closed`; remove from `open_messages` only after approval
  and preserve or archive according to the proposal.
- **Closed coordination state:** status `closed` or completed records no longer
  referenced by active tasks/handoffs.
- **Stale active coordination task:** a record listed in
  `state/index.json` `active_tasks` that is missing, has status `closed`, or
  names a JSON `task_card` already in `done` while the coordination status is
  resolved (`verified` or `completed`). Keep unresolved done-card records such
  as `needs_review`, `needs_verification`, and `needs_integration` active until
  the pending work is resolved.
- **Active project knowledge:** project profile and knowledge index are
  active by default. Never delete or auto-rewrite. Recommend
  `mpi-project-refresh` when the user wants drift cleaned up.
- **Legacy Markdown board:** `kanban.md` is a migration input or snapshot once
  `board.json` exists. Do not rewrite it as the live board during cleanup.

Default stale threshold: 60 days.

## Proposal

Print a cleanup proposal grouped by action:

- keep active,
- keep open messages,
- keep attention-required tasks,
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
- move approved completed task workspace snapshots out of the active
  `.agents/mpi-kanban/tasks/<id>/` tree only when their `done` state and
  validation notes are preserved and the board/event updates are explicit,
- delete superseded handoffs,
- move closed coordination records to `.agents/mpi-kanban/state/archive/`,
- remove closed records from active `index.json` arrays,
- move approved resolved, superseded, or closed message records to
  `.agents/mpi-kanban/state/archive/messages/` and remove them from
  `open_messages`,
- remove approved stale active coordination task pointers from
  `state/index.json` `active_tasks` while preserving the task record for
  archive or review,
- leave active and uncertain files untouched.

Never delete active task cards, task workspaces, files, or archives by default.
Do not remove a task ID from `board.json` without preserving the task workspace
and appending a board/task event that explains the archive action.

Coordination-state cleanup is conservative. Propose actions first. Do not delete
coordination-state files unless the user explicitly approves those exact paths.
Prefer moving closed state to archive over deletion.

Do not delete or archive open, acknowledged, or replied messages by default.
Cleanup checks messages only at its normal decision boundary; it does not
monitor for live messages while it runs.

Never delete `.agents/mpi-kanban/project-profile.md` or
`.agents/mpi-kanban/project-knowledge-index.md`. They are active project
knowledge. If they appear stale, recommend `mpi-project-refresh`.

## Final output

Report:

- files kept,
- files archived,
- files deleted,
- files left for manual review.




