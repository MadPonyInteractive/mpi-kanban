---
name: mpi-umbrella
description: MPI workflow pack - Review the task board and fold related cards into an umbrella card. Use when the user says "create an umbrella", "make an umbrella card", "umbrella these cards", "evaluate the cards on the kanban", "review the board and group the cards", "group these cards", "combine MPI-31 and MPI-35", "roll these into one card", "these three are the same job", "tidy up the board", "$mpi-umbrella", or "/mpi-umbrella". This is board restructuring, not execution - a request to RUN cards goes to mpi-continue, and a request to delete stale artifacts goes to mpi-cleanup.
---

# mpi-umbrella Skill

Fold scattered cards that are really one job into a single umbrella card. Two
ways in: the user names the cards, or the user points at the board and asks
what should be grouped.

An umbrella is a large-plan card whose `plan.md` carries the phases and the
`## Parallel Batch` sections; the clustered cards become its batch tasks. There
is no `parent` field and none may be added - the board contract forbids new
card fields, and the VS Code extension reads that fixed schema.

## Read first

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/close-out/consolidation.md` - how to
  cluster, and what a proposal looks like
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md` - `findBoard`,
  `findTask`, `loadTask`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` -
  `createTask`, `writeTask`, `appendEvent`

Missing? The install is broken - tell the user to reinstall the plugin and
stop. Never hand-write a `task.json`.

## Process

### 1. Which cards

**The user named them** - load exactly those. Do not go looking for more; a
named set is a decision, not an opening bid.

**The user pointed at the board** - load the `todo` cards and cluster them per
`consolidation.md`: shared file footprint first, theme second. Use each card's
`files.json` when it lists files, otherwise the paths its `plan.md` or
description names.

Below 8 `todo` cards, say so and ask whether to continue anyway. A small
backlog is usually not sprawl, and an umbrella over three unrelated cards is
just a worse board.

### 2. Propose before creating

One line per cluster, then stop and wait:

```text
11 todo cards cluster into 3 themes. Make umbrellas?
- API surface (MPI-31, MPI-35, MPI-40, MPI-44) - all touch src/api/**
- Install docs (MPI-33, MPI-34, MPI-41) - all touch docs/install.md and README.md
```

Say plainly when a card does NOT fit any cluster, and why. A card quietly left
out of the proposal reads as one that was considered and grouped.

### 3. Create, one at a time

On approval, `createTask` per `mutate.md` for one umbrella. Its `plan.md`
carries the phases and a `## Parallel Batch` section per phase that can run in
parallel, with each member card's file ownership listed - that section is what
`mpi-execute-parallel` later reads, so disjoint file ownership is the point of
writing it, not decoration.

Link the member cards from the umbrella's `plan.md` by ID and title.

### 4. Leave the member cards alone

Do not close, merge, delete, or move them. They stay until their work lands in
the umbrella's plan, and the user decides which of the two the board keeps.
Ask that question once, in one line, and accept the answer:

```text
Umbrella MPI-52 created over MPI-31, MPI-35, MPI-40, MPI-44.
Keep the member cards, or close them once their work is in the umbrella plan?
```

## Report

```text
**CREATED:** <umbrella id and title> over <member ids>
**LEFT OUT:** <card ids that fit no cluster, with the reason, or "none">
**MEMBERS:** unchanged, still in <column>
```

## Hard rules

- Propose first, create on approval, one umbrella at a time.
- Never close, merge, delete, or move a member card here.
- Never hand-edit a `task.json`; every write goes through a `mutate.md` recipe
  so the enum, coherence, and events stay correct.
- Never add a `parent` field or any other new card field.
- Do not commit or push; that belongs to `mpi-handoff` or `mpi-end-session`.
- A request to RUN cards is `mpi-continue`, not this skill.
