# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- README now explains the multi-agent coordination workflow in user-facing
  terms: roles, file claims, pending state, integration, and display-only tags.
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

[Unreleased]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.1
