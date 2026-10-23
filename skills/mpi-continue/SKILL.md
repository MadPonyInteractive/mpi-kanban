---
name: mpi-continue
description: MPI workflow pack - Continue active MPI work, show/read one board task, or update one task-card state. Use when the user says "continue this MPI plan", "MPI continue", "continue", "resume", "keep going", "pick this back up", "read a handoff and continue", "move/update/set MPI-5 to doing/validating/done", "mark the card validating", "run the ready cards", "dispatch ready cards", "work the board", "$mpi-continue", or wants implementation to proceed from an MPI plan/handoff. Board-wide dispatch requests route to mpi-execute-parallel, and a read-only card lookup ("what is MPI-5", "show MPI-5") routes to mpi-show.
---

# mpi-continue Skill

Continue from the card, its plan, the latest handoff, and the workspace as it
really is. Plans are living documents: when reality drifted, fix the plan;
never force the next unchecked item.

Route first. `<here>` is `${CLAUDE_PLUGIN_ROOT}/skills/mpi-continue`; read a
sub-file only when its line applies:

- Read-only lookup ("what is MPI-5?", "show MPI-5") -> invoke `mpi-show` and
  stop; never re-inline the lookup here. "Continue it" afterwards comes back.
- Move or set one card without implementing -> read `<here>/card-update.md`.
- Whole board ("run the ready cards", "work the board"), a `## Parallel Batch`
  as the next unit, or two or more ready cards -> read `<here>/dispatch.md`.
- `state/index.json` shows an open message, stale coordination records, or
  another writer's claim or pending state on a file you need -> read
  `<here>/peers.md`.

Recipes (read the one you call): `beginImplementation`, `moveTask`,
`writeTask`, `appendEvent` in
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/implement.md`;
`findBoard`/`findTask` in `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md`;
checklist shape in `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/plan-ops/derive.md`;
sessions and claims in `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md`,
their status values in `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/statuses.md`.

## Card contract

These are the only legal values. Do not copy them from other cards on the
board; other cards may be wrong.

- `column`: `todo` | `doing` | `done`
- `maturity`:
  - `todo`: `idea` | `planned` | `research` | `needs-decision` | `blocked` | `deferred`
  - `doing`: `in-progress` | `validating`
  - `done`: `complete` | `rejected`
- Coherence: `todo` -> `idea`, `planned`, `research`, `needs-decision`,
  `blocked`, or `deferred`; `doing` -> `in-progress` or `validating`;
  `done` -> `complete` or `rejected`

`research` needs investigation first; `needs-decision` waits on a decision;
`blocked` waits on another card or outside dependency; `deferred` is
deliberately postponed; `rejected` closed unbuilt, kept as the decision record.

Not maturity values: `active`, `accepted`, `done`, `implementing`,
`implementation`, `validated`, `Validated`, `validation`, `spec`, `scoped`,
`designed`, `review`. Process detail goes in `status`, `attention`,
`description`, or workspace files. An invalid or incoherent maturity is fixed by
the same write that changes or confirms the column. Every write goes through a
recipe - never hand-edit a `task.json`. A field this contract does not cover ->
read `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` first.

## Discovered work

Work found while implementing the active card belongs to the active card. That
is the default and needs no approval.

- Same system, same files, or needed for this card's verification -> fold it
  in: a `checklist.md` item, a `plan.md` extension, a `validation.md` note.
- Breaks users or the next release, in any system: small and no other live
  session claims the files -> fix it now; otherwise create a card without
  asking - the only card an agent creates unasked. Either way the close-out
  leads with it.
- Everything else -> one line in the card's `brief.md` under `## Noticed`; the
  close-out prints only the count.
- A card for non-breaking work only when the user asks in the current request:
  `python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/task_ops.py" create
  --title "..." --column todo`. Never hand-write a `task.json`; half of one is
  invisible.

First extend an open `todo`/`doing` card already covering the same system.
Several cards on one system is the failure this prevents; an umbrella
afterwards is a repair, not the goal.

## Start

Source, first match wins: a handoff path (`.agents/mpi-kanban/state/handoffs/<uuid>.json`;
a legacy `docs/handoffs/` pointer -> load the canonical one it names); a card
id; a plan path; a `doing` card with `attention.state === "required"`; a
`doing` card linked to the active plan; without `board.json` only, a legacy
VALIDATING/IMPLEMENTING/PLANNING `kanban.md` entry with a `Plan file:` line.
None -> ask `Which MPI plan or handoff should I continue from? Please paste the path.`

1. The handoff's `task_card.id`, `plan.file`, and workspace links are the
   route. Do not enumerate other tasks or done cards unless those pointers are
   missing, contradictory, or blocked.
2. Read `.agents/mpi-kanban/project-profile.md` and
   `project-knowledge-index.md` if present; load only the topic block matching
   the plan.
3. Read `lifecycle.md`, call `ensureStateRoot()`, and read `state/index.json`
   for blockers only. Register or renew an `implementer` session and create or
   attach a task coordination record for the card and plan.
4. Read the plan; find the card (handoff id, direct id, linked plan, or
   required attention in `doing`).
5. Check the workspace with small commands (`git status`, targeted reads).
6. Orient: done, pending, changed, obsolete, blocked? Ready cards are `todo`,
   `maturity: "planned"`, with a `plan.md`, no required attention - two or more,
   or a batch next -> `dispatch.md` now, unasked, before the brief. Stale plan
   -> fix it first: dated bullet in `## Plan Drift`, update `## Current State`,
   move or rewrite obsolete items. Note docs/rules/memory worth preserving.

## Gate 1 - Continue brief

This is still a stop: print the brief below and wait for the user's go before
implementing.

```text
Next: <one plain sentence: what I will do>
How: <one or two plain sentences: the approach>
Risk: <what could go wrong, or "none">
Heads-up: <plan drift, a peer holding a needed file, an open message>   (only when one exists)
```

## Implementation

The card is in `doing` before any implementation edit, on every entry path:
`beginImplementation(id, actor, planPath, sessionTitle)` moves `todo -> doing`,
sets `in-progress`/`active` and the session, derives the checklist, appends the
events. Never implement a `todo` card in place; never leave `doing` at
`planned` or `implementing`. Always `To do -> Doing -> Done`.

```text
Stop only when you cannot carry on without the user:
- a look-and-feel or product call
- an eye-test
- anything public, sent as the user (email, messages), or that cannot be undone
- anything that costs money: state the price and the number of runs first; the
  yes covers only that, so ask again before going past it
Everything else: take your recommended option and say so in one line.
Questions that can wait go in the close-out's "Your call" line.
```

1. Renew the heartbeat; claim the files before editing them. A file turns out
   claimed by another writer, or has pending state -> `peers.md` before
   touching it.
2. Implement the briefed action within the stated files. Temporary logs come
   out after the user verifies.
3. **Self-verify always**: run the plan's `**Verify:**` / `## Verification`.
   Never commit or push here - that is `mpi-handoff` or `mpi-end-session`.

## Post-implementation gate

Mode: `**Verify mode:**` in `## Verification` (a phase's own value wins);
absent -> `auto`. Print the matching block as-is, nothing around it. Line 1 is
word for word `Nothing breaking` (only when this step's check ran and passed),
`Not checked: <why>`, or `BREAKS USERS: <what>` - never a paraphrase. Add
`Changed from the brief:`, `Left before close:`, `Your call:`, or `Spent:` only
when they apply.

**A. `auto`, passed -> no stop.** Run `## After verified work`, then go on.

```text
<BREAKS USERS: what + "fixed, test added" or "card MPI-n made"> | Nothing breaking
Done: <what landed> - <the check that proved it>
Continuing to the next step.
```

**B. `user-ux`, passed -> stop for the user's eyes.**

```text
<BREAKS USERS: ...> | Nothing breaking (automated checks)
Left before close: your look at it.
Check in the app: <exact, specific steps to look at and feel>
Say "1" if it looks right, or "2" and what to change.
```

**C. Failed or could not run -> stop; lead with the blocker.**

```text
<what failed, or "Not checked"> - <the specific failure, or why it could not run>
I will not mark this verified. Say how to proceed, or "2" to keep talking.
```

"2" or changes after B/C -> skip `## After verified work`, address them, and
append once: `Context getting large? Run mpi-handoff - it commits, pushes, and writes the handoff in about a minute.`

## After verified work

After A, or "1" after B.

1. Remove temporary logs.
2. Update the plan - the running notes `mpi-handoff` reads instead of
   reconstructing; stale costs ten minutes. A few lines: `## Completed`,
   `## Remaining Work`, `## Current State` (where it stands, the one next
   action, any non-obvious gotcha - enough for a zero-memory session), and
   `## Plan Drift` when reality diverged.
3. Complete or release claims (`complete`, `needs_review`,
   `needs_verification`, `needs_integration`, `verified`, `released`) and
   update the coordination task. Released ownership is not commit ownership.
4. Workspace, not `task.json`: tick `checklist.md`, note `validation.md`,
   `writeTask` for badges, append `checklist.updated`/`validation.updated`.
   `done` only once validation is in the workspace and verified - by the user
   for `user-ux`, by passing checks for `auto`.
5. After B with work left -> `Step verified. Say "continue", "handoff", or "end session".`
   Plan complete -> `Plan complete. Run mpi-end-session to close the card.`
