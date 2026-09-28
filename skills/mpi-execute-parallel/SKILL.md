---
name: mpi-execute-parallel
description: MPI workflow pack - Execute a parallel batch with worker sub-agents, from a plan's `## Parallel Batch` section or from ready cards on the JSON task board. Use when a plan contains a `## Parallel Batch` section with task ownership, or when the user says "MPI execute parallel", "run a parallel batch", "run the ready cards", "dispatch ready cards", "work the board", "$mpi-execute-parallel", or asks to run a parallel batch or dispatch ready board cards.
---

# mpi-execute-parallel Skill

## Purpose

Run a parallel implementation batch. This skill only applies to explicitly
declared work - a `## Parallel Batch` section in a plan, or ready cards on the
JSON board - and for eligible batches it is the default path: `mpi-continue`
routes valid batches here rather than implementing them sequentially.

The main agent coordinates workers, integrates changes, verifies the batch,
and updates the plan plus JSON task-board state. Workers implement only their
assigned task.

## Batch sources

A batch comes from one of two places:

1. **Plan batch** - a `## Parallel Batch` section inside one card's active
   plan. Splits work *within* one card. See `## Eligibility gate`.
2. **Board batch** - ready cards selected from `.agents/mpi-kanban/board.json`.
   Splits work *across* cards. See `## Board batch source`.

Everything below selection - coordination and message reads, worker briefing,
integration, verification, and card-write rules - applies to both.

Shared coordination lifecycle references:

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/statuses.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md`

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Eligibility gate

This gate covers the plan batch source. For a board batch, read `## Board
batch source` first for selection, then apply the coordination reads and
abort conditions here to the selected cards.

Before spawning workers, read the active plan and find the next incomplete
`## Parallel Batch` section.

Read `.agents/mpi-kanban/state/index.json` through the lifecycle operations.
Register or renew an `orchestrator` session for the main agent and create or
attach the batch coordination task record. If `.agents/mpi-kanban/board.json`
exists, locate the active task card by task ID, plan link, or `doing` task with
`attention.required`; ensure `checklist.md`, `validation.md`, and
`handoffs/` links exist when needed.

At this boundary, read `open_messages` from `state/index.json` targeting the
batch, task, declared ownership, workspace, orchestrator session, agent, role,
or user. Treat `open`, `acknowledged`, and `replied` as unresolved; a relevant
one can block eligibility, require a reply/acknowledgement, change ownership,
or route the batch to an integrator/user decision before workers spawn. Async
boundary check only - no live interruption, remote delivery, broadcast, or
background broker.

Abort and explain why if any task is missing:

- an unchecked `- [ ]` task,
- `Ownership:` with files/modules it may edit,
- `**Verify:**`,
- disjoint ownership from every other task in the batch.

When a task declares no `Ownership:`, infer it by grepping the paths, globs and
modules the task names, and report it as inferred rather than aborting. Abort
only when the footprint is still underivable after that.

If ownership overlaps or a task depends on another task in the same batch,
do not parallelize. Tell the user to use `mpi-continue` instead.

If any declared ownership is already claimed by another fresh active writer,
do not spawn workers for that batch. Reread relevant `open_messages` for the
contested files, owning sessions, task, workspace, agent, or role, then choose
wait, handoff, integration, a message/request record, or user clarification
according to the lifecycle rules.

## Board batch source

Use this when the user asks to run the ready cards, dispatch ready cards, or
work the board, instead of naming a plan batch, and when `mpi-continue` hands
over a set from its `## Autonomous dispatch` evaluation unasked. A handed-over
set is already conflict-checked; re-run the validator and selection anyway,
since that evaluation is read-only and the board may have moved. Requires
`.agents/mpi-kanban/board.json`; no legacy Markdown equivalent.

First, run the board validator with the safe auto-repair:

```text
python ${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/validate_board.py <project-root> --fix
```

`--fix` applies only the safe repairs, then validates, exit 0 on a passing
board - run this, not a plain check: every new session's board is red until
the safe repair runs (the session hook writes the session record but not its
`state/index.json` line), so a plain check stopped "run the ready cards" in
every new session. A board still red after `--fix` stops dispatch as before -
report every violation verbatim. If Python or the script is unavailable, say
so and stop; unlike close-out, dispatch does not proceed without the check.

A card is selectable only when all of these hold:

- it is in the `todo` column,
- its `maturity` is exactly `planned` - not `idea`, `research`,
  `needs-decision`, `blocked`, or `deferred`,
- its task workspace has a `plan.md`,
- it carries no `attention.state: "required"`,
- its ownership is derivable,
- that ownership is disjoint from every other selected card's ownership and
  from every fresh active write claim in `state/index.json`.

Ownership derives from the card's `files.json` when it lists files, otherwise
from `Ownership:` lines in `plan.md`, otherwise by inference: grep the repo
for the paths, globs and modules the plan names. Accept both `files.json`
shapes - a bare `[]` list and the `{"schema": ..., "files": [...]}` object.

Confirm every footprint against the repo before selecting; a declared path
that no longer exists is stale, not ownership. Report each footprint with its
source, marking inferred ones. Never infer silently or from card text, title,
or a diff - only from paths a plan names. A footprint that resolves to
nothing is not selectable; an empty footprint cannot be proven disjoint.

Report the whole selection before spawning any worker - every card the board
offered, with a reason when excluded, e.g. `MPI-31 - owns src/api/**
(files.json, 12 files)` when selected, `MPI-30 - maturity is research, not
planned` when excluded. Never drop a card silently.

Then dispatch without asking. A card carrying a `plan.md` has already been
through a planning conversation and that plan is the approval. The only stops
are a validator failure and an ownership conflict between selected cards.

Each selected card becomes one worker task: its `plan.md` is the task text,
its derived ownership is the ownership, and its plan's `**Verify:**` or
`## Verification` content is the verify instruction. Call `beginImplementation`
from `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` for each
card before its worker edits anything, so no card is implemented while still
in `todo`. That recipe writes ownership into `files.json`; give it the
footprint already resolved, so the next session inherits it.

## Briefing workers

For each task:

1. Resolve its `Briefings:` list or bundle through `mpi-brief-rule` when
   configured.
1b. Pick the worker type. When `.claude/agents/<name>.md` exists for the task's
   bundle or archetype name, spawn with `subagent_type: "<name>"` and skip the
   briefing text that definition already carries. Otherwise spawn a general
   worker and pass the resolved briefing text inline. Never spawn a worker with
   `isolation: "worktree"`: a worktree branches from the default branch, not
   this session's HEAD, and MPI commits only at close-out, so the worker would
   not see it. Workers share one session id, so `guard-claim` cannot help.
2. Spawn one worker with:
   - task text,
   - ownership,
   - verify instruction,
   - relevant rule briefing text,
   - active plan path,
   - active JSON task ID and task workspace path when available,
   - instruction to register/renew its own `implementer` session and claim only
     its owned files before editing,
   - instruction to read relevant `open_messages` at worker startup and before
     contested file claims, treating messages as async boundary records only,
   - instruction not to edit `board.json`, `tasks/<id>/task.json`, task
     workspace files, plan, handoff, rules, or memory unless those paths are
     explicitly in its ownership,
   - warning that other workers may edit the repo and unrelated edits must
     not be reverted,
   - the **Mid-work stops** and **Found work** blocks below, verbatim,
   - a budget only when the orchestrator set one in this briefing: state the
     amount; the worker never spends money without it and never goes past it,
   - the rule in `## Blocked on a file it does not own`.

**Mid-work stops** and **Found work** (verbatim):

```text
Stop only when you cannot carry on without the user:
- a look-and-feel or product call
- an eye-test
- anything public, sent as the user (email, messages), or that cannot be undone
- anything that costs money: state the price and the number of runs first; the
  yes covers only that, so ask again before going past it
Everything else: take your recommended option and say so in one line.
Questions that can wait go in the close-out's "Your call" line.

Breaks users or the next release, in any system:
- small, and no other live session claims those files -> fix it now; first line of the close-out
- otherwise -> first line of the close-out, and create a card for it without asking
  (the only card an agent creates unasked)
Everything else keeps the existing rule; separate work goes to the card's
brief.md under ## Noticed, and the close-out prints only the count.
```

Workers must edit only their owned files/modules and report changed paths.

## Blocked on a file it does not own

A worker needing a file outside its ownership does not edit it or negotiate;
it files one `mpi-message`, then stops that line of work:

- `to`: `{ "selector": "file", "value": "<the exact path it needed>" }`
- `related`: its own `task_card`, the owning card as `task_card` when known,
  the coordination `task` for the batch, and the file under `files`
- `subject`: one line, the file and why it was needed
- `body`: what it needed the file for and what it did instead

It reports the stop, finishes its remaining owned work, and does not wait for
a reply - the bus is async, with no live delivery or read receipt.

The orchestrator surfaces these messages at integration (step 1 of
`## Main-agent responsibilities`) and decides there: widen ownership and rerun,
make the edit itself as `integrator`, or leave it for a follow-up card.

This is the only worker-to-worker messaging case in this skill.

## Main-agent responsibilities

While workers run, do non-overlapping integration prep if useful. After workers
finish:

1. Reread `state/index.json` and relevant `open_messages` for the batch,
   workers, claimed files, task, workspace, agent, role, or user; handle
   unresolved messages before mutating plan or task-board state.
2. Review changed files for conflicts or ownership violations.
3. Mark worker file claims `complete`, `needs_review`, `needs_verification`,
   or `needs_integration` per the returned result.
4. Integrate results. If same-file or cross-worker reconciliation is required,
   claim the affected files as `integrator` before editing them.
5. Run the batch verification.
6. Report in Close-out order: the breaker line first (`BREAKS USERS: <what>` |
   `Nothing breaking`, only when the batch verification ran and passed and
   nothing found breaks users or the next release | `Not checked: <why>`),
   `Changed from the brief` (only if any), `Left before close`, `Your call`
   lines with picks, `Done` with proof, `Spent: <amount> of <approved>` (only
   when money was spent), and the notes count. Then `mpi-continue`'s gate:
   `auto` and passed continues; `user-ux` or a failed check stops.
7. Once that gate passes, mark the batch tasks complete in the plan, update the
   active task workspace checklist/validation files, append
   `checklist.updated` or `validation.updated` events when meaningful, and use
   `moveTask` / `writeTask` from `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` for
   any card status, maturity, or column change. Never write invented maturity
   values: `active`, `accepted`, `done`, `implementing`, `implementation`,
   `validated`, `Validated`, `validation`, and `spec` are not maturities. The
   only allowed values are `idea`, `planned`, `research`, `needs-decision`,
   `blocked`, `deferred`, `in-progress`, `validating`, `complete`, and
   `rejected`, matched to the card column. Move the card to `done` only after
   validation state is represented. For unmigrated legacy projects, update the
   relevant kanban step as compatibility behavior.

## Hard rules

- Parallelize whenever footprints are provably disjoint and each unit is
  independently verifiable, whatever produced the plan; an overlapping or
  underivable footprint disqualifies work, not the plan's shape.
- Infer ownership by grepping the paths the plan names when it declares none,
  and report every inferred footprint as inferred. Never infer silently, and
  never infer from card text, title, or a diff.
- Never dispatch a board batch without a passing `validate_board.py --fix`
  run, and never select a card that has no `plan.md`.
- Card-write preflight is mandatory before any `column`, `maturity`, or
  `status` write: read `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` and
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md`. Do not derive legal values from
  existing cards.
- Never let workers edit the plan, JSON board, task workspace, legacy kanban,
  handoff, rules, or memory files unless that path is explicitly their
  ownership and the task is about those files.
- Never treat file-claim completion as commit permission. Commit ownership
  belongs to `mpi-end-session` or an explicit integrator.
- No commits or pushes.

