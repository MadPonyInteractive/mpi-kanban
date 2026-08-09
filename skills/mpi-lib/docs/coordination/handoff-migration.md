# Handoff Migration

New canonical handoffs live under:

```text
.agents/mpi-kanban/state/handoffs/<uuid>.json
```

The old location remains legacy compatibility during migration:

```text
docs/handoffs/YYYY-MM-DD-HH-MM-<slug>.json
```

## New Handoffs

`mpi-end-session`, on its `resume` exit, creates a canonical handoff record in
`.agents/mpi-kanban/state/handoffs/` using the schema in
[schemas.md](schemas.md). (Before 1.0 this was a separate `mpi-handoff` skill.)

When compatibility with older resume prompts is useful, it may also write a
small legacy pointer under `docs/handoffs/` that names the canonical handoff
path. The canonical `.agents/` record is the source of truth.

## Continuing Work

`mpi-continue` should accept either a canonical handoff path or a legacy
`docs/handoffs/` path. When a legacy file points to a canonical handoff, agents
should load the canonical record before continuing.

## Cleanup

`docs/handoffs/` files are legacy compatibility artifacts. They must not be
treated as the future canonical state store.

