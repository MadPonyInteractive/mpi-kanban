# coordination-ops/lifecycle - session, task, and claim operations

Read this before writing `.agents/mpi-kanban/state/` records. The human JSON
task board is display state; agents coordinate through these records first.

Related references:

- `docs/coordination/README.md`
- `docs/coordination/schemas.md`
- `docs/coordination/roles.md`
- `docs/coordination/uuid-helper.md`
- `coordination-ops/statuses.md`
- `coordination-ops/messages.md`

## State Root

`ensureStateRoot()`

1. Create these directories when missing:
   - `.agents/mpi-kanban/state/sessions/`
   - `.agents/mpi-kanban/state/tasks/`
   - `.agents/mpi-kanban/state/files/`
   - `.agents/mpi-kanban/state/messages/`
   - `.agents/mpi-kanban/state/handoffs/`
   - `.agents/mpi-kanban/state/archive/`
2. If `.agents/mpi-kanban/state/index.json` is missing, create it with:

   ```json
   {
     "schema": "mpi-kanban/state-index/v1",
     "updated_at": "<ISO-8601 timestamp>",
     "board": ".agents/mpi-kanban/board.json",
     "heartbeat_timeout_minutes": 120,
     "active_sessions": [],
     "active_tasks": [],
     "active_file_claims": [],
     "pending_file_states": [],
     "open_messages": [],
     "active_handoffs": []
   }
   ```

3. Preserve unknown keys unless they contradict the schema. Update
   `updated_at` whenever the index changes.

## Index Rules

- `active_sessions` points at sessions with `active`, `idle`, or
  `handoff_ready` status.
- `active_tasks` points at tasks that are not `closed`.
- `active_file_claims` points only at file records with status `claimed`.
- `pending_file_states` points at file records with `complete`,
  `needs_review`, `needs_verification`, or `needs_integration` status.
- `open_messages` points at message records with `open`, `acknowledged`, or
  `replied` status.
- `active_handoffs` points at handoffs with `open` or `accepted` status.

If a coordination task record names a JSON `task_card` that is already in the
board `done` column, keep it in `active_tasks` only while the coordination
status is explicitly unresolved (`needs_review`, `needs_verification`, or
`needs_integration`). `verified`, `completed`, and `closed` coordination tasks
for done cards must be removed from `active_tasks`; `closed` records may be
archived by cleanup.

Keep the index small. Do not duplicate plan text, diffs, or long histories in
it.

## Message Boundary

Message records live under `.agents/mpi-kanban/state/messages/`. They are
same-filesystem async coordination records checked at workflow boundaries such
as continue, contested file claims, handoff, parallel execution, cleanup, and
end-session. They must not promise live interruption, remote delivery, global
broadcast, or a daemon. Message operations for send, inbox, acknowledge, reply,
resolve, and explicit peer routing live in `coordination-ops/messages.md`.

## Operation: Register Or Renew Session

Inputs: `agent`, `role`, optional `task`, optional display `name`.

1. Read `state/index.json`.
2. Reuse the current session record when the session path is already known.
   Otherwise generate a UUID with `python ${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/new_uuid.py`.
   If that script is missing, use `python -c "import uuid; print(uuid.uuid4())"`.
   Never skip session registration because the helper could not be found.
3. Write or update `sessions/<uuid>.json`:
   - `schema`: `mpi-kanban/session/v1`
   - `status`: `active`
   - `heartbeat_at`: current ISO-8601 timestamp
   - `claude_session_id`: the current Claude Code session id, when it is known
   - `allowed_actions`: from `docs/coordination/roles.md`
   - `recent_events`: append `session_started` or `heartbeat_renewed`

   `claude_session_id` is what lets the `guard-claim` hook tell your own claims
   from a peer's. Without it a claim is unattributable, and the hook allows the
   write rather than blocking an agent out of files it claimed itself.
4. Add the session path to `active_sessions` if missing.

## Operation: Renew Heartbeat

Inputs: session path.

1. Update the session `heartbeat_at`.
2. Update related active task and claimed file `heartbeat_at` values if this
   session owns them.
3. Append a concise event only when useful; do not log every routine heartbeat.
4. Update `index.updated_at`.

## Operation: Create Or Attach Task

Inputs: title, JSON task-board item ID or legacy kanban entry title, plan path,
owner session path.

1. Reuse an existing non-closed coordination task for the same plan and
   task-board item when it clearly represents the same work.
2. Otherwise generate a UUID and create `tasks/<uuid>.json` with status
   `in_progress`.
3. For JSON-board projects, set `task_card` to the visible `MPI-*` task ID and
   keep any task-workspace paths as pointers only. For unmigrated legacy
   projects, set `kanban_entry` to the entry title.
4. Set `owner_session`, `plan`, and `allowed_actions`.
5. Add the task path to `active_tasks`.
6. Link the task path from the session record.

## Operation: Claim Files

Inputs: session path, task path, file paths or module ownership.

1. Read `active_file_claims` before editing. A record claims either `path` (a
   single string) or `paths` (a list); read BOTH fields on every record. An
   entry ending in `/` claims that whole subtree. See
   `docs/coordination/schemas.md`.
2. For each file, if another fresh `claimed` record exists:
   - do not edit the file;
   - choose wait, request handoff, create a proposal/review note, ask for an
     integrator, split ownership, or ask the user.
3. If a claim is stale, only an orchestrator or integrator may reclaim it when
   intent is clear. Uncertain cases ask the user.
4. If no active writer blocks the file, create a file record with status
   `claimed`, `claim_kind: "write"`, owner session, owner role, task path, and
   heartbeat. Use `path` for a single file; use `paths` for one claim over a set
   of files or a module. Do not write both on the same record.
5. Add the file record to `active_file_claims`.
6. If the same path has records in `pending_file_states`, read them before
   editing; they are provenance, not write locks.

## Operation: Complete Or Release File Claim

Inputs: file claim path, outcome.

Use the outcome to set status:

- No relevant changes made: `released`.
- Editing finished, awaiting task-level close: `complete`.
- Needs a reviewer: `needs_review`.
- Needs checks: `needs_verification`.
- Needs reconciliation with other work: `needs_integration`.
- Checks passed and no further file-level work remains: `verified`.

Then:

1. Remove the claim path from `active_file_claims` unless status remains
   `claimed`.
2. Add it to `pending_file_states` when status is `complete`, `needs_review`,
   `needs_verification`, or `needs_integration`.
3. Remove it from `pending_file_states` when status is `released`, `verified`,
   or `closed`.
4. Preserve provenance fields such as owner session, task path, file path,
   outcome, and recent events.

## Operation: Complete Task

Inputs: task path, outcome.

1. Set task status to `needs_review`, `needs_verification`,
   `needs_integration`, `verified`, or `completed` as appropriate.
2. Keep the task in `active_tasks` until it is `closed`.
3. Close or update related file records only when their pending state has been
   reviewed, verified, integrated, or intentionally released.
4. Do not treat a completed file claim as a commit boundary.

When the matching JSON task card is moved to `done` after explicit validation,
set resolved coordination tasks to `closed` and remove them from
`active_tasks`. Keep unresolved records active only when review, verification,
or integration is still pending.

## Operation: Record Handoff

Inputs: session path, task path, active plan, JSON task-board item or legacy
kanban entry, next role.

1. Update active task/file records to `handoff_ready`, `complete`, or
   `needs_integration` as appropriate.
2. Generate a UUID and write
   `.agents/mpi-kanban/state/handoffs/<uuid>.json`.
3. Add the handoff path to `active_handoffs`.
4. Set the outgoing session to `handoff_ready` unless it will continue working.
5. The resume prompt must point the next session to `mpi-continue`.
6. Include the visible task-card ID and task workspace links when available.
   Use the legacy kanban entry title only for unmigrated projects.

## Operation: Close Session

Inputs: session path.

1. Reread `state/index.json`, related task/file records, and current Git state.
2. Confirm there are no active `claimed` files owned by the session. Complete,
   release, or hand off each claim first.
3. If committing, the closing or integrating session owns the final commit
   summary and must describe the current workspace snapshot, not stale per-file
   assumptions from an older claim.
4. Set session status to `completed` or `closed`.
5. Remove closed sessions and closed records from active index arrays.

## Task Board Summary State

Task-card badges, column placement, linked checklist/validation files, and
attention state are user-facing work summaries. They must never be the source
of truth for agent coordination.

Suggested summary badges or status labels:

- `agent-active`
- `claimed`
- `needs-review`
- `needs-verify`
- `needs-integration`
- `blocked`
- `stale-claim`
- `handoff-ready`

Update card badges or attention state sparingly through JSON task-board
operations. Detailed coordination state belongs in `.agents/mpi-kanban/state/`;
long implementation checklists, validation notes, and handoffs belong in
`.agents/mpi-kanban/tasks/<id>/` workspace files.

