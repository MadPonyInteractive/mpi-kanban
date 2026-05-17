# Mpi-Kanban Implementation Plan

## Shared coordination Phase 1

- [x] Add shared coordination reference docs for `.agents/mpi-kanban/state/`.
- [x] Define compact examples for `state/index.json`, sessions, tasks, file
  claims, and handoffs.
- [x] Document lightweight roles and `allowed_actions` expectations.
- [x] Add shared UUID helper tooling for coordination record IDs.
- [x] Mark `docs/handoffs/` as legacy compatibility and
  `.agents/mpi-kanban/state/handoffs/` as canonical.
- [x] Update `SPEC.md`, `README.md`, `AGENTS.md`, and workflow skills to point
  at the shared contract.
- [x] Run validation and targeted contradiction searches.

## Shared coordination Phase 2 follow-up

- [ ] Automate session/task/file claim lifecycle under
  `.agents/mpi-kanban/state/`.
- [ ] Add reviewer/verifier/integrator automation.
- [ ] Add stale claim reclaim behavior for orchestrator/integrator roles.
- [ ] Extend `mpi-cleanup` to garbage collect coordination state safely.
- [ ] Decide whether the VS Code extension should visualize active agent state.

## Current redesign tasks

- [x] Replace `mpi-write-plan` with `mpi-create-large-plan`.
- [x] Add `mpi-create-plan` for compact/default plans.
- [x] Replace `mpi-execute-next` with `mpi-continue`.
- [x] Add `mpi-execute-parallel` for explicit parallel batches.
- [x] Add `mpi-cleanup` for conservative workflow artifact cleanup.
- [x] Update `mpi-brainstorm` to route to compact or large plan creation.
- [x] Update `mpi-handoff` with preservation pass and mandatory resume block.
- [x] Update `mpi-brief-rule` to support rule bundles.
- [x] Update plan/kanban/config reference docs for the new workflow.
- [x] Update README and SPEC for the new skill set.

## Validation checklist

- [ ] Confirm old `mpi-write-plan` / `mpi-execute-next` references are gone or
  only appear in migration notes.
- [ ] Confirm all skill frontmatter names match folder names.
- [ ] Confirm plugin metadata lists the current skills.
- [ ] Run `update_live.py` after review to copy the plugin into the live cache.
- [ ] In a test project, run brainstorm -> create-plan -> continue -> handoff
  -> continue -> end-session.
- [ ] Test `mpi-execute-parallel` refusal on a plan without a valid
  `## Parallel Batch`.
- [ ] Test `mpi-cleanup` proposal mode without approval.
