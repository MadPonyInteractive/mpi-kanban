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

## Plugin listing and marketplace compliance Phase 5

- [x] Add the marketplace bundle directory required by plugin submission checks:
  `plugins/MadPonyInteractive/mpi-kanban/`.
- [x] Add `plugins/MadPonyInteractive/mpi-kanban/plugins.json` with complete
  plugin metadata for Codex marketplace consumption.
- [x] Add an SVG icon in the bundle as required by the submission schema.
- [x] Point the Codex plugin interface at the icon using
  `interface.composerIcon`.
- [x] Extend plugin validation to check the Codex marketplace bundle metadata,
  icon asset, and `composerIcon` path.
- [x] Add the public Codex marketplace manifest at
  `.agents/plugins/marketplace.json`.
- [x] Document the public Codex install/update flow with
  `codex plugin marketplace add`, `marketplace upgrade`, and
  `codex plugin add`.
- [x] Keep `scripts/register_codex_plugin.py` documented as a local development
  helper, not the public install path.
- [x] Record the Superpowers / Kilo generator lesson for a future Codex target
  adapter: shared workflow source, runtime-native packaging, and target-specific
  overlays instead of bridges.

## Future multi-agent packaging adapters

Follow-up idea from comparing `obra/superpowers` and the Phase 6 Kilo generator:
keep `skills/mpi-*/SKILL.md` canonical for now, but treat Kilo, Codex,
OpenCode, and future systems as target adapters around that source.

- Kilo currently needs generated self-contained skills because marketplace pulls
  one skill folder at a time.
- Codex does not need that same inlining path today; it consumes the shared
  `skills/` tree through `.codex-plugin/plugin.json`.
- A future `build_agent_skills.py --target kilo|codex|opencode` could reuse
  discovery, validation, and overlay metadata while keeping each runtime native.
- Prefer Option C first: shared Markdown plus per-runtime overlays. Reconsider a
  neutral source format only if overlays become the real source of truth.

## KiloCode plugin packaging Phase 6

Plan file: `docs/plans/2026-05-23-kilocode-plugin-packaging-phase-6.md`.

Superseded by Phase 7 before release. The Kilo-specific generator,
marketplace docs, and template were removed in favor of the npx-only
skills.sh distribution path.

- [x] Authoring audit: confirm all 14 skills meet Kilo `name`/`description`
  schema and map `${CLAUDE_PLUGIN_ROOT}` sibling dependencies.
- [x] Build `scripts/build_kilo_skills.py` to inline siblings into a portable
  `skills-kilo/` tree (`skills-kilo/` is gitignored; rebuilt at release time).
- [x] Audit generated tree: zero residual `${CLAUDE_PLUGIN_ROOT}` refs, no
  missing/cycle inline markers, reasonable per-skill size.
- [x] Add `docs/kilocode-install.md`, `templates/kilo.jsonc`, AGENTS.md pointer.
- [x] Add `docs/kilocode-marketplace-submission.md` runbook.
- [ ] Submit marketplace PR to `Kilo-Org/kilo-marketplace` (runbook step 4-6).
- [x] Extend `scripts/validate_plugin.py` with `validate_kilo_assets()` and
  `validate_kilo_skill_limits()`, additive beside the Codex marketplace bundle
  validation committed in `eb0362e`.
- [ ] Append Phase 6 SPEC section and project-profile architecture note.
- [x] Superseded by Phase 7 before release; no Phase 6 release tag.

## Cross-agent skills distribution Phase 7

Plan file: `docs/plans/2026-05-23-cross-agent-skills-distribution-phase-7.md`.

- [x] Confirm hard-drop release strategy: npx-only, all-or-nothing.
- [x] Add `skills/mpi-lib/` support skill with shared reference docs.
- [x] Rewrite workflow skills to resolve shared docs through `mpi-lib`.
- [x] Move runtime templates into skill folders.
- [x] Add `skills.sh.json`.
- [x] Replace Kilo-specific install docs with `docs/install.md`.
- [x] Remove Claude/Codex plugin manifests, Codex marketplace bundle, Kilo
  generator/docs/template, and live-copy bridge.
- [x] Rewrite README, AGENTS, CLAUDE, SPEC, project profile, and knowledge
  index for npx-only distribution.
- [x] Rewrite validator for the universal skill pack.
- [x] Run validator and contradiction sweeps.
- [ ] Smoke test npx install and one workflow skill in Claude, Kilo, and Codex.
- [ ] Release `0.7.0`.

## Skill onboarding simplification and release readiness

Plan file: `docs/plans/2026-05-31-skill-onboarding-simplification.md`.

- [x] Re-evaluate `mpi-init`, `mpi-project-setup`, `mpi-project-refresh`, and
  `mpi-project-mode` before changing behavior.
- [x] Consolidate project onboarding around one clear init/adoption skill and
  one clear refresh/update skill.
- [x] Fix clean-checkout validator behavior.
- [x] Align README, install docs, SPEC, skill metadata, and changelog with the
  consolidated lifecycle model.
- [x] Sync event type docs with the VS Code extension.
- [x] Run validator and contradiction searches.
- [x] Run changelog extraction.
- [x] Run local `npx skills add . --all -y -g` and `npx skills add . -l`
  smoke tests.
