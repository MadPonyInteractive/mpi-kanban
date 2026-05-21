---
name: mpi-create-plan
description: Create a compact/default MPI plan for normal work. Use when the user says "MPI create plan", "create an MPI plan", "create a plan", "make a plan", "plan this", "$mpi-create-plan", or after brainstorming when the task can be implemented as one coherent flow with final verification.
---

# mpi-create-plan Skill

## Purpose

Create a compact plan at `docs/plans/YYYY-MM-DD-<slug>.md` and reflect it on
the kanban board. This is the default planning path for normal work.

Invocation: Claude Code users may run `/mpi-kanban:mpi-create-plan`; Codex
users may run `$mpi-create-plan` or ask naturally to create an MPI plan.
References using `${CLAUDE_PLUGIN_ROOT}` mean the installed plugin root; Codex
resolves the same files relative to this plugin root.

Use `mpi-create-large-plan` instead when the work needs investigation,
multiple phases, explicit parallel batches, or complex risk management.

## Plan shape

```markdown
# <Goal>

## Current State

Brief facts known at planning time.

## Implementation

- [ ] Implement the planned change end to end. **Verify:** <final verification>

## Completed

- [ ] Nothing yet.

## Remaining Work

- Implement the planned change end to end.

## Plan Drift

- None yet.

## Verification

Final verification instructions.

## Preservation Notes

Docs, rules, memory, or cleanup notes to consider before handoff/end-session.
```

Keep the plan compact. Do not split related work into many checklist items just
because several files may change.

## Workflow

1. Understand the goal or BACKLOG entry from `mpi-brainstorm`.
2. If the goal is clearly large or uncertain, recommend `$mpi-create-large-plan`
   in Codex or `/mpi-kanban:mpi-create-large-plan` in Claude Code instead and
   wait for confirmation.
3. Write the compact plan file.
4. Update the kanban board.

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
Next: say "continue this plan" to start implementation.
```

## Hard rules

- Do not implement.
- Do not create a large multi-step checklist in this skill.
- If the work obviously needs phased investigation, redirect to
  `mpi-create-large-plan`.
