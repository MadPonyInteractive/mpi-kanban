# coordination-ops/statuses - shared state vocabulary

Use these status values for `.agents/mpi-kanban/state/` records. Keep new
values out unless they are needed for agent coordination and are reflected in
`docs/coordination/schemas.md`.

## Sessions

- `active` - session is currently working and should renew heartbeat.
- `idle` - session is alive but not actively editing.
- `handoff_ready` - session is stopping and has prepared a handoff.
- `completed` - session finished its assigned work.
- `stale` - heartbeat exceeded the timeout.
- `closed` - session no longer belongs in the active index.

## Tasks

- `planned` - task is known but not started.
- `in_progress` - task has an active owner.
- `blocked` - task cannot proceed without user or integration input.
- `needs_review` - work is ready for review.
- `needs_verification` - work is ready for checks.
- `needs_integration` - work needs an integrator before final close.
- `verified` - checks passed and the task is ready to close.
- `completed` - task is done but may still be retained for cleanup.
- `closed` - task no longer belongs in the active index.
- `stale` - owner heartbeat exceeded the timeout.

## File Claims

- `claimed` - active writer owns the file. Other writers must not edit it.
- `complete` - owner finished editing. No active writer owns the file, but
  pending-change provenance remains.
- `needs_review` - no active writer; reviewer should inspect.
- `needs_verification` - no active writer; verifier should run checks.
- `needs_integration` - no active writer; integrator must reconcile or own the
  final shape before close.
- `verified` - file-level work is checked and ready for task close.
- `released` - no active writer and no pending change from this claim needs to
  be carried forward.
- `stale` - active claim heartbeat exceeded the timeout.
- `closed` - claim no longer belongs in the active index.

Only `claimed` means the file currently has an active writer. A file with
`complete`, `needs_review`, `needs_verification`, or `needs_integration` is
available for a new writer, but the next session must treat the existing
pending-change provenance as current context.

## Handoffs

- `open` - handoff is available for a future session.
- `accepted` - a session has resumed from this handoff.
- `superseded` - a newer handoff replaces this one.
- `closed` - handoff no longer belongs in the active index.

## Messages

- `open` - message is waiting for the recipient or matching workflow boundary.
- `acknowledged` - recipient has seen the message but has not resolved it.
- `replied` - recipient answered and the thread may still need follow-up.
- `resolved` - message outcome is complete and no longer belongs in
  `open_messages`.
- `superseded` - a newer message or handoff replaces this message.
- `closed` - message no longer belongs in the active index.

Messages are same-filesystem async coordination records. Agents check them at
safe workflow boundaries; statuses do not imply live interruption, background
delivery, remote transport, or a daemon.

## Message Recipient Selectors

- `session` - one coordination session record.
- `agent` - an agent runtime or named agent identity.
- `role` - a coordination role such as `implementer`, `reviewer`, or
  `integrator`.
- `task` - a visible `MPI-*` task card or UUID coordination task.
- `file` - a plain or folder-aware file reference.
- `workspace` - the active workspace context or an explicit peer workspace.
- `user` - the human operator.

## Commit Ownership

File ownership and commit ownership are separate. Releasing or completing a
file claim never grants an older session permission to commit later from stale
assumptions.

The session running `mpi-end-session`, or an explicit integrator, owns the final
commit summary. Before committing, it must reread current coordination state and
the current Git state, then describe the workspace snapshot it is actually
committing.
