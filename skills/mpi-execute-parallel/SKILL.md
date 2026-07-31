---
name: mpi-execute-parallel
description: MPI workflow pack - Execute an explicit parallel batch from an MPI large plan using worker sub-agents. Use only when a plan contains a `## Parallel Batch` section with task ownership, or when the user says "MPI execute parallel", "run a parallel batch", "$mpi-execute-parallel", or asks to run a parallel batch.
---

# mpi-execute-parallel Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Run a parallel implementation batch from an MPI large plan. This skill only
applies to explicit `## Parallel Batch` sections, and for eligible batches it is
the default execution path - `mpi-continue` routes valid batches here rather
than implementing them sequentially. "Only explicit batches" is a safety scope,
not a discouragement: when a batch passes the eligibility gate below, running it
in parallel is the expected default.

The main agent coordinates workers, integrates changes, verifies the batch,
and updates the plan plus JSON task-board state. Workers implement only their
assigned task.

Shared coordination lifecycle references:

- `<mpi-lib-root>/coordination-ops/lifecycle.md`
- `<mpi-lib-root>/coordination-ops/statuses.md`
- `<mpi-lib-root>/task-board-ops/_schema.md`
- `<mpi-lib-root>/task-board-ops/read.md`
- `<mpi-lib-root>/task-board-ops/mutate.md`

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Eligibility gate

Before spawning workers, read the active plan and find the next incomplete
`## Parallel Batch` section.

Read `.agents/mpi-kanban/state/index.json` through the lifecycle operations.
Register or renew an `orchestrator` session for the main agent and create or
attach the batch coordination task record. If `.agents/mpi-kanban/board.json`
exists, locate the active task card by task ID, plan link, or `doing` task with
`attention.required`; ensure `checklist.md`, `validation.md`, and
`handoffs/` links exist when needed. If `board.json` is absent, legacy
`kanban.md` references are compatibility context only.

At this parallel execution boundary, read any `open_messages` records pointed
to by `state/index.json` when they target the active batch, task, declared
ownership, workspace, orchestrator session, agent, role, or user. Treat
`open`, `acknowledged`, and `replied` as unresolved. A relevant unresolved
message can block eligibility, require a reply/acknowledgement, change
ownership, or route the batch to an integrator/user decision before workers are
spawned. This is an async boundary check only; do not promise live
interruption, remote delivery, global broadcast, or a background broker.

Abort and explain why if any task is missing:

- an unchecked `- [ ]` task,
- `Ownership:` with files/modules it may edit,
- `**Verify:**`,
- disjoint ownership from every other task in the batch.

If ownership overlaps or a task depends on another task in the same batch,
do not parallelize. Tell the user to use `mpi-continue` instead.

If any declared ownership is already claimed by another fresh active writer,
do not spawn workers for that batch. Reread relevant `open_messages` for the
contested files, owning sessions, task, workspace, agent, or role, then choose
wait, handoff, integration, a message/request record, or user clarification
according to the lifecycle rules.

## Briefing workers

For each task:

1. Resolve its `Briefings:` list or bundle through `mpi-brief-rule` when
   configured.
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
     not be reverted.

Workers must edit only their owned files/modules and report changed paths.

## Main-agent responsibilities

While workers run, do non-overlapping integration prep if useful. After workers
finish:

1. Reread `state/index.json` and relevant `open_messages` for the batch,
   workers, claimed files, task, workspace, agent, role, or user before
   integration decisions. Handle unresolved messages before mutating plan or
   task-board state.
2. Review changed files for conflicts or ownership violations.
3. Mark worker file claims `complete`, `needs_review`,
   `needs_verification`, or `needs_integration` according to the returned
   result.
4. Integrate results. If same-file or cross-worker reconciliation is required,
   claim the affected files as `integrator` before editing them.
5. Run the batch verification.
6. Present the same post-implementation gate used by `mpi-continue`.
7. After user verifies, mark the batch tasks complete in the plan, update the
   active task workspace checklist/validation files, append
   `checklist.updated` or `validation.updated` events when meaningful, and use
   `moveTask` / `writeTask` from `<mpi-lib-root>/task-board-ops/mutate.md` for
   any card status, maturity, or column change. Never write invented maturity
   values such as `Validated`, `spec`, `implementing`, or `done`; the only
   allowed values are `idea`, `planned`, `research`, `needs-decision`,
   `blocked`, `deferred`, `in-progress`, `validating`, `complete`, and
   `rejected`, matched to the card column. Move the card to `done` only after
   validation state is represented. For unmigrated legacy projects, update the
   relevant kanban step as compatibility behavior.

## Hard rules

- Never parallelize a normal phase or compact plan.
- Never infer ownership when the plan omitted it.
- Card-write preflight is mandatory before any `column`, `maturity`, or
  `status` write: read `<mpi-lib-root>/task-board-ops/_schema.md` and
  `<mpi-lib-root>/task-board-ops/mutate.md`. Do not derive legal values from
  existing cards.
- Never let workers edit the plan, JSON board, task workspace, legacy kanban,
  handoff, rules, or memory files unless that path is explicitly their
  ownership and the task is about those files.
- Never treat file-claim completion as commit permission. Commit ownership
  belongs to `mpi-end-session` or an explicit integrator.
- No commits or pushes.



