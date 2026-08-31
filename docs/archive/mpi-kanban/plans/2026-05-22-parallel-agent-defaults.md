# Parallel Agent Defaults

## Current State

The plugin already supports parallel work, but the workflow defaults are
conservative:

- `mpi-create-large-plan` encourages parallel sub-agents during investigation
  only "where useful" and treats parallel implementation as opt-in.
- `mpi-execute-parallel` can run explicit `## Parallel Batch` sections with
  worker sub-agents, disjoint ownership, and verification gates.
- `mpi-continue` refuses parallel implementation and redirects to
  `mpi-execute-parallel` only when a plan already has an explicit batch.
- The current project-knowledge Phase 4 plan is about durable project context,
  not parallel-agent execution policy.

This plan changes the default behavior for suitable work: agents should spawn
multiple sub-agents for independent investigation, and large plans should
include executable parallel batches whenever implementation ownership can be
made disjoint and verifiable.

## Completed

- [ ] Nothing yet.

## Remaining Work

## Phase 1: Policy Contract

- [ ] Update the shared specification and user-facing docs so parallel agent
  use is the default for independent investigation and clearly separable large
  implementation work. **Verify:** `SPEC.md` and `README.md` describe the same
  default behavior, while still requiring explicit ownership and verification
  before implementation workers are spawned.
- [ ] Clarify the distinction between "default to parallel when eligible" and
  "never parallelize unsafe work." **Verify:** docs still refuse overlapping
  ownership, missing `Ownership:`, missing `**Verify:**`, unresolved
  dependencies, and compact-plan work.

## Parallel Batch: Planning Skill Defaults

- [ ] Update `mpi-brainstorm` routing so ideas likely to benefit from parallel
  implementation are sent to `mpi-create-large-plan`, not compact planning.
  Ownership: `skills/mpi-brainstorm/SKILL.md`. Briefings: none. **Verify:**
  brainstorm end-state wording mentions parallel implementation eligibility as
  a reason to choose the large-plan path.
- [ ] Update `mpi-create-plan` so normal compact plans redirect to
  `mpi-create-large-plan` when independent parallel implementation is likely.
  Ownership: `skills/mpi-create-plan/SKILL.md`. Briefings: none. **Verify:**
  compact planning does not gain parallel-batch syntax and still remains the
  one-flow default for genuinely small work.
- [ ] Update `mpi-create-large-plan` so it defaults to spawning read-only
  investigation sub-agents for independent investigation areas and defaults to
  writing `## Parallel Batch` sections for disjoint implementation tasks.
  Ownership: `skills/mpi-create-large-plan/SKILL.md`. Briefings: none.
  **Verify:** the skill tells planners to include parallel batches whenever
  ownership is clear, and to explain why no batch was created when work looks
  large but cannot be split safely.

## Parallel Batch: Execution Routing

- [ ] Update `mpi-continue` so, when the next eligible unit is a valid
  `## Parallel Batch`, it recommends or routes to `mpi-execute-parallel`
  before offering sequential implementation. Ownership:
  `skills/mpi-continue/SKILL.md`. Briefings: none. **Verify:** continue still
  does not spawn workers directly, but its Continue Brief makes the parallel
  path the default for eligible batches.
- [ ] Update `mpi-execute-parallel` wording from "opt-in only" to "eligible
  explicit batches run through this skill by default," while preserving strict
  refusal gates. Ownership: `skills/mpi-execute-parallel/SKILL.md`.
  Briefings: none. **Verify:** the skill still aborts on overlapping ownership,
  missing metadata, active write claims, or intra-batch dependencies.

## Phase 2: Plan Shape and Reference Alignment

- [ ] Update plan-shape reference docs so large plans prefer parallel batches
  when independent work exists. **Verify:** `lib/plan-ops/_shape.md` and
  `lib/plan-ops/read.md` remain consistent with the skill wording.
- [ ] Update `PLAN.md` if this work should be tracked in the repository-level
  implementation checklist. **Verify:** this parallel-defaults plan is listed
  separately from project-knowledge Phase 4 and does not imply Phase 4 is
  blocked.

## Phase 3: Validation

- [ ] Run plugin validation. **Verify:** `python scripts/validate_plugin.py`
  passes.
- [ ] Run targeted contradiction searches for old parallel policy language.
  **Verify:** remaining uses of "opt-in", "where useful", and "do not run
  parallel implementation" are either removed, narrowed to unsafe cases, or
  intentionally preserved for `mpi-continue` direct worker spawning.
- [ ] Review the final docs for accidental overreach. **Verify:** agents
  default to parallelism only when work is independent, ownership is explicit,
  and verification is batch-safe.

## Plan Drift

- None yet.

## Verification

Before this plan is complete:

1. Large planning defaults to parallel investigation for independent codebase
   questions.
2. Large planning defaults to explicit `## Parallel Batch` sections when
   implementation tasks have disjoint ownership and batch-safe verification.
3. Compact planning redirects parallel-capable work to large planning.
4. Continue routes eligible parallel batches to `mpi-execute-parallel`.
5. `mpi-execute-parallel` remains the only worker-spawning implementation path
   and keeps strict refusal gates.
6. Specs, README, skill docs, and plan references agree on the new default.

## Preservation Notes

- Keep project-knowledge Phase 4 separate. That phase can later consume the
  revised parallel defaults when it updates planning and continue skills to
  read project profiles and knowledge indexes.
- Do not weaken the existing file-claim and ownership model under
  `.agents/mpi-kanban/state/`.
- Do not run `update_live.py` unless the user explicitly asks to update the
  installed live plugin copy after validation.
