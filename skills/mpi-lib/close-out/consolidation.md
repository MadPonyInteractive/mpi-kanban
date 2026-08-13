# Consolidation sweep

Read this only when the board holds **8 or more `todo` cards** at close-out.
Below that a backlog is not sprawl, and the sweep is noise.

## Cluster

Group the `todo` cards by shared file footprint first, theme second. Use each
card's `files.json` when it lists files, otherwise the paths its `plan.md` or
description names.

Two cards belong to the same cluster when they touch the same files or the
same directory, or when they describe the same subsystem in different words.
A cluster is worth proposing at three cards or more.

## Propose, then stop

One line per cluster:

```text
11 todo cards cluster into 3 themes. Make umbrellas?
- API surface (MPI-31, MPI-35, MPI-40, MPI-44) - all touch src/api/**
- Install docs (MPI-33, MPI-34, MPI-41) - all touch docs/install.md and README.md
- Board validator (MPI-37, MPI-38, MPI-45) - all touch scripts/validate_board.py
```

An umbrella is a large-plan card whose `plan.md` carries the phases and the
`## Parallel Batch` sections; the clustered cards become its batch tasks. There
is no `parent` field and none may be added - the board contract forbids new
card fields.

## Rules

- Create nothing without approval, one umbrella at a time, through `createTask`
  in `task-board-ops/mutate.md`.
- Never close, merge, or delete the clustered cards as part of this. They stay
  until their work lands in the umbrella's plan, and the user decides which of
  the two the board keeps.
