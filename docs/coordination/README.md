# Shared Agent Coordination Contract

This document defines the shared coordination contract for agents.
Phase 2 adds shared lifecycle procedures for sessions, tasks, file claims,
handoffs, stale claims, and cleanup behavior.

The human task board lives outside coordination state:

```text
.agents/mpi-kanban/board.json
.agents/mpi-kanban/tasks/<id>/
```

Legacy projects may still have `.agents/mpi-kanban/kanban.md`. Treat it as a
migration input or snapshot after `board.json` exists.

The canonical machine-readable coordination state lives under:

```text
.agents/mpi-kanban/state/
```

Agents should read `state/index.json` first when it exists. The index is a
small facade that points to active session, task, file-claim, message, and
handoff records without requiring agents to scan every state directory.

Agents coordinate through `.agents/mpi-kanban/state/` first. The JSON task
board is the human display surface; card badges and attention state may
summarize state for the user, but they are not the machine coordination source.

One Kanban root owns one work context. In a multi-root VS Code workspace, the
active `.code-workspace` file defines the member folders for the shared board,
coordination state, and same-filesystem message inbox. Related folders outside
that workspace should be added to the workspace before agents treat them as in
scope.

Async messages are durable JSON records under
`.agents/mpi-kanban/state/messages/`. Agents check them at workflow boundaries;
they are not live interruptions and do not require a daemon, broker, remote
delivery, or global machine-wide broadcast.

Reference docs:

- [state-layout.md](state-layout.md) - directory layout and migration rules.
- [schemas.md](schemas.md) - compact JSON record examples.
- [roles.md](roles.md) - lightweight role permissions.
- [uuid-helper.md](uuid-helper.md) - UUID generation helper.
- [handoff-migration.md](handoff-migration.md) - canonical and legacy handoff behavior.

Lifecycle references:

- [../../lib/coordination-ops/statuses.md](../../lib/coordination-ops/statuses.md) - shared status vocabulary.
- [../../lib/coordination-ops/lifecycle.md](../../lib/coordination-ops/lifecycle.md) - session, task, file-claim, handoff, and close operations.
