---
name: mpi-brainstorm
description: MPI workflow pack - MPI brainstorm workflow. Collaboratively explore an idea and design a solution through dialogue before planning. Use when the user says "MPI brainstorm", "I have an idea", "let's think through this", "brainstorm with me", "help me figure out how to approach X", "$mpi-brainstorm", or wants to explore options before implementation.
---

# mpi-brainstorm Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

Help turn ideas into fully formed designs through natural collaborative
dialogue.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

Start by understanding the current project context only when needed: only
docs/rules relevant to the topic, or what the user explicitly calls out. Do
not exhaustively scan everything.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project,
or take any implementation action until you have presented a design AND the
user has approved it. The entire value of brainstorming is catching design
mistakes before they become code; rushing to implementation defeats the
purpose.
</HARD-GATE>

## Checklist

1. **Explore context only if needed.** Check files, docs, or rules only when
   the topic directly involves them. If nothing is obviously relevant, skip.
2. **Ask clarifying questions** one at a time. Understand purpose,
   constraints, success criteria.
3. **Propose 2-3 approaches** with trade-offs and your recommendation.
4. **Present design in sections** scaled to complexity. After each section ask
   a specific question (e.g. "Does this approach work for you?") and wait for
   a response before continuing.
5. **Capture the idea on the JSON task board.** See "After design approved"
   below.
6. **Ask: want a plan?** "Do you want to create a plan for this?" If yes,
   invoke `mpi-create-plan` for normal work or `mpi-create-large-plan` for
   complex/adaptive work, passing the created task ID and title forward in the
   prompt context. Session ends.

## Context exploration rule

Only explore when explicitly needed:

- The topic directly involves a subsystem documented in `docs/PROJECT.md`.
- The user explicitly asks to look at something specific.
- The brainstorm reveals a knowledge gap that requires a quick check.

Do NOT auto-scan all of CLAUDE.md, rules, docs, or commits upfront. Keep
context lean.

## Key principles

- **One question at a time**: don't overwhelm.
- **Multiple choice preferred**: easier to answer than open-ended.
- **YAGNI ruthlessly**: remove unnecessary features.
- **Explore alternatives**: propose 2-3 approaches before settling.
- **Incremental validation**: present one section, get approval, continue.

## After design approved (BEFORE asking "Want a plan?")

Lib pointers, read each only when its recipe is actually needed:

- `<mpi-lib-root>/task-board-ops/_schema.md` - JSON task-card shape.
- `<mpi-lib-root>/task-board-ops/read.md` - `ensureBoard`, `findTask`.
- `<mpi-lib-root>/task-board-ops/mutate.md` - `createTask`, event behavior.

Steps:

1. Read `<mpi-lib-root>/task-board-ops/read.md` for `ensureBoard`. Call
   `ensureBoard()` through the `createTask` recipe. If a legacy
   `.agents/mpi-kanban/kanban.md` exists, leave it untouched and treat it only
   as a migration source or snapshot.

2. Build the task input:
   - **Title:** 2-4 word slug from the idea (e.g. "Video history support",
     "Refactor mount adapter").
   - **Description:** 1-2 short lines summarizing the approved design direction.
   - **Column:** `todo`.
   - **Maturity:** `idea`.
   - **Actor:** current agent name, such as `codex` or `claude`.

3. Before creation, call `findTask(e => e.title === <title>)`. If it already
   returns a duplicate, ask the user for a distinguishing suffix and retry with
   the revised title. Exact duplicate titles make later title-based lookup
   ambiguous.

4. Read `<mpi-lib-root>/task-board-ops/mutate.md` for `createTask`. Call
   `createTask(input)`. The recipe allocates the system task ID; never ask the
   user to supply or choose an ID.

5. Confirm to the user:

   ```text
   Captured on board: <id> "<title>" -> To do. [.agents/mpi-kanban/board.json](.agents/mpi-kanban/board.json)
   ```

## New-project routing

If this brainstorm is about a brand-new project (no `README.md` content,
no source tree, no `AGENTS.md`/`CLAUDE.md`, or the user explicitly said
"new project"), recommend `mpi-project-setup` after the todo task is
captured:

```text
This looks like a new project. Run `mpi-project-setup` to establish project mode and
knowledge before planning?
```

Do not invoke setup automatically. The user chooses whether to set up
project knowledge before planning, or proceed directly to a plan.

## End state

After the todo task is captured:

1. Ask: **"Do you want to create a plan for this?"**
2. If **yes**, choose the plan skill:
   - Use `mpi-create-plan` by default for compact, normal work.
   - Use `mpi-create-large-plan` when the work is complex, uncertain,
     multi-phase, likely to benefit from parallel investigation, or splittable
     into independent parallel implementation tasks. Parallel implementation
     eligibility alone is enough reason to choose the large-plan path, since
     compact plans cannot carry `## Parallel Batch` sections.
   Include in the prompt context: the task ID and title, e.g.
   `Create a plan for MPI-42 "Video history support"`. The plan skill will
   attach the plan to that task workspace.
3. If **no**, session ends. The task stays in `todo` until someone runs
   `mpi-create-plan` / `mpi-create-large-plan` against it later.

**No auto-invocation past this point.** The user is always in control.

## Hard rules

- No design or code work before the user approves the design.
- The todo task is created by THIS skill, not by the user and not by the next
  skill in the chain.
- New ideas create JSON task-board tasks in `todo` with system-assigned
  `MPI-*` IDs. Do not create or mutate legacy Markdown board entries for new
  work.
