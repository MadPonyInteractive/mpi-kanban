# Coordination State Layout

The project-local coordination root is:

```text
.agents/mpi-kanban/state/
```

Expected layout:

```text
.agents/
  mpi-kanban/
    state/
      index.json
      sessions/
        <uuid>.json
      tasks/
        <uuid>.json
      files/
        <uuid>.json
      handoffs/
        <uuid>.json
      archive/
```

`index.json` is the first machine-readable file every agent checks. It should
remain small and pointer-driven. It directly lists active record paths, active
write claims, pending file states, and handoffs so agents can decide what to
inspect next.

The Markdown board remains human-visible state only:

```text
.agents/mpi-kanban/kanban.md
```

The board must keep the locked columns and metadata fields required by the VS
Code extension. Agent-only coordination details belong in `.agents/`, not in
new board columns or metadata fields.

## Active Records

Active records should retain only recent operational history. Keep roughly the
last 5-10 events in each record and move long-term narrative context into
plans, docs, or handoffs.

Only file records with status `claimed` are active write locks. Completed or
released write ownership does not erase pending-change provenance; agents must
inspect pending file states before editing or committing related work.

## Heartbeats

The default heartbeat timeout is 2 hours.

Stale claims are reclaimable by an orchestrator or integrator. Uncertain cases
should ask the user instead of guessing ownership intent.

## Cleanup

`mpi-cleanup` will eventually own garbage collection for coordination state.
It should keep active state out of archive/delete proposals and move closed
state out of `index.json` only after approval.

