# MPI Kanban Shared Agent Coordination Brainstorm

Date: 2026-05-17
Status: brainstorm

## Purpose

Design MPI Kanban as a shared workflow layer for Claude and Codex agents working
in the same project. The goal is not one permanent orchestrator chat. The goal is
for any number of agent sessions to coordinate through project files without
stepping on each other's work.

This brainstorm should become the source material for later `SPEC.md`,
`PLAN.md`, skill, and Codex bridge updates after the design is accepted.

## Current Direction

MPI Kanban should have two layers:

- Human-visible board: `.claude/mpi-kanban/kanban.md`
- Machine-readable coordination state: `.agents/mpi-kanban/state/`

The board remains a human work surface. It can contain tasks owned by the user,
tasks owned by one agent, tasks split across several agents, or tasks waiting
for planning, review, verification, or integration.

The state directory contains the structured coordination data that agents need
to read quickly before editing files. The board should not be overloaded with
machine metadata because the VS Code extension has a locked board contract and
manual extension updates are currently expensive.

The `.claude/mpi-kanban/kanban.md` path remains the board path for compatibility
with the existing Claude plugin and VS Code extension. The coordination state
should use `.agents/mpi-kanban/state/` so Claude and Codex have an agent-neutral
place to read and write the same machine contract.

## Design Goals

- Claude and Codex should have the same coordination abilities.
- The system should support one Claude session, one Codex session, multiple
  Claude sessions, multiple Codex sessions, or any mixed combination.
- Agent sessions should coordinate through shared project files, not private
  chat history.
- Agents should read a small facade first, then follow pointers only for
  relevant task, session, file, or handoff details.
- User-owned work must remain valid. A backlog or active card does not imply an
  agent will touch it.
- Worktrees may still be recommended for filesystem isolation, but they are not
  the coordination mechanism.
- Cleanup should be conservative and run through `mpi-cleanup`.

## Non-Goals For The First Pass

- Do not update the VS Code extension until the agent communication contract is
  stable.
- Do not require a long-lived daemon or permanent orchestrator process.
- Do not require every task to be agent-owned.
- Do not encode coordination state as extra kanban card metadata fields.
- Do not assume the system only coordinates one Claude agent with one Codex
  agent.

## Decisions So Far

- Canonical machine coordination state should live under
  `.agents/mpi-kanban/state/`.
- The human board stays at `.claude/mpi-kanban/kanban.md` for now because the VS
  Code extension watches that path and extension updates are manual.
- New handoffs should move directly to `.agents/mpi-kanban/state/handoffs/`.
  `docs/handoffs/` should be treated as legacy compatibility, not the future
  canonical handoff location.
- Session, task, handoff, claim, and file-state records should use UUIDs as
  primary ids. Human-readable labels belong in metadata, not filenames or ids.
- Active file paths and their claim/state pointers should live directly in
  `state/index.json` so agents do not need to scan `state/files/` before
  editing.
- Default heartbeat timeout: 2 hours.
- Stale claims are reclaimable by an orchestrator or integrator. If no such
  role is active, or the state is uncertain, the agent should ask the user.
- Use lightweight role permissions: orchestrator, planner, implementer,
  reviewer, verifier, integrator, and docs. Roles are behavioral contracts first,
  not hard runtime security boundaries.
- Reviewer is a first-class role. Reviewers inspect diffs/state and mark review
  status, but do not claim write ownership unless explicitly reassigned.
- User-owned/manual kanban tasks remain board-only unless an agent needs to
  coordinate around them.
- `index.json` should stay tiny: active sessions, active claims, blockers,
  integration needs, and pointers.
- Active records should keep a short recent history window, roughly the last
  5-10 events. Older history should move to archive through cleanup.
- Define minimal schemas for all core records in the design pass: `index.json`,
  session records, file/claim records, task records, and handoff records.
- Session records should include explicit allowed actions derived from the
  session's lightweight role.
- First implementation phase should make both Claude and Codex read the same
  shared coordination contract: shared instructions, state layout, schema docs,
  and bridge instructions. Claim lifecycle automation can come after that.
- UUID generation should be handled by helper tooling rather than relying on
  each Markdown skill or agent prompt to improvise ids.
- Handoff migration should use a transition phase: write canonical handoffs to
  `.agents/mpi-kanban/state/handoffs/`, and optionally write a legacy pointer or
  compatibility artifact under `docs/handoffs/` until `mpi-continue` fully
  supports the new location.

## Proposed State Layout

Candidate layout:

```text
.claude/mpi-kanban/
  kanban.md

.agents/mpi-kanban/
  state/
    index.json
    instructions.md
    sessions/
      <session-id>.json
    files/
      <file-key>.json
    tasks/
      <task-id>.json
    handoffs/
      <handoff-id>.json
    archive/
```

`index.json` is the fast facade. Every agent reads it before claiming work or
editing files. It should stay small and point to detailed records instead of
duplicating all context.

`instructions.md` is the shared coordination rulebook. Claude skills and Codex
`AGENTS.md` bridge instructions should both point at it so neither agent family
has special hidden behavior.

`sessions/` records active agent sessions, including agent family, session id,
role, current task, heartbeat, and status.

`files/` records file-level claims, active writers, reviewers, proposers,
completed work, integration requirements, and history.

`tasks/` optionally records machine state for kanban cards or plan tasks when a
card needs structured coordination beyond the human board.

`handoffs/` records machine-readable coordination handoffs. New handoffs should
be written here. `docs/handoffs/` remains compatible legacy/session-resume
history during migration.

`archive/` stores closed or compacted state that should no longer appear in the
active facade.

## Session Model

The coordination unit is an agent session, not a vendor.

Each participating session should have:

- stable session id
- agent family, such as `claude`, `codex`, or future values
- optional display name
- current role, such as orchestrator, planner, implementer, reviewer, verifier,
  integrator, or docs
- current task or kanban card reference when known
- heartbeat timestamp
- status: active, idle, handoff-ready, completed, stale, or closed

The system must work when no orchestrator exists. A session may act as
orchestrator when the user asks it to coordinate the board, but baseline
coordination should be peer-to-peer through shared state files.

## Claim Lifecycle

File and task claims need an explicit lifecycle.

Candidate lifecycle:

1. Session registers or renews itself.
2. Session reads `state/index.json`.
3. Session checks whether intended files or task records are already claimed.
4. Session creates or updates claims for the files/tasks it intends to edit.
5. Session renews heartbeat while working.
6. Session marks file/task work complete or releases the claim when done.
7. Integrator or verifier marks work integrated/verified when needed.
8. Cleanup archives or compacts closed state later.

Claim statuses should distinguish:

- active
- proposed
- blocked
- complete
- needs-review
- needs-integration
- verified
- closed
- stale
- archived

Completing a file claim is not the same as deleting its state. Completed state
may still be needed for review, same-file integration, handoff, or debugging.

## Same-File Coordination

Default rule: one active writer owns a file at a time.

Other sessions may still participate in controlled ways:

- reviewer: reads and comments without editing
- proposer: prepares a suggested change without overwriting the owner
- integrator: resolves competing proposals or handoff work

When another session needs a claimed file, it should choose an explicit path:

- wait
- request handoff
- add a proposal
- become or ask for an integrator
- split work so ownership is no longer overlapping

This should prevent silent same-file conflicts while still allowing useful
parallel work.

## Cleanup And Garbage Collection

`mpi-cleanup` should become the entry point for coordination-state garbage
collection.

It should eventually scan `.agents/mpi-kanban/state/` in addition to plans,
handoffs, archives, and the board.

Candidate cleanup classifications:

- active session
- stale session
- active file claim
- completed file state
- integrated file state
- orphaned state
- superseded handoff or state
- archive candidate
- uncertain

Cleanup should propose actions and wait for approval. It should never delete
active state, and it should not delete archives by default.

## VS Code Extension Direction

The VS Code board should remain the visual representation for the user. It
should eventually be able to display useful coordination signals from
`.agents/mpi-kanban/state/`, such as active claims or blocked integration, but
extension work should wait until the communication contract is stable.

This is especially important because extension release/update work is currently
manual and expensive.

## Phase Split

Phase 1 should focus on making MPI Kanban genuinely usable by both Claude and
Codex through the same shared contract:

- shared coordination instructions
- `.agents/mpi-kanban/state/` layout
- minimal JSON schemas for core records
- UUID helper tooling
- Claude skill references to the shared contract
- Codex `AGENTS.md` bridge references to the shared contract
- compatibility path for current board and handoff behavior
- README installation and testing instructions updated for the new shared
  Claude/Codex contract
- end-to-end install/update test in Claude before Phase 2 starts, because the
  maintainer currently tests by installing the Claude plugin with auto-update
  enabled and the shared `.agents/` contract may change setup expectations

Phase 2 should improve the coordination system after Phase 1 works:

- claim lifecycle automation
- review, verification, and integration workflows
- stale claim reclaim flows
- cleanup and archive handling for state records
- richer orchestrator behavior
- optional VS Code visualization after the communication contract is stable

## Open Questions

Resolved enough for Phase 1 planning:

- Minimal schemas should be defined for `index.json`, sessions, file claims,
  task records, and handoffs. Fields should be just enough for agents to
  identify active sessions, active claims, blockers, integration needs, and
  pointers.
- Role records should carry explicit `allowed_actions` derived from the role.
- UUID generation should use shared helper tooling so Claude and Codex do not
  improvise ids differently.
- During migration, canonical handoffs should be written to
  `.agents/mpi-kanban/state/handoffs/`, with an optional legacy pointer under
  `docs/handoffs/` for old resume flows.

Remaining details can be finalized in the Phase 1 plan/spec work:

- exact JSON field names and examples
- exact role action strings
- exact helper command name
- exact legacy pointer shape

## Next Step

Use `docs/plans/2026-05-17-shared-agent-coordination-phase-1.md` to convert the
accepted design into `SPEC.md`, `PLAN.md`, shared coordination docs, bridge
instructions, README updates, and install/update verification.
