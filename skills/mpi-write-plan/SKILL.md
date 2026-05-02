---
name: mpi-write-plan
description: Decompose a complex goal into a structured plan file using parallel sub-agents for investigation. Use when the user describes a multi-step feature, a non-trivial bug fix with unclear root cause, or says "write a plan", "make a plan for this", "plan out X", or "I need to implement Y" with multiple moving parts.
---

# mpi-write-plan Skill

## Purpose

Decompose a complex goal into to-dos using parallel sub-agents during the
investigation phase only. Output a structured plan file at
`docs/plans/YYYY-MM-DD-<slug>.md` and reflect the work on the kanban board
(BACKLOG → PLANNING, or fresh PLANNING entry).

## Core principle

**Parallel sub-agents ONLY in investigation. Execution is always sequential.**

Parallel investigation is safe because sub-agents only read and write findings
— they never touch the codebase. Execution must be sequential because each
to-do may depend on the previous one, and the user verifies each step before
the next begins.

## Key rules

1. Sub-agents write findings to files — they do NOT implement.
2. Investigation phase: parallel. Execution phase: sequential (via
   `/mpi-execute-next`).
3. To-dos must be independently verifiable — each is a single, focused task.
4. Plan file path: `docs/plans/YYYY-MM-DD-<slug>.md`.
5. **No forward dependencies.** A to-do's verify step must be satisfiable
   using only what exists after *that* to-do completes — never after a later
   one. If A can only be verified once B (later) is done, merge A into B.

## To-do decomposition principle

**Err on the side of fewer, larger to-dos.** Split only when there is a clear
reason:

- One to-do depends on a prerequisite being complete first.
- The verification for each is meaningfully different and testable at
  different stages.
- The same file needs unrelated changes that could conflict.

Do NOT split just because:

- It's multiple CSS rules — group CSS changes to the same file/feature into
  one to-do.
- It's multiple utility functions in the same file.
- It's several small related tweaks.

If two tasks are in the same file and related, they belong in the same to-do.
One to-do, one file, one commit.

## Verification step rules

Every to-do MUST end with a `**Verify:**` line — no exceptions. The verify
step must be **actually testable at that stage of implementation:**

- **If the UI exists at that point** — describe what the user should
  click/toggle/see.
- **If the UI doesn't exist yet** — frame as a console.log check:
  `**Verify:** Look in browser dev tools console for "..."`
- **If the feature cannot be tested at all** (purely structural code) — write:
  `**Verify:** Look at the code — confirm the [specific thing] is present and
  correct.`

The agent executing the to-do should add `console.log(...)` calls where needed
during implementation, then tell the user what log to look for. The plan's
verification step is the source of truth for what to look for.

Never write a verification step that assumes the UI being built by that same
to-do already exists.

### Most common forward-dependency failure

A prop or API is *added* in step N but can only be *seen working* after step M
(later) passes it in. Step N's verify silently assumes M is done. Fix: move N's
code into M, or merge them. Rule of thumb: if you can't demo the change
without writing code from a later step, it doesn't belong in its own to-do.

## Workflow

1. **User describes the goal** (or `mpi-brainstorm` hands off with a BACKLOG
   entry title in prompt context).

2. **Identify investigation areas** (typically 2-4).

3. **Spawn parallel sub-agents.** Each writes findings to
   `/tmp/investigation/<area>.md`. Sub-agents READ ONLY — never edit project
   files.

4. **Synthesize findings** into a draft list of to-dos.

5. **Self-audit before writing the plan file.** For each to-do in order:
   - "Can this be verified *right now* without completing any later to-do
     first?" If no → merge into the to-do it depends on.
   - "Does this to-do have an explicit `**Verify:**` line?" If no → add one.

6. **Write the plan file** to `docs/plans/YYYY-MM-DD-<slug>.md` with `[ ]`
   to-dos.

7. **Update the kanban board.** Read `lib/kanban-ops.md` once. Then:

   - Determine if a BACKLOG entry exists for this work:
     - If `mpi-brainstorm` passed a title in prompt context → match by that
       title.
     - Otherwise, ask the user: "Does this work already have a BACKLOG entry?
       If yes, what's the title? (or 'no' for a fresh PLANNING entry)".
   - Call `findEntry(e => e.title === <title>)` to confirm.

   **If a BACKLOG entry matches:**
   1. `moveEntry(title, "BACKLOG", "PLANNING")`.
   2. `updateEntry(title, ...)` — replace the existing tag with `[PLAN]`.
   3. `updateEntry(title, ...)` — replace the body fence content with:
      ```
      Plan file: docs/plans/YYYY-MM-DD-<slug>.md
      ```

   **If no BACKLOG entry matches (or the user said no):**
   1. `ensureKanban()`.
   2. Build a PLANNING entry directly:
      - Title: 2-4 word slug from the goal.
      - tags: `[PLAN]`.
      - priority: ask the user (default `medium`).
      - defaultExpanded: `true`.
      - body: `Plan file: docs/plans/YYYY-MM-DD-<slug>.md`.
   3. `createEntry("PLANNING", entry)`.

   Confirm to the user: `Kanban: "<title>" → PLANNING. [kanban.md](.claude/mpi-kanban/kanban.md)`.

8. **User reviews the plan** before moving to execution. Suggest:
   `Run /mpi-execute-next when you're ready to start.`

## Hard rules

- No kanban steps yet — those are derived at the PLANNING → IMPLEMENTING
  transition by `/mpi-execute-next`.
- One to-do, one file, one commit (the principle — `mpi-execute-next`
  enforces this when running the plan).

## Related commands

- `/mpi-execute-next` — runs to-dos one at a time with brief gate.
