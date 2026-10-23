# mpi-end-session - peers

Read from `mpi-end-session` only when the step 0 scope gate did NOT clear:
`state/index.json` has a non-empty `active_sessions`, `active_tasks`,
`active_file_claims`, `pending_file_states`, or `open_messages`. Then also read
the coordination references the gate skips:
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/docs/coordination/README.md`,
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md`,
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/statuses.md`, and
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/messages.md`.

- Reread the active session, task, file claim, and handoff records before
  committing. A released file claim means no active writer owns the file; it
  does not mean the pending changes are independently safe to commit.
- Read any `open_messages` records that target the current session, task,
  changed files, workspace, agent, role, or user. Treat `open`, `acknowledged`,
  and `replied` as unresolved. They can block commit, require a
  reply/acknowledgement, require an integrator, or require a handoff first.
  This is an async boundary check only; do not promise live interruption,
  remote delivery, global broadcast, or a background broker.
- If this session owns active `claimed` files, complete, release, or hand them
  off before committing. If another fresh active session owns claimed files
  that are part of the current task, do not commit those changes; ask the user
  or assign an integrator.
- Never treat task-card badges or attention as coordination authority; reread
  `.agents/mpi-kanban/state/`.
- Close-out (or an explicit integrator) owns the final commit summary. Base it
  on current coordination and Git state, not a stale file claim.
