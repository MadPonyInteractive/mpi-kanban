---
name: mpi-create-large-plan
description: Create an adaptive, investigation-backed MPI plan for large or uncertain work. Use when the user says "MPI create large plan", "create a large MPI plan", "large plan", "complex plan", "adaptive plan", "multi-phase implementation", "$mpi-create-large-plan", or asks for non-trivial investigation or a parallel-safe plan.
---

# mpi-create-large-plan Skill

## Purpose

Create a large adaptive plan at `docs/plans/YYYY-MM-DD-<slug>.md` and reflect
it on the kanban board. Use this for work with unclear root cause, multiple
subsystems, meaningful risk, or enough moving pieces that a compact plan would
hide important decisions.

Invocation: Claude Code users may run `/mpi-kanban:mpi-create-large-plan`;
Codex users may run `$mpi-create-large-plan` or ask naturally to create a
large MPI plan. References using `${CLAUDE_PLUGIN_ROOT}` mean the installed
plugin root; Codex resolves the same files relative to this plugin root.

Large plans are living documents. They guide work, but `mpi-continue` may
revise the remaining work as implementation reveals new facts.

## Core principles

1. Parallel sub-agents are encouraged during investigation.
2. Implementation is adaptive through `mpi-continue`.
3. Parallel implementation is opt-in only through explicit `## Parallel Batch`
   sections that declare ownership.
4. Every executable task or batch must include a concrete `**Verify:**` line.
5. No forward dependencies inside a task or parallel batch. If verification
   depends on later work, merge the work or move it later.

## Plan shape

Use this structure unless the project has a stronger local convention:

```markdown
# <Goal>

## Current State

What is known now, including relevant files, constraints, and open risks.

## Completed

- [ ] Nothing yet.

## Remaining Work

## Phase 1: <name>

- [ ] <task>. **Verify:** <testable check at this stage>

## Parallel Batch: <name>

- [ ] <task>. Ownership: <files/modules>. Briefings: <rule names or bundle>. **Verify:** <batch-safe check>
- [ ] <task>. Ownership: <files/modules>. Briefings: <rule names or bundle>. **Verify:** <batch-safe check>

## Plan Drift

- None yet.

## Verification

Final end-to-end verification criteria.

## Preservation Notes

Docs, rules, memory, or cleanup items likely to matter before handoff/end-session.
```

Only include `## Parallel Batch` when tasks are genuinely independent and have
disjoint ownership. Otherwise use normal phases.

## Workflow

1. Understand the user's goal or the BACKLOG entry passed by `mpi-brainstorm`.
2. Identify 2-4 investigation areas. Spawn read-only sub-agents where useful.
   Sub-agents write findings to `/tmp/investigation/<area>.md` and never edit
   project files.
3. Synthesize findings into an adaptive plan with `Current State`,
   `Remaining Work`, `Plan Drift`, `Verification`, and `Preservation Notes`.
4. Self-audit:
   - Each task has `**Verify:**`.
   - Parallel batch tasks declare `Ownership:` and do not overlap.
   - No task assumes later work has already happened.
   - The plan says when `mpi-execute-parallel` is appropriate, if at all.
5. Write the plan file to `docs/plans/YYYY-MM-DD-<slug>.md`.
6. Update the kanban board.

## Kanban update

Lib pointers, read only when needed:

- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/find.md` - `findEntry`, `ensureKanban`
- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/mutate.md` - `moveEntry`, `updateEntry`, `createEntry`

If `mpi-brainstorm` passed a BACKLOG title, match that entry. Otherwise ask:

```text
Does this work already have a BACKLOG entry? If yes, what's the title? (or "no" for a fresh PLANNING entry)
```

If a BACKLOG entry matches:

1. `moveEntry(title, "BACKLOG", "PLANNING")`.
2. Replace its tag with `[PLAN]`.
3. Replace its body fence with `Plan file: docs/plans/YYYY-MM-DD-<slug>.md`.

If no entry matches:

1. `ensureKanban()`.
2. Create a PLANNING entry with title, `[PLAN]`, priority (ask, default
   `medium`), `defaultExpanded: true`, and body
   `Plan file: docs/plans/YYYY-MM-DD-<slug>.md`.

Confirm:

```text
Kanban: "<title>" -> PLANNING. [kanban.md](.claude/mpi-kanban/kanban.md)
Next: say "continue this plan" to start, or "create a handoff" if you want a fresh session first.
```

## Hard rules

- Do not execute implementation work.
- Do not add kanban steps yet; `mpi-continue` derives lifecycle/phase steps on
  PLANNING -> IMPLEMENTING.
- Do not create parallel batches without explicit ownership for every task.

## Related invocations

- Codex: `$mpi-create-plan`, `$mpi-continue`, `$mpi-execute-parallel`.
- Claude Code: `/mpi-kanban:mpi-create-plan`,
  `/mpi-kanban:mpi-continue`, `/mpi-kanban:mpi-execute-parallel`.
