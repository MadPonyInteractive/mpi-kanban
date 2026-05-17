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
```

`index.json` is the first machine-readable file every agent checks. It should
remain small and pointer-driven. It directly lists active record paths and
claims so agents can decide what to inspect next.

The Markdown board remains human-visible state only:

```text
.claude/mpi-kanban/kanban.md
```

The board must keep the locked columns and metadata fields required by the VS
Code extension. Agent-only coordination details belong in `.agents/`, not in
new board columns or metadata fields.

## Active Records

Active records should retain only recent operational history. Keep roughly the
last 5-10 events in each record and move long-term narrative context into
plans, docs, or handoffs.

## Heartbeats

The default heartbeat timeout is 2 hours.

Stale claims are reclaimable by an orchestrator or integrator. Uncertain cases
should ask the user instead of guessing ownership intent.

## Cleanup

`mpi-cleanup` will eventually own garbage collection for coordination state.
Phase 1 only defines the layout and expected behavior.

