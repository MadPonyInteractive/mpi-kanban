# Shared Agent Coordination Contract

Phase 1 defines the shared coordination contract for Claude and Codex agents.
It does not implement the full automated claim lifecycle.

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

Reference docs:

- [state-layout.md](state-layout.md) - directory layout and migration rules.
- [schemas.md](schemas.md) - compact JSON record examples.
- [roles.md](roles.md) - lightweight role permissions.
- [uuid-helper.md](uuid-helper.md) - UUID generation helper.
- [handoff-migration.md](handoff-migration.md) - canonical and legacy handoff behavior.

