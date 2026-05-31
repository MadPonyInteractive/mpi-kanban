---
name: mpi-message
description: MPI workflow pack - Send or manage same-filesystem async coordination messages between agents. Use for tell another agent, read inbox, reply, acknowledge, resolve, or explicit peer workspace messages.
---

# mpi-message Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Create and manage durable MPI coordination messages under
`.agents/mpi-kanban/state/messages/`. Use this when the user asks to tell
another agent, read an inbox, acknowledge a message, reply to a message,
resolve a message, or route a message to a known peer workspace.

Messages are async and same-filesystem only. This skill does not interrupt
running agents, start a daemon, run a broker, scan for recipients globally,
broadcast across projects, or deliver messages to remote machines.

## Shared References

Read these references as needed:

- `<mpi-lib-root>/coordination-ops/messages.md` - message root, send, inbox,
  acknowledge, reply, resolve, and peer-route operations
- `<mpi-lib-root>/coordination-ops/lifecycle.md` - state root and file-claim
  safety rules
- `<mpi-lib-root>/coordination-ops/statuses.md` - message statuses and
  recipient selectors
- `<mpi-lib-root>/docs/coordination/schemas.md` - message JSON examples
- `<mpi-lib-root>/docs/coordination/state-layout.md` - state layout and
  workspace scope

## Invocation

Use the installed Agent Skills invocation for this agent, or ask naturally:

- `mpi-message tell <agent/session/role/task/file/user> ...`
- `mpi-message inbox`
- `mpi-message read <message-id>`
- `mpi-message ack <message-id>`
- `mpi-message reply <message-id> ...`
- `mpi-message resolve <message-id> ...`
- `mpi-message route <peer-root> ...`

## Pre-conditions

1. Resolve `<mpi-lib-root>`.
2. Read `<mpi-lib-root>/coordination-ops/messages.md`.
3. Read `.agents/mpi-kanban/state/index.json` when it exists. If it is missing
   and the user only wants to read the inbox, report that no MPI coordination
   inbox exists yet.
4. For send, acknowledge, reply, resolve, or peer routing, use the shared
   `ensureMessageRoot()` flow. Create only coordination state directories and
   index keys required by that operation.
5. If the message concerns files, reread `state/index.json` and active file
   claim records before suggesting or taking any edit action. A message never
   bypasses a fresh `claimed` file lock.

## Send Or Tell

Use this path when the user asks to tell another agent/session/role/task/file,
or when a workflow needs an async handoff request.

1. Identify the recipient selector: `session`, `agent`, `role`, `task`,
   `file`, `workspace`, or `user`.
2. Ask one concise clarification only if the selector or message body is
   ambiguous.
3. Keep the subject one line. Put detail in the message body, not in
   `task.json` or `state/index.json`.
4. Include compact related pointers when available:
   - `task_card`: visible `MPI-*` task ID
   - `task`: coordination task path
   - `files`: plain or folder-aware file references
   - `claim`: contested file claim path
   - `handoff`: related handoff path
5. Run the shared `Send Message` operation.
6. Report the message ID, path, recipient selector, and subject.

## Read Inbox

Use this path for `inbox`, `read inbox`, `messages`, or checking pending
coordination.

1. Run the shared `Read Inbox` operation.
2. Default to unresolved messages: `open`, `acknowledged`, and `replied`.
3. For a summary view, list each message ID, status, recipient selector,
   subject, related task/files, and updated time.
4. For a specific message ID, show the body and recent events.
5. Report stale index pointers as drift. Do not repair them unless the user
   asks or the active workflow owns cleanup.

## Acknowledge

Use this path when the recipient has seen a message but the outcome is not
complete.

1. Run the shared `Acknowledge Message` operation.
2. Keep the message in `open_messages`.
3. Report the message ID and new status.

## Reply

Use this path when the user answers a message or needs to ask a follow-up.

1. Load the parent message.
2. Run the shared `Reply To Message` operation.
3. Send the reply to the parent sender unless the user names a different
   recipient.
4. Keep the parent in `open_messages` with status `replied`.
5. Report the child message ID and parent message ID.

## Resolve

Use this path when the message outcome is complete.

1. If the message concerns files, reread `state/index.json` and active file
   claims first.
2. Do not edit files blocked by another fresh `claimed` record. Resolve with a
   coordination outcome or reply asking for a handoff instead.
3. Run the shared `Resolve Message` operation.
4. Remove the message pointer from `open_messages`; keep the message record for
   history.
5. Report the message ID, status, and outcome summary.

## Route To Peer Workspace

Use this path only when the user gives a known peer workspace root or a trusted
record names one.

1. Confirm the peer root explicitly. Do not scan sibling folders or all MPI
   projects on the machine.
2. Confirm this is same-filesystem routing.
3. In the peer root, run the shared `Route To Peer Workspace` operation.
4. Add `from_workspace` and `to_workspace` provenance.
5. Report the peer message ID and peer message path.

## Hard Rules

- Same-filesystem async messages only.
- No live interruption, daemon, background broker, remote delivery, global
  broadcast, or implicit recipient discovery.
- Message bodies and thread details belong in `state/messages/<uuid>.json`,
  not in task cards or `state/index.json`.
- Reread `state/index.json` before every message mutation.
- Do not edit files blocked by active `claimed` file records.
- Keep `state/index.json` pointer-only; use `open_messages` for unresolved
  message paths.
