# coordination-ops/messages - async message operations

Read this before creating or updating
`.agents/mpi-kanban/state/messages/<uuid>.json` records. Messages are
same-filesystem async coordination records. They are checked at safe workflow
boundaries and never imply live interruption, remote delivery, global
broadcast, a daemon, or a background broker.

Related references:

- `coordination-ops/lifecycle.md`
- `coordination-ops/statuses.md`
- `docs/coordination/README.md`
- `docs/coordination/schemas.md`
- `docs/coordination/state-layout.md`
- `docs/coordination/uuid-helper.md`

## Message Root

`ensureMessageRoot()`

1. Ensure `.agents/mpi-kanban/state/` exists using `ensureStateRoot()` from
   `coordination-ops/lifecycle.md`.
2. Ensure `.agents/mpi-kanban/state/messages/` exists.
3. Read `.agents/mpi-kanban/state/index.json`.
4. If `open_messages` is missing, add it as an empty array and update
   `index.updated_at`.
5. Preserve unknown index keys. Keep the index pointer-only; message bodies
   stay in `state/messages/<uuid>.json`.

## Index Discipline

Reread `state/index.json` immediately before each message mutation:

- before creating a message, so the new pointer is appended to the current
  `open_messages` list;
- before acknowledging, replying, resolving, superseding, or closing a message,
  so concurrent message updates are not lost;
- before acting on a message about a file, so current `active_file_claims` and
  `pending_file_states` are known;
- before routing to a peer workspace, both in the source workspace and in the
  peer workspace.

Never scan every workspace on the machine for recipients. Use only the active
Kanban root or an explicit peer root supplied by the user or a trusted record.

## File-Claim Safety

Messages coordinate; they do not grant write ownership. If a message concerns a
file or workspace folder:

1. Reread `state/index.json`.
2. Load relevant `active_file_claims`. Match against both `path` and `paths`
   on each record, and treat an entry ending in `/` as covering its subtree.
3. If another fresh claim has `status: "claimed"` for the file, do not edit the
   file. Reply, ask for handoff, wait, or ask the user.
4. If no active claim blocks the file, still read matching
   `pending_file_states` before editing. Pending states are provenance.
5. Claim files through `coordination-ops/lifecycle.md` before editing.

## Operation: Send Message

Inputs: `from`, `to`, `subject`, `body`, optional `related`, optional
`thread`, optional `provenance`.

1. Call `ensureMessageRoot()`.
2. Reread `state/index.json`.
3. Generate a UUID with `python ${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/new_uuid.py`. If that
   script is missing, use `python -c "import uuid; print(uuid.uuid4())"`.
4. Write `.agents/mpi-kanban/state/messages/<uuid>.json`:
   - `schema`: `mpi-kanban/message/v1`
   - `id`: generated UUID
   - `status`: `open`
   - `created_at` and `updated_at`: current ISO-8601 timestamp
   - `from`: session, agent, role, or workspace provenance
   - `to`: `{ "selector": "<selector>", "value": <value> }`
   - `subject`: one-line summary
   - `body`: the message detail
   - `related`: compact pointers only, such as `task_card`, coordination
     `task`, `files`, `claim`, or `handoff`
   - `thread`: `{ "root": null, "parent": null }` for a new thread, or
     pointers for replies
   - `recent_events`: append `{ "at": "<timestamp>", "event": "created" }`
5. Add the message path to `open_messages` if missing.
6. Update `index.updated_at`.

Do not put message body text, thread history, or long details in `task.json` or
`state/index.json`.

## Operation: Read Inbox

Inputs: optional selector filter such as session, agent, role, task, file,
workspace, or user.

1. Read `state/index.json` first. If it does not exist, report that no MPI
   coordination inbox exists yet.
2. Load only records pointed to by `open_messages`.
3. Include messages with status `open`, `acknowledged`, or `replied`.
4. Filter by `to.selector` and `to.value` when the caller asks for a specific
   recipient or context.
5. Show the message ID, status, sender, recipient selector, subject, related
   task/files, and updated time. Summarize the body briefly unless the user
   asks to read a specific message.
6. If a pointed record is missing or already `resolved`, `superseded`, or
   `closed`, report index drift. Repair only when the active workflow owns
   cleanup or the user explicitly asks.

## Operation: Acknowledge Message

Inputs: message path or ID, acknowledging session/agent.

1. Reread `state/index.json`.
2. Load the message record from `open_messages` or the explicit path.
3. If status is `resolved`, `superseded`, or `closed`, report that it no
   longer needs acknowledgement and do not reopen it.
4. Set `status` to `acknowledged`.
5. Update `updated_at`.
6. Append a concise `acknowledged` event with actor/session provenance.
7. Keep the message path in `open_messages`.

## Operation: Reply To Message

Inputs: parent message path or ID, `from`, `body`, optional subject override.

1. Reread `state/index.json`.
2. Load the parent message.
3. Use `Send Message` to create a child message. Set `thread.parent` to the
   parent path and `thread.root` to the root path, or the parent path when the
   parent has no root.
4. Set the child `to` from the parent sender unless the user names a different
   recipient.
5. Set the parent status to `replied` unless it is already terminal.
6. Update the parent `updated_at`, append a `replied` event, and keep the
   parent path in `open_messages`.

Replies remain async. They do not wake or interrupt another agent.

## Operation: Resolve Message

Inputs: message path or ID, outcome summary, resolving session/agent.

1. Reread `state/index.json`.
2. Load the message.
3. If the message concerns files, reread active file claims before claiming or
   editing anything. Resolution records the coordination outcome; it is not
   permission to bypass a claim.
4. Set `status` to `resolved`.
5. Update `updated_at`.
6. Append a `resolved` event with the outcome summary.
7. Remove the message path from `open_messages`.
8. Keep the message record in `state/messages/` for history. Do not delete it
   during normal message handling.

Use `superseded` when a newer message, handoff, or task state replaces the
request. Use `closed` only for final cleanup.

## Operation: Archive Resolved Messages

Inputs: approved message paths or an approved cleanup proposal.

Use this only from cleanup/archive flows after surfacing the proposal to the
user. It is not part of normal send/reply/resolve handling.

1. Reread `state/index.json`.
2. Load the approved message records.
3. Refuse to archive messages with status `open`, `acknowledged`, or
   `replied`; these remain unresolved workflow-boundary records.
4. For records with status `resolved`, `superseded`, or `closed`, remove the
   path from `open_messages` if a stale pointer remains.
5. Move each approved record to
   `.agents/mpi-kanban/state/archive/messages/<uuid>.json`.
6. Leave active sessions, active tasks, active file claims, pending file
   states, and unresolved handoffs untouched.
7. Update `index.updated_at`.

Resolved messages may stay in `state/messages/` indefinitely when cleanup has
not been approved. Archiving is only a storage hygiene action.

## Operation: Route To Peer Workspace

Inputs: explicit peer workspace root, `from_workspace`, normal send-message
inputs.

1. Confirm the peer root was supplied explicitly by the user or by a trusted
   record. Do not discover peer roots by scanning sibling directories.
2. Confirm the peer root is on the same filesystem and has or can initialize
   `.agents/mpi-kanban/state/`.
3. In the peer root, call `ensureMessageRoot()`.
4. Reread the peer `state/index.json`.
5. Write the message into the peer root's
   `.agents/mpi-kanban/state/messages/<uuid>.json`.
6. Include provenance:
   - `from_workspace`: source workspace root
   - `to_workspace`: peer workspace root
7. Add the peer message path to the peer `open_messages`.
8. Optionally create or update a local source-workspace message that records
   the routing action, but do not duplicate long message bodies in local task
   cards.

Peer routing is opt-in same-machine delivery only. It is not remote delivery,
global broadcast, or a persistent bridge between workspaces.
