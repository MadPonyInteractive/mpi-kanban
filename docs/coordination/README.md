# Shared Agent Coordination Contract

Phase 1 defines the shared coordination contract for Claude and Codex agents.
Phase 2 adds shared lifecycle procedures for sessions, tasks, file claims,
handoffs, stale claims, and cleanup behavior.

The human board remains:

```text
.claude/mpi-kanban/kanban.md
```

The canonical machine-readable coordination state lives under:

```text
.agents/mpi-kanban/state/
```

Agents should read `state/index.json` first when it exists. The index is a
small facade that points to active session, task, file-claim, and handoff
records without requiring agents to scan every state directory.

Agents coordinate through `.agents/mpi-kanban/state/` first. The kanban board is
the human display surface; tags may summarize state for the user, but tags are
not the machine coordination source.

Reference docs:

- [state-layout.md](state-layout.md) - directory layout and migration rules.
- [schemas.md](schemas.md) - compact JSON record examples.
- [roles.md](roles.md) - lightweight role permissions.
- [uuid-helper.md](uuid-helper.md) - UUID generation helper.
- [handoff-migration.md](handoff-migration.md) - canonical and legacy handoff behavior.

Lifecycle references:

- [../../lib/coordination-ops/statuses.md](../../lib/coordination-ops/statuses.md) - shared status vocabulary.
- [../../lib/coordination-ops/lifecycle.md](../../lib/coordination-ops/lifecycle.md) - session, task, file-claim, handoff, and close operations.
