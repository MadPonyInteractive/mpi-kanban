---
name: mpi-show
description: MPI workflow pack - Read one JSON task-board card and report it, without starting implementation. Use when the user says "what is MPI-5", "show MPI-5", "read MPI-5", "open MPI-5", "what is this card", "look at the <title> card", "describe MPI-42", "$mpi-show", or "/mpi-show". This is the read-only lookup path only - a request to CONTINUE, resume, implement, or move a card goes to mpi-continue, and a request to run the ready cards goes to mpi-execute-parallel.
---

# mpi-show Skill

## Purpose

Answer "what is MPI-5?" from the JSON task board and stop. One card, its direct
task-folder links, a short report, no writes.

This is a separate skill for cost, not for tidiness: a lookup is the cheapest
thing anyone asks of the pack, and it used to load `mpi-continue` whole -
dispatch, verify gates, after-verified steps and hard rules included - to do
four bounded reads. Continuing work still needs all of that; reading a card
does not.

## Routing

Stay here only for a read. Hand off the moment the request is not one:

- continue, resume, keep going, implement, pick this back up -> `mpi-continue`
- move/set/mark a card to `doing`, `validating`, `done` -> `mpi-continue`
  (direct card update mode; it carries the card contract and the mutate
  recipes)
- run the ready cards, dispatch, work the board -> `mpi-execute-parallel`

A lookup that turns into "ok, continue it" is a new request: say you are
switching, then invoke `mpi-continue`.

## Pre-conditions

1. Check for `.agents/mpi-kanban/board.json`.
2. If present, use it. Ignore `.agents/mpi-kanban/kanban.md` except to mention
   that it is legacy/tombstoned if relevant.
3. If `board.json` is absent, stop and tell the user to run `mpi-init`. A
   legacy `.agents/mpi-kanban/kanban.md` is a migration input, not a board to
   read work from.

Resolve `MPI-*` IDs directly from `board.json`. For title lookups, load only
the visible `task.json` files listed by `board.json` and match title
case-insensitively. If multiple title matches exist, list the matching IDs and
ask the user to choose one. If no match exists, report that the task was not
found on the active JSON board. Do not search sibling repos or legacy boards to
"confirm" unless the user explicitly asks.

## Reads

Stay inside `.agents/mpi-kanban/tasks/<id>/` and read direct links only:

1. Required: `task.json`.
2. Summary first: `brief.md`, when present.
3. Current work detail: `plan.md`, then `checklist.md`, when present.
4. Completion evidence: `validation.md`, when present.
5. File context: `files.json`, when present.
6. Recent activity: last 10 lines of `events.jsonl`, when present.
7. Handoffs: list files under `handoffs/` and read only the newest one unless
   the user asks for all.
8. Research: list files under `research/`; read only a named research file or
   the newest one if the task summary depends on it.

A large `plan.md` is the common case on an umbrella card. Read it, but report
from its `## Current State` and `## Remaining Work`; do not replay its phases.

## Report

```text
<ID> - <title>
Column: <todo | doing | done>
Status: <status/maturity/attention summary when available>

Summary:
<brief explanation in plain language>

Linked context read:
- <files read or "task.json only">

Next useful action:
<one sentence, e.g. continue, review validation, archive, or no action obvious>
```

After reporting, stop.

## Hard rules

- Read only. Do not mutate the board, a task card, coordination state, memory,
  docs, or a plan file - not even to tidy something obviously wrong. Report it
  in the `Next useful action` line instead.
- One card per request. Do not walk the board, and do not search sibling
  repositories or unrelated board surfaces.
- No card creation, ever. Discovered work belongs to whichever skill is doing
  the work.
- Do not start implementation, however small the fix looks. That is
  `mpi-continue`, and it needs its own approval gate.
