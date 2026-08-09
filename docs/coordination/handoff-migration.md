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

The **resume** exit of `mpi-end-session` creates a canonical handoff record in
`.agents/mpi-kanban/state/handoffs/` using the schema in
[schemas.md](schemas.md). There is no separate `mpi-handoff` skill; it merged
into close-out in v1.0.

When compatibility with older resume prompts is useful, the resume exit may
also write a small legacy pointer under `docs/handoffs/` that names the
canonical handoff path. The canonical `.agents/` record is the source of
truth.

## Continuing Work

`mpi-continue` should accept either a canonical handoff path or a legacy
`docs/handoffs/` path. When a legacy file points to a canonical handoff, agents
should load the canonical record before continuing.

## Cleanup

`docs/handoffs/` files are legacy compatibility artifacts. They must not be
treated as the future canonical state store.

