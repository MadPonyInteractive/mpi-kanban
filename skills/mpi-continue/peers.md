# mpi-continue - peers

Read from `mpi-continue` only when `.agents/mpi-kanban/state/index.json` shows
something that touches this work: an `open_messages` record, another live
session's claim or pending file state on a file you need, or stale coordination
records; or when a file you are about to edit is claimed by another writer.
The shared contract is
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/docs/coordination/README.md`; message
operations are `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/messages.md`.

## Open messages at start

At the continue startup boundary, read the `open_messages` records the index
points to when they target the active session, task, files, workspace, agent,
role, or user. Treat statuses `open`, `acknowledged`, and `replied` as
unresolved. Put a relevant one on the brief's `Heads-up:` line, and resolve,
acknowledge, reply, or ask the user before editing when a message changes the
next action. This is an async boundary check only; do not promise live
interruption, remote delivery, broadcast, or a background broker.

## Stale coordination records

Stale `active_tasks` records tied to done cards, or unrelated to this work, are
cleanup findings, not a reason to scan every task before the brief. Mention
them once, as a count on the `Heads-up:` line (`<n> stale coordination records
- mpi-cleanup`). Do not silently close unrelated task records during normal
continuation.

## A needed file is claimed

If another fresh active writer owns a needed file, do not edit it. Choose wait,
request handoff, create a proposal/review note, ask for an integrator, split
ownership, or ask the user. Before choosing, reread `state/index.json` and any
`open_messages` targeting the contested file, owning session, task, workspace,
agent, or role. If no relevant message exists and coordination is needed,
create or ask to create a normal message record; the recipient checks it at its
next safe workflow boundary.

## A file has pending state

If a file has pending state but no active writer, read that state before
editing and treat it as current provenance. Released file ownership is not
commit ownership; preserve pending-change provenance until review, integration,
or session close resolves it.
