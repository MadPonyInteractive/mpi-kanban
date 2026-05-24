---
name: mpi-create-large-plan
description: MPI workflow pack - Create an adaptive, investigation-backed MPI plan for large or uncertain work. Use when the user says "MPI create large plan", "create a large MPI plan", "large plan", "complex plan", "adaptive plan", "multi-phase implementation", "$mpi-create-large-plan", or asks for non-trivial investigation or a parallel-safe plan.
---

# mpi-create-large-plan Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Create a large adaptive plan at `docs/plans/YYYY-MM-DD-<slug>.md` and reflect
it on the kanban board. Use this for work with unclear root cause, multiple
subsystems, meaningful risk, or enough moving pieces that a compact plan would
hide important decisions.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

Large plans are living documents. They guide work, but `mpi-continue` may
revise the remaining work as implementation reveals new facts.

## Core principles

1. Default to parallel read-only sub-agents for independent investigation
   areas, not just "where useful." Use a single agent only when investigation
   areas are not independent or the work is trivial.
2. Implementation is adaptive through `mpi-continue`.
3. Default to explicit `## Parallel Batch` sections whenever implementation
   tasks have disjoint, declarable ownership and batch-safe verification.
   Parallel implementation runs only through these sections (executed by
   `mpi-execute-parallel`), but writing them is the default for splittable work,
   not an opt-in extra. When work is large but cannot be split safely, keep
   normal phases and state in the plan why no batch was created.
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

Default to `## Parallel Batch` whenever tasks are genuinely independent and have
disjoint ownership. Use normal phases only when work cannot be split safely,
and note why in the plan.

## Workflow

1. Understand the user's goal or the BACKLOG entry passed by `mpi-brainstorm`.
2. **Load project knowledge if present.** Read
   `.agents/mpi-kanban/project-profile.md` and
   `.agents/mpi-kanban/project-knowledge-index.md` when they exist. Follow
   the context-budget rules in
   `<mpi-lib-root>/project-knowledge/indexing.md`. Brief each
   investigation sub-agent with the profile mode and the relevant topic
   block(s), not the whole project.
3. Identify 2-4 investigation areas. Default to spawning one read-only sub-agent
   per independent area, in parallel. Sub-agents write findings to
   `/tmp/investigation/<area>.md` and never edit project files. Use a single
   agent only when the areas are not independent or the work is trivial.
4. Synthesize findings into an adaptive plan with `Current State`,
   `Remaining Work`, `Plan Drift`, `Verification`, and `Preservation Notes`.
   Include project mode in `## Current State` when the profile exists.
5. Self-audit:
   - Each task has `**Verify:**`.
   - Independent implementation work is in `## Parallel Batch` sections by
     default; if splittable work was left as sequential phases, the plan says
     why.
   - Parallel batch tasks declare `Ownership:` and do not overlap.
   - No task assumes later work has already happened.
   - The plan says when `mpi-execute-parallel` is appropriate, if at all.
6. Write the plan file to `docs/plans/YYYY-MM-DD-<slug>.md`.
7. Update the kanban board.

## Kanban update

Lib pointers, read only when needed:

- `<mpi-lib-root>/kanban-ops/find.md` - `findEntry`, `ensureKanban`
- `<mpi-lib-root>/kanban-ops/mutate.md` - `moveEntry`, `updateEntry`, `createEntry`

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
Kanban: "<title>" -> PLANNING. [kanban.md](.agents/mpi-kanban/kanban.md)
Next: say "continue this plan" to start, or "create a handoff" if you want a fresh session first.
```

## Hard rules

- Do not execute implementation work.
- Do not add kanban steps yet; `mpi-continue` derives lifecycle/phase steps on
  PLANNING -> IMPLEMENTING.
- Do not create parallel batches without explicit ownership for every task.

## Related invocations

- Related skills: `mpi-create-plan`, `mpi-continue`, `mpi-execute-parallel`.




