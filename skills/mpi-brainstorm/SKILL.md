---
name: mpi-brainstorm
description: Collaboratively explore an idea and design a solution through dialogue — no spec doc needed. Use when the user says "I have an idea", "let's think through this", "brainstorm with me", "help me figure out how to approach X", "what's the best way to do Y", or wants to explore options before committing to implementation.
---

# mpi-brainstorm Skill

Help turn ideas into fully formed designs through natural collaborative
dialogue.

Start by understanding the current project context only when needed — only
docs/rules relevant to the topic, or what the user explicitly calls out. Do
not exhaustively scan everything.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project,
or take any implementation action until you have presented a design AND the
user has approved it. The entire value of brainstorming is catching design
mistakes before they become code — rushing to implementation defeats the
purpose.
</HARD-GATE>

## Checklist

1. **Explore context only if needed.** Check files, docs, or rules only when
   the topic directly involves them. If nothing is obviously relevant, skip.
2. **Ask clarifying questions** — one at a time. Understand purpose,
   constraints, success criteria.
3. **Propose 2-3 approaches** with trade-offs and your recommendation.
4. **Present design in sections** scaled to complexity. After each section ask
   a specific question (e.g. "Does this approach work for you?") and wait for
   a response before continuing.
5. **Capture the idea on the kanban board.** See "After design approved" below.
6. **Ask: want a plan?** "Do you want to write a plan for this?" → if yes,
   invoke `mpi-write-plan` and pass the BACKLOG entry title forward in the
   prompt context. Session ends.

## Context exploration rule

Only explore when explicitly needed:

- The topic directly involves a subsystem documented in `docs/PROJECT.md`.
- The user explicitly asks to look at something specific.
- The brainstorm reveals a knowledge gap that requires a quick check.

Do NOT auto-scan all of CLAUDE.md, rules, docs, or commits upfront. Keep
context lean.

## Key principles

- **One question at a time** — don't overwhelm.
- **Multiple choice preferred** — easier to answer than open-ended.
- **YAGNI ruthlessly** — remove unnecessary features.
- **Explore alternatives** — propose 2-3 approaches before settling.
- **Incremental validation** — present one section, get approval, continue.

## After design approved (BEFORE asking "Want a plan?")

Read `lib/kanban-ops.md` once. Then:

1. Call `ensureKanban()`. If the file did not exist, the recipe in kanban-ops
   creates it from the template and emits the one-time setup notice (kanban
   link + extension marketplace link). Continue regardless.

2. Ask the user ONCE for the priority of this idea:
   ```
   Priority for the kanban entry? (high / medium / low — default medium)
   ```
   Default to `medium` if the user gives no answer.

3. Build the entry:
   - **Title:** 2-4 word slug from the idea (e.g. "Video history support",
     "Refactor mount adapter").
   - **Tags:** infer ONE from the idea content:
     - `[bug]` — fixing broken behavior.
     - `[feature]` — new user-facing capability.
     - `[refactor]` — internal restructure with no behavior change.
     - `[Idea]` — exploratory or speculative; default if unclear.
   - **priority:** the value the user gave (or `medium`).
   - **defaultExpanded:** `true`.
   - **body:** 2-3 line summary of the idea.
   - **No `steps`. No `Plan file:` ref.**

4. Call `createEntry("BACKLOG", entry)`. If `findEntry(e => e.title === <title>)`
   already returns a hit, ask the user for a distinguishing suffix and retry.

5. Confirm to the user: `Captured on board: "<title>" → BACKLOG. [kanban.md](.claude/mpi-kanban/kanban.md)`.

## End state

After the BACKLOG entry is captured:

1. Ask: **"Do you want to write a plan for this?"**
2. If **yes** → invoke `mpi-write-plan`. Include in the prompt context: the
   BACKLOG entry title (skills don't pass arguments natively — pass it as
   prose, e.g. "Write a plan for the BACKLOG entry titled \"<title>\""). The
   plan skill will move the entry to PLANNING.
3. If **no** → session ends. Entry stays in BACKLOG until someone runs
   `/mpi-write-plan` against it later.

**No auto-invocation past this point.** The user is always in control.

## Hard rules

- No `mcp__nimbalyst-*` calls.
- No design or code work before the user approves the design.
- The BACKLOG entry is created by THIS skill — not by the user, not by the
  next skill in the chain.
