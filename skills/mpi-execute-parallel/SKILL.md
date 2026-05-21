---
name: mpi-execute-parallel
description: Execute an explicit parallel batch from an MPI large plan using worker sub-agents. Use only when a plan contains a `## Parallel Batch` section with task ownership, or when the user says "MPI execute parallel", "run a parallel batch", "$mpi-execute-parallel", or asks to run a parallel batch.
---

# mpi-execute-parallel Skill

## Purpose

Run a parallel implementation batch from an MPI large plan. This skill is
opt-in and only applies to explicit `## Parallel Batch` sections.

The main agent coordinates workers, integrates changes, verifies the batch,
and updates the plan/kanban. Workers implement only their assigned task.

Shared coordination lifecycle references:

- `${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/lifecycle.md`
- `${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/statuses.md`

Invocation: Claude Code users may run `/mpi-kanban:mpi-execute-parallel`;
Codex users may run `$mpi-execute-parallel` or ask naturally to run an MPI
parallel batch. References using `${CLAUDE_PLUGIN_ROOT}` mean the installed
plugin root; Codex resolves the same files relative to this plugin root.

## Eligibility gate

Before spawning workers, read the active plan and find the next incomplete
`## Parallel Batch` section.

Read `.agents/mpi-kanban/state/index.json` through the lifecycle operations.
Register or renew an `orchestrator` session for the main agent and create or
attach the batch task record.

Abort and explain why if any task is missing:

- an unchecked `- [ ]` task,
- `Ownership:` with files/modules it may edit,
- `**Verify:**`,
- disjoint ownership from every other task in the batch.

If ownership overlaps or a task depends on another task in the same batch,
do not parallelize. Tell the user to use `mpi-continue` instead.

If any declared ownership is already claimed by another fresh active writer,
do not spawn workers for that batch. Choose wait, handoff, integration, or user
clarification according to the lifecycle rules.

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
   - instruction to register/renew its own `implementer` session and claim only
     its owned files before editing,
   - warning that other workers may edit the repo and unrelated edits must
     not be reverted.

Workers must edit only their owned files/modules and report changed paths.

## Main-agent responsibilities

While workers run, do non-overlapping integration prep if useful. After workers
finish:

1. Review changed files for conflicts or ownership violations.
2. Mark worker file claims `complete`, `needs_review`,
   `needs_verification`, or `needs_integration` according to the returned
   result.
3. Integrate results. If same-file or cross-worker reconciliation is required,
   claim the affected files as `integrator` before editing them.
4. Run the batch verification.
5. Present the same post-implementation gate used by `mpi-continue`.
6. After user verifies, mark the batch tasks complete in the plan and update
   the relevant kanban step.

## Hard rules

- Never parallelize a normal phase or compact plan.
- Never infer ownership when the plan omitted it.
- Never let workers edit the plan, kanban, handoff, rules, or memory files
  unless that path is explicitly their ownership and the task is about those
  files.
- Never treat file-claim completion as commit permission. Commit ownership
  belongs to `mpi-end-session` or an explicit integrator.
- No commits or pushes.
