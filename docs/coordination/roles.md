# Coordination Roles

Roles are lightweight behavior contracts, not permission enforcement. They tell
agents what they are expected to do unless the user or an orchestrator assigns a
different role.

## Orchestrator

Owns task decomposition, assignment, and conflict resolution. May reclaim stale
claims after the default heartbeat timeout when the situation is clear.
Coordinates through `.agents/mpi-kanban/state/`; kanban updates are only
user-facing summaries.

Default actions: `coordinate`, `assign`, `reclaim_stale`, `handoff`.

## Planner

Owns plan shape and task breakdown. Does not write implementation files unless
also assigned as implementer.

Default actions: `read`, `write_plan`, `update_kanban`.

## Implementer

Owns scoped code or doc changes for assigned files. Must respect active file
claims and update handoff or plan state when stopping mid-work.
Completing or releasing a file claim does not grant later commit ownership; the
closing or integrating session owns the final commit summary.

Default actions: `read`, `claim_files`, `edit_owned_files`, `verify`, `handoff`.

## Reviewer

First-class review role. Reads and comments by default. Does not take write
ownership unless explicitly reassigned.

Default actions: `read`, `review`, `recommend_changes`.

## Verifier

Runs checks and reports results. May edit only verification artifacts or files
explicitly assigned for fixes.

Default actions: `read`, `run_checks`, `report`.

## Integrator

Owns merging competing proposals and resolving claim conflicts. May reclaim
stale claims when intent is clear; uncertain ownership cases ask the user.
Before committing integrated work, rereads current coordination state and Git
state so the commit message describes the actual final workspace snapshot.

Default actions: `read`, `claim_files`, `integrate`, `reclaim_stale`, `verify`.

## Docs

Owns documentation updates and preservation notes. Does not alter code or rule
files unless explicitly assigned.

Default actions: `read`, `write_docs`, `update_plan`.
