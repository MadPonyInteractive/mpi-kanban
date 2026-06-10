---
name: mpi-create-plan
description: MPI workflow pack - Create a compact/default MPI plan for normal work. Use when the user says "MPI create plan", "create an MPI plan", "create a plan", "make a plan", "$mpi-create-plan", or after brainstorming when the task can be implemented as one coherent flow with final verification.
---

# mpi-create-plan Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Create a compact plan in the JSON task workspace at
`.agents/mpi-kanban/tasks/<id>/plan.md` and reflect that plan on the task card.
This is the default planning path for normal work.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

Use `mpi-create-large-plan` instead when the work needs investigation,
multiple phases, explicit parallel batches, or complex risk management. In
particular, if the work can be split into independent implementation tasks with
disjoint ownership, it belongs in a large plan: compact plans stay one coherent
flow and never carry `## Parallel Batch` sections.

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

1. Understand the goal or task from `mpi-brainstorm`.
2. **Load project knowledge if present.** Read
   `.agents/mpi-kanban/project-profile.md` and
   `.agents/mpi-kanban/project-knowledge-index.md` when they exist. Follow
   the context-budget rules in
   `<mpi-lib-root>/project-knowledge/indexing.md`: read pointer
   files first, then only the topic-matching docs/rules. Do not scan all
   rules and docs.
3. If the goal is clearly large or uncertain, or if independent parallel
   implementation looks likely (work splits into disjoint-ownership tasks),
   recommend `mpi-create-large-plan` instead and wait for confirmation.
4. Resolve or create the JSON board task. See "Task-board update" below.
5. Write the compact plan file to `.agents/mpi-kanban/tasks/<id>/plan.md`.
   Include project mode in `## Current State` when the profile exists
   ("Project mode: scalable-foundation"). Pull relevant conventions or
   commands from the matched topic block only.
6. Update the task card's `maturity`, `status`, and `links.plan`.

## Task-board update

Lib pointers, read only when needed:

- `<mpi-lib-root>/task-board-ops/_schema.md` - JSON board and task-card shape.
- `<mpi-lib-root>/task-board-ops/read.md` - `findBoard`, `ensureBoard`,
  `loadTask`, `findTask`.
- `<mpi-lib-root>/task-board-ops/mutate.md` - `createTask`, `writeTask`,
  `ensureLinkedFiles`, `attachPlan`.
- `<mpi-lib-root>/interop-ops/modes.md` - source-of-truth mode gate.

Before mutating `board.json`, read `.agents/mpi-kanban/state/interop.json`
when it exists. If `source_of_truth` is `nimbalyst`, do not move or create MPI
board tasks. Report:

```text
Interop mode is nimbalyst, so Nimbalyst trackers/sessions are canonical. I drafted the plan content, but I will not update .agents/mpi-kanban/board.json or task files. Update the Nimbalyst tracker/session, or run mpi-nimbalyst-sync for an explicit snapshot boundary.
```

If the file is missing or `source_of_truth` is `file`, continue with the
normal JSON task-board update below.

If `mpi-brainstorm` passed a task ID, call `loadTask(<id>)`. If it passed only
a title, call `findTask` by exact title and handle duplicates by asking the
user to choose the visible `MPI-*` ID. Otherwise ask:

```text
Does this work already have a task on the board? If yes, give the MPI ID or exact title. Reply "no" for a fresh To do task.
```

If an existing task matches:

1. If the task is in `done`, ask before reopening it into `todo`. On approval,
   call `moveTask(id, "todo", actor, "Reopened for a new plan.")`.
2. If the task is in `todo` or `doing`, leave it in its current column unless
   the user explicitly asks to move it.
3. Call `attachPlan(id, planMarkdown, actor)`.

If no task matches:

1. Call `createTask` with title, a short description, `column: "todo"`,
   `maturity: "planned"`, `status: "active"`, and the current actor.
2. Call `attachPlan(id, planMarkdown, actor)`.

Keep long-form plan content in `plan.md`. Do not embed the plan or a long
summary in `task.json`.

Confirm:

```text
Task: <id> "<title>" -> <To do | Doing>, planned. Plan: .agents/mpi-kanban/tasks/<id>/plan.md
Next: say "continue this plan" to start implementation. Implementation runs
through `mpi-continue`, which moves the card To do -> Doing before any edits.
```

## Hard rules

- Do not implement.
- Card-write preflight is mandatory before any `column`, `maturity`, or
  `status` write: read `<mpi-lib-root>/task-board-ops/_schema.md` and
  `<mpi-lib-root>/task-board-ops/mutate.md`. Do not derive legal values from
  existing cards.
- Do not let implementation begin from a `todo` card. Implementation must run
  through `mpi-continue`, which calls `beginImplementation` to move the card
  `To do -> Doing` and derive the checklist first. The lifecycle is always
  `To do -> Doing -> Done`; never `To do -> Done`.
- Do not create a large multi-step checklist in this skill.
- Do not add `## Parallel Batch` syntax to a compact plan.
- If the work obviously needs phased investigation, or splits into independent
  parallel implementation tasks, redirect to `mpi-create-large-plan`.
- New planning work uses `.agents/mpi-kanban/board.json` plus
  `.agents/mpi-kanban/tasks/<id>/plan.md`. Legacy `kanban.md` may be read only
  for explicit migration or compatibility and must not be updated as the live
  board once `board.json` exists.
- Plan steps belong in the plan file under `## Implementation`. Implementation
  checklists belong in the task workspace and are derived later by
  `mpi-continue`; do not stuff checklist steps into `task.json`.
