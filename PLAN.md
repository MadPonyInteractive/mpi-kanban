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

- [x] Add a native Codex plugin manifest and metadata while preserving the
  existing Claude plugin manifest.
- [x] Keep the shared `skills/` tree as the workflow source for both Claude and
  Codex.
- [x] Make Codex invocation native through `$mpi-*` skills and natural language,
  not Claude-style slash commands.
- [x] Update README, SPEC, AGENTS, validation, and live-copy guidance for the
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

## Parallel agent defaults

Plan file: `docs/plans/2026-05-22-parallel-agent-defaults.md`. Independent of the
project-knowledge Phase 4 work; does not block or imply Phase 4.

- [x] Make parallel use the default for eligible work in `SPEC.md` and
  `README.md`, keeping ownership/verification gates.
- [x] Default planning skills to parallel: brainstorm routing, create-plan
  redirect, create-large-plan investigation + batch defaults.
- [x] Route eligible batches through `mpi-continue` to `mpi-execute-parallel`;
  reword `mpi-execute-parallel` from opt-in to default-for-eligible.
- [x] Align `lib/plan-ops/_shape.md` and `read.md` with the new default.
- [ ] Run `validate_plugin.py` and the parallel-policy contradiction sweep.

## Validation checklist

- [x] Confirm old `mpi-write-plan` / `mpi-execute-next` references are gone or
  only appear in migration notes.
- [x] Confirm all skill frontmatter names match folder names.
- [x] Confirm plugin metadata lists the current skills.
- [ ] Run `update_live.py` after review to copy the plugin into the live cache.
- [ ] In a test project, run brainstorm -> create-plan -> continue -> handoff
  -> continue -> end-session.
- [ ] Test `mpi-execute-parallel` refusal on a plan without a valid
  `## Parallel Batch`.
- [ ] Test `mpi-cleanup` proposal mode without approval.

## Project knowledge and architectural intent Phase 4

Plan file: `docs/plans/2026-05-20-project-knowledge-architectural-intent-phase-4.md`.

- [x] Add `lib/project-intent/modes.md` (mode contracts, default-mode rule,
  intentional engineering guardrails).
- [x] Add `lib/project-knowledge/` reference docs (`profile-schema.md`,
  `index-schema.md`, `adoption.md`, `indexing.md`, `updates.md`).
- [x] Add `templates/project-profile.md` and
  `templates/project-knowledge-index.md`.
- [x] Add `mpi-project-setup`, `mpi-project-mode`, and `mpi-project-refresh`
  skills.
- [x] Wire `mpi-brainstorm`, `mpi-create-plan`, `mpi-create-large-plan`,
  `mpi-continue`, `mpi-handoff`, `mpi-end-session`, and `mpi-cleanup` to
  the project profile/knowledge index.
- [x] Update `SPEC.md`, `README.md`, `AGENTS.md`, and `PLAN.md` for the new
  skill set and project knowledge contract.
- [ ] Run `python scripts/validate_plugin.py` and the project-knowledge
  contradiction sweep.
- [ ] Run `update_live.py` only after Phase 4 is reviewed and the user
  explicitly asks for the live cache update.
