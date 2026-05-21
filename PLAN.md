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

- [x] Automate session/task/file claim lifecycle under
  `.agents/mpi-kanban/state/`.
- [x] Add reviewer/verifier/integrator automation.
- [x] Add stale claim reclaim behavior for orchestrator/integrator roles.
- [x] Extend `mpi-cleanup` to garbage collect coordination state safely.
- [x] Defer richer VS Code extension visualization; use existing tags for now.

## Dual Claude/Codex plugin packaging Phase 3

- [ ] Add a native Codex plugin manifest and metadata while preserving the
  existing Claude plugin manifest.
- [ ] Keep the shared `skills/` tree as the workflow source for both Claude and
  Codex.
- [ ] Make Codex invocation native through `$mpi-*` skills and natural language,
  not Claude-style slash commands.
- [ ] Update README, SPEC, AGENTS, validation, and live-copy guidance for the
  dual-package model.
- [ ] Smoke-test `mpi-cleanup` and `mpi-end-session` in Codex, then rerun Claude
  plugin validation.

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
