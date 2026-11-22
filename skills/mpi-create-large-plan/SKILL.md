---
name: mpi-create-large-plan
description: MPI workflow pack - Create an adaptive, investigation-backed MPI plan for large or uncertain work. Use when the user says "MPI create large plan", "create a large MPI plan", "large plan", "complex plan", "adaptive plan", "multi-phase implementation", "$mpi-create-large-plan", or asks for non-trivial investigation or a parallel-safe plan.
---

# mpi-create-large-plan Skill

## Purpose

Create a large adaptive plan in the JSON task workspace at
`.agents/mpi-kanban/tasks/<id>/plan.md` and reflect that plan on the task card.
Use this for work with unclear root cause, multiple subsystems, meaningful
risk, or enough moving pieces that a compact plan would hide important
decisions.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

Large plans are living documents. They guide work, but `mpi-continue` may
revise the remaining work as implementation reveals new facts.

## Core principles

1. Investigate inline by default. A sub-agent costs a brief, a report, and
   re-reading what it found, so on a small area it costs more than it saves.
   Hand an area to an `investigator` only when it means reading more than
   about 10 files or long logs.
2. Implementation is adaptive through `mpi-continue`.
3. Plan in sequential phases by default. A worker costs a fresh context, a
   brief, a report and a review, so a batch buys wall-clock time, not tokens,
   and its workers share one uncommitted tree with no guard between them.
   Write a `## Parallel Batch` (run by `mpi-execute-parallel`) only when every
   task in it is big (about 10+ files or a long run), has disjoint declared
   `Ownership:`, and names a `Model:`. Unbatched work needs no justification.
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

- [ ] <task>. Ownership: <files/modules>. Briefings: <rule names or bundle>. Model: <haiku|sonnet|opus>. **Verify:** <batch-safe check>
- [ ] <task>. Ownership: <files/modules>. Briefings: <rule names or bundle>. **Verify:** <batch-safe check>

## Plan Drift

- None yet.

## Verification

**Verify mode:** auto | user-ux

`auto` = the agent fully self-verifies (tests, build, smoke, re-read) and does
not need the user to confirm a passing result. `user-ux` = the card has a UI/UX
surface the user must look at and feel in the running app before it is done.
Choose `user-ux` only when there is something a human must visually or
interactively judge; otherwise `auto`. `mpi-continue` reads this line to decide
whether to stop for the user after implementation.

Final end-to-end verification criteria.

## Preservation Notes

Docs, rules, memory, or cleanup items likely to matter before handoff/end-session.
```

## Workflow

1. Understand the user's goal or the task passed by `mpi-brainstorm`.
2. **Load project knowledge if present.** Read
   `.agents/mpi-kanban/project-profile.md` and
   `.agents/mpi-kanban/project-knowledge-index.md` when they exist. Follow
   the context-budget rules in
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/indexing.md`. Brief each
   investigation sub-agent with the profile mode and the relevant topic
   block(s), not the whole project.
3. Identify 2-4 investigation areas and investigate each inline. Only an area
   that means reading more than about 10 files or long logs goes to an
   `investigator` agent (Haiku); pass `model: "sonnet"` when the area asks
   "why does this happen" rather than "where is X". Brief it with the
   question, where to start, and the facts the plan needs. It returns its
   report; it never edits. Independent big areas run in parallel.
4. Synthesize findings into an adaptive plan with `Current State`,
   `Remaining Work`, `Plan Drift`, `Verification`, and `Preservation Notes`.
   Include project mode in `## Current State` when the profile exists.
   **Front-load decisions (scalable-foundation):** when project mode is
   `scalable-foundation`, exercise the mode's clarification and
   proactive-engineering behavior from
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-intent/modes.md` before finalizing the plan — surface
   the architecture, pattern, and library decisions the work implies, push back
   where a stronger foundation is warranted, name future-proofing concerns the
   user has not raised, and resolve open questions with the user now. A task
   becomes implementable only when it carries no unresolved decisions, so
   `mpi-continue` does not stop mid-implementation to ask.
   Set `**Verify mode:**` in `## Verification` (`user-ux` if the work has a
   UI/UX surface the user must judge in the running app, otherwise `auto`). For
   a multi-phase plan, also note per phase or per batch when a phase is
   `user-ux` so `mpi-continue` stops only on those phases.
5. Self-audit:
   - Each task has `**Verify:**`.
   - Any `## Parallel Batch` meets principle 3: big tasks, disjoint
     `Ownership:`, a `Model:` on every task.
   - No task assumes later work has already happened.
   - The plan says when `mpi-execute-parallel` is appropriate, if at all.
6. Resolve or create the JSON board task. See "Task-board update" below.
7. Write the plan file to `.agents/mpi-kanban/tasks/<id>/plan.md`.
8. Update the task card's `maturity`, `status`, and `links.plan`.

## Task-board update

Lib pointers, read only when needed:

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` - JSON board and task-card shape.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md` - `findBoard`, `ensureBoard`,
  `loadTask`, `findTask`.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` - `createTask`, `attachPlan`;
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/implement.md` - `writeTask`,
  `ensureLinkedFiles`, `moveTask`.

If `mpi-brainstorm` passed a task ID, call `loadTask(<id>)`. Otherwise search
the board: `findTask` by exact title, then by keywords from the goal. One
match (exact-title included) -> use it and name it. No match -> a fresh `todo`
task (below). Several matches (exact-title duplicates included) -> pick the
closest, say which, and list the others.

If an existing task matches:

1. If the task is in `done`, reopen it into `todo` and say so: call
   `moveTask(id, "todo", actor, "Reopened for a new large plan.")`.
2. If the task is in `todo` or `doing`, leave it in its current column unless
   the user explicitly asks to move it.
3. Call `ensureLinkedFiles(id, { "research": "research/" })` if preserving
   investigation notes.
4. Call `attachPlan(id, planMarkdown, actor)`.
5. Store investigation notes under `.agents/mpi-kanban/tasks/<id>/research/`
   when they are worth preserving.
6. If research was preserved, call `writeTask` to keep `links.research` set to
   `research/`.

If no task matches:

1. Call `createTask` with title, a short description, `column: "todo"`,
   `maturity: "planned"`, `status: "active"`, and the current actor.
2. Call `attachPlan(id, planMarkdown, actor)`.
3. Call `ensureLinkedFiles(id, { "research": "research/" })` only if preserving
   investigation notes.

Keep long-form plans, research, and batch details in task workspace files. Do
not embed them in `task.json`.

Confirm:

```text
Task: <id> "<title>" -> <To do | Doing>, planned. Plan: .agents/mpi-kanban/tasks/<id>/plan.md
Next: say "continue this plan" to start, or "create a handoff" if you want a fresh session first.
```

## Hard rules

- Do not execute implementation work.
- Card-write preflight is mandatory before any `column`, `maturity`, or
  `status` write: read `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` and
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md`. Do not derive legal values from
  existing cards.
- Do not add implementation checklist steps yet; `mpi-continue` derives
  lifecycle/phase checklists when implementation starts.
- Do not create parallel batches without explicit ownership for every task.
- Planning work uses `.agents/mpi-kanban/board.json` plus
  `.agents/mpi-kanban/tasks/<id>/plan.md`.
- Keep plan and research content in task workspace files, not in `task.json`.

## Related invocations

- Related skills: `mpi-create-plan`, `mpi-continue`, `mpi-execute-parallel`.
