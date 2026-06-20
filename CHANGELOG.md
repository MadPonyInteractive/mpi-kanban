# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.5] - 2026-06-20

### Changed

- Made the `mpi-continue` post-implementation gate conditional. Plans now
  declare `**Verify mode:**` (`auto` or `user-ux`) in their `## Verification`
  section. For an `auto` card whose self-verification passed, `mpi-continue`
  reports the passing result and continues without stopping for the user; it
  stops only when the card has a `user-ux` surface to judge in the running app,
  or when self-verification failed or could not run. Untagged or legacy plans
  default to `auto`. This removes the per-step "press 1 to verify" prompt for
  work the agent has already verified.
- Taught `mpi-create-plan` and `mpi-create-large-plan` to set `Verify mode:` on
  the plan and, in `scalable-foundation` mode, to front-load architecture,
  pattern, and library decisions and push back before a card is implementable,
  so implementation does not stop mid-flight to ask.
- Added a proactive engineering bar to the `scalable-foundation` mode contract:
  enforce strong patterns where they pay off and proactively name
  future-proofing concerns at planning time.
- `mpi-end-session` now treats its own invocation as the user's explicit request
  to commit the session's touched files, so it commits without deferring to a
  general "ask before committing" instruction. It still never pushes and still
  will not commit over a contested file claim or in `nimbalyst` mode.

## [0.8.4] - 2026-06-10

### Changed

- Added direct task-card state update triggers to `mpi-continue` so requests
  such as `set MPI-42 to validating` load the right workflow instead of
  relying on agents to rediscover board rules from memory or grep.
- Promoted the card-write preflight into the card-writing workflows and
  `task-board-ops/mutate.md`: agents must read `_schema.md` and `mutate.md`
  before writing `column`, `maturity`, or `status`, and must write
  `validation.md` before setting `maturity: "validating"`.
- Clarified that `mpi-lib` reference files are safe for agents to read
  directly, even though `mpi-lib` itself is not a user workflow.

## [0.8.3] - 2026-06-08

### Changed

- Tightened the task-card maturity contract for labels agents were still
  inventing, including `Validated`, `validated`, `validation`, `spec`, and
  other process words. `moveTask` now documents column movement as maturity
  reconciliation, `read.md` reports invalid maturity drift, and refresh/repair
  guidance calls these out as board repair findings.
- Added validator coverage to keep the maturity enum and common invalid
  examples documented in the spec, shared task-board references, and default
  project profile template.

## [0.8.2] - 2026-06-05

### Changed

- Surface the `maturity` enum at write time so agents stop guessing it.
  `mpi-lib/task-board-ops/mutate.md` now opens with the allowed values
  (`idea`, `planned`, `in-progress`, `validating`, `complete`), the column
  coherence rules, and an explicit reject-list: `active`, `accepted`, `done`,
  `deferred`, `implementing`, and `implementation` are not maturity values.
- `mpi-lib/templates/project-profile.md` gains a "Task Board Card Contract"
  section with the maturity-by-column table, so the enum is visible in a
  read-first doc without opening the shared library.
- `mpi-end-session` now auto-corrects an invalid or column-incoherent
  `maturity` on a touched card before any board move, printing a one-line note.

### Fixed

- Cards that agents marked with non-enum maturity values (for example
  `deferred`, `active`, or `implementation`) rendered as red invalid cards in
  the VS Code board. The guidance above prevents those writes; a `doing` card
  under active work is `in-progress` (yellow), not `implementation` or `idea`.

## [0.8.1] - 2026-06-05

### Changed

- `mpi-create-plan`, `mpi-continue`, and `mpi-lib/task-board-ops/mutate.md` now
  enforce the `To do -> Doing -> Done` lifecycle: implementation must run through
  `mpi-continue`/`beginImplementation`, which moves a card into `Doing` before
  any edit. Inline implementation from a `todo` card is no longer allowed
  (MPI-18).
- `mpi-end-session` auto-corrects a `todo` card that carries real implementation
  work through `Doing` (with a one-line warning) before moving it to `Done`,
  instead of skipping the `Doing` phase (MPI-18).
- Retired legacy Markdown from the main product surface: `README.md`, `SPEC.md`,
  and `mpi-init` now present `kanban.md` only as a brief migration/compatibility
  note, not a primary workflow (MPI-15).

## [0.8.0] - 2026-05-31

### Added

- Added `mpi-message` for same-filesystem async coordination messages between
  agents, sessions, roles, tasks, files, users, and explicit peer workspaces.
- Added shared `mpi-lib` message and workspace-discovery references for
  `.agents/mpi-kanban/state/messages/` and VS Code `.code-workspace` scope.
- Added a message-bus smoke harness and validator checks for message records,
  open-message index pointers, claim negotiation, peer routing, and resolved
  message archival.

### Changed

- Workflow skills now check relevant open messages only at safe async
  boundaries such as continue, parallel execution, handoff, cleanup, and
  end-session.
- Documentation now describes the v0.8.0 model: one Kanban root per work
  context, with separate roots communicating through explicit same-machine
  peer messages.

## [0.7.2] - 2026-05-31

### Changed

- Folded read-only card lookup into `mpi-continue` instead of shipping a
  standalone `mpi-show` skill, keeping the installable pack at 14 skills for
  `npx skills`.

## [0.7.1] - 2026-05-31

### Changed

- Tightened post-migration cleanup so JSON-board projects treat legacy
  `kanban.md` files as moved/tombstoned compatibility artifacts, and refresh
  validation flags boot docs that still route active work through Markdown.

### Added

- `mpi-show` read-only workflow for natural board-card lookup requests such as
  "what is MPI-5?" or "show the <title> card".

## [0.7.0] - 2026-05-31

### Added

- JSON task board contract with `.agents/mpi-kanban/board.json`,
  `.agents/mpi-kanban/events.jsonl`, and task workspaces under
  `.agents/mpi-kanban/tasks/<id>/`.
- Shared `mpi-lib/task-board-ops/` references for JSON board schema, read,
  mutation, migration, and validation behavior.
- `mpi-nimbalyst-sync` for Nimbalyst source-of-truth mode, detection, and
  explicit import/export snapshot boundaries.
- Validator coverage for JSON board templates and live board/task workspace
  consistency.

### Changed

- `mpi-init` is now the single project onboarding/adoption skill. It owns JSON
  board bootstrap or migration, profile/index creation, project mode selection,
  interop mode initialization, and freeform backlog import.
- `mpi-project-refresh` is now the existing-project maintenance skill. It owns
  project knowledge drift checks, board/state consistency, and later project
  mode changes.
- Workflow skills now treat `board.json` as the primary human board once it
  exists, with fixed `To do`, `Doing`, and `Done` columns.
- Legacy Markdown boards remain readable as migration inputs or snapshots, not
  competing live sources of truth after JSON-board migration.
- Nimbalyst interop docs and workflow references map tracker state into the
  JSON board model instead of restoring legacy MPI lifecycle columns.
- Validator interop checks now use tracked templates rather than ignored local
  `.agents/` state, so release validation is reproducible from a clean checkout.

### Removed

- Retired separate `mpi-project-setup` and `mpi-project-mode` skills before
  release; their behavior is folded into `mpi-init` and `mpi-project-refresh`.

## [0.6.1] - 2026-05-24

### Changed

- Documentation updates and project migration housekeeping.

## [0.6.0] - 2026-05-23

### Added

- `mpi-lib` support skill carrying shared reference docs for the all-or-nothing
  Agent Skills pack.
- `skills.sh.json` pack metadata and `docs/install.md` npx install docs.

### Changed

- Distribution is now npx-only through skills.sh:
  `npx skills add MadPonyInteractive/mpi-kanban --all -y -g`.
- Workflow skills now resolve shared references through the sibling `mpi-lib`
  skill instead of plugin-root variables.

### Removed

- Removed Claude Code plugin manifest and Codex plugin/marketplace bundle.
- Removed Kilo-specific generated skill packaging, install docs, marketplace
  runbook, and template. Existing users should reinstall with:
  `npx skills add MadPonyInteractive/mpi-kanban --all -y -g`.

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

[Unreleased]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.5...HEAD
[0.8.5]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.4...v0.8.5
[0.8.4]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.3...v0.8.4
[0.8.3]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.7.2...v0.8.0
[0.7.2]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.7.2
[0.7.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.7.1
[0.7.0]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.7.0
[0.6.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.6.1
[0.6.0]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.6.0
[0.5.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.5.1
[0.5.0]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.5.0
[0.4.3]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.3
[0.4.2]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.2
[0.4.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.1
