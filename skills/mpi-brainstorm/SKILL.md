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

Start by understanding the current project context only when needed â€” only
docs/rules relevant to the topic, or what the user explicitly calls out. Do
not exhaustively scan everything.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project,
or take any implementation action until you have presented a design AND the
user has approved it. The entire value of brainstorming is catching design
mistakes before they become code â€” rushing to implementation defeats the
purpose.
</HARD-GATE>

## Checklist

1. **Explore context only if needed.** Check files, docs, or rules only when
   the topic directly involves them. If nothing is obviously relevant, skip.
2. **Ask clarifying questions** â€” one at a time. Understand purpose,
   constraints, success criteria.
3. **Propose 2-3 approaches** with trade-offs and your recommendation.
4. **Present design in sections** scaled to complexity. After each section ask
   a specific question (e.g. "Does this approach work for you?") and wait for
   a response before continuing.
5. **Capture the idea on the kanban board.** See "After design approved" below.
6. **Ask: want a plan?** "Do you want to create a plan for this?" â†’ if yes,
   invoke `mpi-create-plan` for normal work or `mpi-create-large-plan` for
   complex/adaptive work, passing the BACKLOG entry title forward in the
   prompt context. Session ends.

## Context exploration rule

Only explore when explicitly needed:

- The topic directly involves a subsystem documented in `docs/PROJECT.md`.
- The user explicitly asks to look at something specific.
- The brainstorm reveals a knowledge gap that requires a quick check.

Do NOT auto-scan all of CLAUDE.md, rules, docs, or commits upfront. Keep
context lean.

## Key principles

- **One question at a time** â€” don't overwhelm.
- **Multiple choice preferred** â€” easier to answer than open-ended.
- **YAGNI ruthlessly** â€” remove unnecessary features.
- **Explore alternatives** â€” propose 2-3 approaches before settling.
- **Incremental validation** â€” present one section, get approval, continue.

## After design approved (BEFORE asking "Want a plan?")

Lib pointers (read each only when its recipe is actually needed):

- `<mpi-lib-root>/kanban-ops/find.md` â€” `ensureKanban`, `findEntry`
- `<mpi-lib-root>/kanban-ops/mutate.md` â€” `createEntry`
- `<mpi-lib-root>/kanban-ops/_schema.md` â€” entry shape (only if you
  need a schema reminder before building the entry)

Steps:

1. Read `<mpi-lib-root>/kanban-ops/find.md` for `ensureKanban`. Call `ensureKanban()`. If
   the file did not exist, the recipe creates it from the template and emits
   the one-time setup notice (kanban link + extension marketplace link).
   Continue regardless.

2. Ask the user ONCE for the priority of this idea:
   ```
   Priority for the kanban entry? (high / medium / low â€” default medium)
   ```
   Default to `medium` if the user gives no answer.

3. Build the entry:
   - **Title:** 2-4 word slug from the idea (e.g. "Video history support",
     "Refactor mount adapter").
   - **Tags:** infer ONE from the idea content:
     - `[bug]` â€” fixing broken behavior.
     - `[feature]` â€” new user-facing capability.
     - `[refactor]` â€” internal restructure with no behavior change.
     - `[Idea]` â€” exploratory or speculative; default if unclear.
   - **priority:** the value the user gave (or `medium`).
   - **defaultExpanded:** `true`.
   - **body:** 2-3 line summary of the idea.
   - **No `steps`. No `Plan file:` ref.**

4. Read `<mpi-lib-root>/kanban-ops/mutate.md` for `createEntry`. Call
   `createEntry("BACKLOG", entry)`. If `findEntry(e => e.title === <title>)`
   already returns a hit, ask the user for a distinguishing suffix and retry.

5. Confirm to the user: `Captured on board: "<title>" â†’ BACKLOG. [kanban.md](.claude/mpi-kanban/kanban.md)`.

## New-project routing

If this brainstorm is about a brand-new project (no `README.md` content,
no source tree, no `AGENTS.md`/`CLAUDE.md`, or the user explicitly said
"new project"), recommend `mpi-project-setup` after the BACKLOG entry is
captured:

```text
This looks like a new project. Run `mpi-project-setup` to establish project mode and
knowledge before planning?
```

Do not invoke setup automatically. The user chooses whether to set up
project knowledge before planning, or proceed directly to a plan.

## End state

After the BACKLOG entry is captured:

1. Ask: **"Do you want to create a plan for this?"**
2. If **yes** â†’ choose the plan skill:
   - Use `mpi-create-plan` by default for compact, normal work.
   - Use `mpi-create-large-plan` when the work is complex, uncertain,
     multi-phase, likely to benefit from parallel investigation, or splittable
     into independent parallel implementation tasks. Parallel implementation
     eligibility alone is enough reason to choose the large-plan path, since
     compact plans cannot carry `## Parallel Batch` sections.
   Include in the prompt context: the BACKLOG entry title (skills don't pass
   arguments natively â€” pass it as prose, e.g. "Create a plan for the BACKLOG
   entry titled \"<title>\""). The plan skill will move the entry to PLANNING.
3. If **no** â†’ session ends. Entry stays in BACKLOG until someone runs
   ``mpi-create-plan` / `mpi-create-large-plan` against it later.

**No auto-invocation past this point.** The user is always in control.

## Hard rules

- No design or code work before the user approves the design.
- The BACKLOG entry is created by THIS skill â€” not by the user, not by the
  next skill in the chain.



