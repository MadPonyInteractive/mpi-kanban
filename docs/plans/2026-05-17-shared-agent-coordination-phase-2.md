# Shared Agent Coordination Lifecycle Automation - Phase 2

## Current State

Phase 1 established the shared Claude/Codex coordination contract:

- Human-visible board: `.claude/mpi-kanban/kanban.md`
- Canonical machine state: `.agents/mpi-kanban/state/`
- Pointer facade: `.agents/mpi-kanban/state/index.json`
- Runtime records: sessions, tasks, file claims, and handoffs
- Lightweight roles: orchestrator, planner, implementer, reviewer, verifier,
  integrator, and docs

The current plugin is intentionally Markdown-driven. `lib/*.md` files are
reference procedures, not executable code, and the workflow skills perform
state changes by instructing the active agent what to read and write.

The current skills know about the shared coordination index, but they do not
yet automate the full lifecycle:

- No skill consistently registers or renews an active session.
- No shared procedure creates, updates, releases, or completes task/file claims.
- Handoffs write canonical JSON, but index update/release behavior is not fully
  specified.
- Reviewer, verifier, and integrator roles are documented, but not yet wired
  into repeatable workflow steps.
- `mpi-cleanup` classifies state artifacts but does not yet provide safe
  coordination-state garbage collection.
- No active `.agents/mpi-kanban/state/` directory exists in this checkout at
  plan creation time.

Local Phase 2 implementation now adds the shared lifecycle reference layer under
`lib/coordination-ops/` and wires the core workflow skills to it. This remains a
Markdown-driven plugin: the skills instruct agents how to create, update,
release, reclaim, and clean up coordination records.

Hard constraints:

- Do not change the kanban board columns or metadata fields.
- Do not use `update_live.py` during implementation unless the user explicitly
  asks at the end.
- Treat `.agents/mpi-kanban/state/` as the primary coordination source for
  agents. The kanban board is a user display surface, not the machine
  coordination source.
- Use kanban tags only as a coarse human-visible summary of coordination state
  when useful. Detailed state such as file owners, heartbeats, claim IDs,
  handoff pointers, and allowed actions belongs in `.agents/`.
- Minimize kanban edits from competing agents. Agents should coordinate through
  state first, then update the single kanban file only for user-facing summary
  changes.
- Treat file ownership and commit ownership as separate concepts. Releasing a
  file claim means no active writer owns the file; it does not mean the pending
  changes are independently safe to commit.
- Keep the VS Code extension out of scope for this phase. Richer extension
  visualization can be planned later after real use exposes the right signals.
- Preserve pure Markdown skill/reference architecture unless the spec changes.

## Completed

- [x] Added shared lifecycle/status reference docs under
  `lib/coordination-ops/`.
- [x] Updated coordination docs and schemas with `pending_file_states`, status
  vocabulary, and active-write-lock semantics.
- [x] Updated `mpi-continue`, `mpi-execute-parallel`, `mpi-handoff`,
  `mpi-end-session`, and `mpi-cleanup` to use the shared lifecycle model.
- [x] Updated `SPEC.md`, `README.md`, `AGENTS.md`, and `PLAN.md`.
- [x] Preserved the decision that `.agents/` is coordination authority, kanban
  tags are only display summaries, and VS Code extension work is deferred.
- [x] Verified `python scripts/validate_plugin.py` locally.
- [x] Confirmed `update_live.py` did not need code changes and was not run.

## Remaining Work

## Phase 1: Lifecycle Procedure Design

- [x] Define canonical lifecycle operations for coordination state: initialize
  index, register session, renew heartbeat, create task, claim files, release
  files, complete task, close session, and record handoff. **Verify:** the docs
  define inputs, outputs, status transitions, and index updates for each
  operation without contradicting `docs/coordination/schemas.md`.
- [x] Add reference docs under `lib/coordination-ops/` or extend
  `docs/coordination/` so both Claude skills and Codex bridge instructions can
  point at one shared procedure set. **Verify:** targeted searches show no
  duplicated or conflicting lifecycle rules across skills and docs.
- [x] Decide the exact active/closed/stale status values for sessions, tasks,
  file claims, and handoffs. **Verify:** `SPEC.md`, schema examples, and role
  docs use the same vocabulary.

## Phase 2: Skill Lifecycle Automation

- [x] Update `mpi-continue` so implementation sessions create or renew a
  session record, create or attach to a task record, claim likely edited files
  before implementation, and release or complete claims at the verification
  gate. **Verify:** the continue workflow describes exact JSON/index mutations
  and still waits for user approval before implementation.
- [x] Update `mpi-execute-parallel` so orchestrator and worker sessions use
  disjoint task/file claims for explicit `## Parallel Batch` work. **Verify:**
  the skill refuses overlapping ownership and records integration needs when
  workers complete.
- [x] Update `mpi-handoff` so it records the outgoing session state, releases or
  marks claims as handoff-ready, writes the canonical handoff, and updates
  `index.json`. **Verify:** the mandatory resume prompt still points to
  `mpi-continue`, and canonical handoffs remain under `.agents/`.
- [x] Update `mpi-end-session` so completed work closes the session/task state
  while preserving plan, board, docs, and memory behavior. **Verify:** the skill
  does not commit, close, or delete active coordination records incorrectly.

## Phase 3: Reviewer, Verifier, and Integrator Flows

- [x] Add role-specific procedures for reviewer, verifier, and integrator
  sessions, including which records they may create or update. **Verify:**
  reviewer remains read/review by default, verifier reports check results, and
  integrator owns conflict resolution without silently overwriting active work.
- [x] Define same-file coordination paths: wait, request handoff, add proposal,
  assign integrator, or split ownership. **Verify:** docs and skills make one
  active writer per file the default.
- [x] Define commit ownership semantics for multi-agent work. **Verify:**
  released or completed file claims still preserve pending-change provenance,
  and only the active closing/integrating session prepares the final commit
  summary after rereading current state.
- [x] Add integration-status fields or event conventions only if they are needed
  for coordination and remain compatible with the compact schemas. **Verify:**
  schema examples stay small and pointer-driven.

## Phase 4: Stale Claim Reclaim

- [x] Define stale detection around the existing 2-hour heartbeat timeout.
  **Verify:** stale calculation is documented in one place and referenced by
  skills instead of repeated inconsistently.
- [x] Add reclaim behavior for orchestrator and integrator roles when ownership
  intent is clear. **Verify:** uncertain reclaim cases explicitly ask the user.
- [x] Specify how reclaimed sessions/tasks/file claims are recorded in
  `recent_events` without growing unbounded history. **Verify:** examples keep
  only roughly 5-10 recent events.

## Phase 5: Coordination-State Cleanup

- [x] Extend `mpi-cleanup` to classify sessions, tasks, files, and handoffs as
  active, completed, stale, superseded, orphaned, archive candidate, or
  uncertain. **Verify:** cleanup prints a proposal first and never deletes
  active state.
- [x] Define approved cleanup actions for moving closed state out of the active
  facade, compacting event history, and leaving uncertain files untouched.
  **Verify:** `index.json` remains a small active-state pointer file after
  cleanup.
- [x] Add any needed archive path documentation for coordination state.
  **Verify:** archives are not deleted by default and the board contract remains
  unchanged.

## Phase 6: Validation And Release Readiness

- [x] Update `SPEC.md`, `PLAN.md`, `README.md`, and `AGENTS.md` if the lifecycle
  behavior changes the public contract. **Verify:** user-facing docs and bridge
  instructions agree on the same workflow.
- [x] Run repository validation and keep validator changes deferred because the
  existing validator already covers plugin registration/frontmatter for this
  docs-only lifecycle pass. **Verify:** `python scripts/validate_plugin.py`
  passes.
- [x] Run targeted searches for old or contradictory behavior around
  `index.json`, handoffs, claims, reviewers, verifiers, integrators, and
  cleanup. **Verify:** only accepted migration notes remain.
- [x] Confirm VS Code extension visualization is deferred and keep Phase 3 or a
  later improvement card available for richer UI work after real use. **Verify:**
  no files in the companion extension repository are edited during Phase 2.

## Plan Drift

- 2026-05-18: VS Code extension visualization is deferred. Existing kanban tags
  are enough for coarse user-facing status during Phase 2.
- 2026-05-18: `update_live.py` may be edited when copy rules need it, but it
  must not be run until the user explicitly asks for the final live update.

## Verification

Before Phase 2 is considered complete:

1. Skills and docs describe one consistent coordination lifecycle.
2. `mpi-continue`, `mpi-execute-parallel`, `mpi-handoff`, `mpi-end-session`,
   and `mpi-cleanup` have concrete coordination-state behaviors.
3. Reviewer, verifier, and integrator roles are actionable without granting
   accidental write ownership.
4. File-claim release does not erase pending-change provenance, and commit
   responsibility belongs to the session closing or integrating the task.
5. Stale claim reclaim behavior asks the user when ownership intent is unclear.
6. Cleanup can propose safe coordination-state garbage collection without
   deleting active state.
7. The kanban board contract remains unchanged.
8. `update_live.py` has not been run unless the user explicitly asks for the
   final live update.

## Preservation Notes

- Keep `docs/brainstorms/2026-05-17-agent-coordination.md` as the design record.
- This phase likely changes skill behavior and shared reference docs, so final
  verification should include the plugin validator and targeted contradiction
  searches.
- Do not edit the companion VS Code extension unless the user explicitly agrees
  that visualization should move into Phase 2.
