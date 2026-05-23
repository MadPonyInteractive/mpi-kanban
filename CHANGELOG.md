# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

## [0.5.1] - 2026-05-23

### Changed

- Clarified that `mpi-project-setup` and `mpi-project-refresh` may propose new
  `.claude/rules/*.md` files, not only edits to existing rules, when reusable
  project-specific conventions need dedicated briefable rule files.

## [0.5.0] - 2026-05-23

### Added

- Durable project knowledge layer so fresh sessions stop rediscovering
  architecture, conventions, and intent each session. New reference docs under
  `lib/project-knowledge/` cover profile schema, index schema, adoption,
  context-budget indexing, and update/approval rules. Templates added for
  `project-profile.md` and `project-knowledge-index.md`.
- Project mode contract and intentional-engineering guardrails at
  `lib/project-intent/modes.md`. Default mode is `scalable-foundation`.
- Three new skills bringing the surface to 14:
  - `mpi-project-setup` — builds an adoption map and waits for approval before
    writing profile/index.
  - `mpi-project-mode` — records mode-change rationale and migration notes
    without rewriting code.
  - `mpi-project-refresh` — audits drift and runs lightweight mode reassessment.
- Phase 4 plan documents project-knowledge architectural intent and parallel
  implementation strategy.

### Changed

- Existing skills now consume project knowledge when present:
  - `mpi-brainstorm` routes new-project ideas to `mpi-project-setup`.
  - `mpi-create-plan` and `mpi-create-large-plan` read profile/index.
  - `mpi-continue` reads profile/index before the Continue Brief; brief gains
    Project mode and Conventions-in-play fields.
  - `mpi-handoff` records `project_knowledge` pointers in canonical JSON.
  - `mpi-end-session` runs a lightweight refresh on session-touched files.
  - `mpi-cleanup` treats profile/index as active by default and defers drift
    cleanup to `mpi-project-refresh`.
- SPEC, README, AGENTS, PLAN, plugin manifests, and marketplace description
  updated to reflect the 14-skill surface. Kanban schema unchanged.

## [0.4.3] - 2026-05-22

### Changed

- Parallel agents are now the default for eligible large-plan work rather than
  an opt-in extra, with ownership and verification safety gates intact. SPEC and
  README describe parallel investigation and disjoint-ownership parallel batches
  as the default.
- `mpi-brainstorm` and `mpi-create-plan` route parallel-capable work to
  `mpi-create-large-plan`; compact plans never carry parallel batches.
- `mpi-create-large-plan` defaults to parallel investigation sub-agents and to
  writing Parallel Batch sections when ownership is disjoint and verification is
  batch-safe.
- `mpi-continue` routes a valid next batch to `mpi-execute-parallel` instead of
  running it sequentially, and still never spawns workers itself.
- `mpi-execute-parallel` reworded from opt-in to default-for-eligible with
  refusal gates intact.

## [0.4.2] - 2026-05-21

### Added

- Shared coordination lifecycle reference docs under `lib/coordination-ops/`
  covering session registration, task records, file claims, pending file state,
  handoffs, stale reclaim, cleanup, and commit ownership.
- Phase 2 plan documenting local lifecycle automation and the decision to keep
  VS Code visualization deferred while using existing kanban tags as
  display-only summaries.
- README now shows the VS Code companion extension board screenshot.
- GitHub Actions workflow `validate.yml` runs on push/PR to main. Validates plugin
  manifest, marketplace manifest, every `skills/*/SKILL.md` frontmatter, and
  flags any symlink that would break Windows install.
- GitHub Actions workflow `release.yml` runs on `v*` tag push. Re-runs the
  validator, confirms the tag matches `plugin.json` version, extracts the
  matching CHANGELOG section, and creates a GitHub Release.
- `scripts/validate_plugin.py` — local equivalent of the CI validator. Run before
  pushing if you want to catch issues without waiting on CI.
- Native Codex plugin manifest at `.codex-plugin/plugin.json`, pointing to the
  shared `skills/` tree and exposing `$mpi-*` starter prompts.
- `scripts/register_codex_plugin.py` registers a local checkout in a Codex
  marketplace using Python 3.8+ standard-library APIs.

### Changed

- `mpi-continue`, `mpi-execute-parallel`, `mpi-handoff`, `mpi-end-session`, and
  `mpi-cleanup` now reference the shared `.agents/mpi-kanban/state/` lifecycle
  model.
- Codex local registration now rejects plugin paths outside the marketplace root
  instead of writing a marketplace entry Codex will skip.
- `update_live.py` now mirrors the plugin to `~/plugins/mpi-kanban`, registers
  that home-local path, and runs `codex plugin add` so Codex installs the
  current local plugin build.
- README now explains the multi-agent coordination workflow in user-facing
  terms: roles, file claims, pending state, integration, and display-only tags.
- README now documents that local Codex plugin paths must resolve under the home
  directory so the generated marketplace path starts with `./`, and that users
  must run `codex plugin add mpi-kanban@mad-pony-interactive` after registration.
- AGENTS and CLAUDE project instructions now describe the current dual Claude
  cache and Codex install behavior of `update_live.py`.
- Codex direct invocation docs and starter prompts now use the actual
  plugin-prefixed skill names, such as `$mpi-kanban:mpi-continue`.
- Shared coordination docs now distinguish active write claims from pending file
  provenance, and separate file ownership from commit ownership.
- Skill descriptions and docs now distinguish Claude Code slash commands from
  Codex `$mpi-*` skill invocation.

## [0.4.1] - 2026-05-13

### Changed

- Marketplace renamed from `mpi-local` to `mad-pony-interactive` so future
  MadPonyInteractive plugins can live under the same marketplace.
- README rewritten to lead with the public GitHub install path
  (`/plugin marketplace add MadPonyInteractive/mpi-kanban`) instead of local
  directory install.
- `update_live.py` now reads the destination version from `plugin.json` rather
  than hardcoding `0.2.0`, so the cache directory always matches the declared
  plugin version.

### Documented

- VS Code extension fork (`MadPonyInteractive.mpi-kanban`) and its publish
  sequence relative to this plugin.

## [0.4.0] - earlier

### Changed

- Workflow skills redesigned. `mpi-write-plan` split into `mpi-create-plan` and
  `mpi-create-large-plan`. `mpi-execute-next` split into `mpi-execute-parallel`
  and `mpi-continue`. New skill `mpi-cleanup` added for workflow artifact
  garbage collection.

[Unreleased]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.5.1
[0.5.0]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.5.0
[0.4.3]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.3
[0.4.2]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.2
[0.4.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.1
