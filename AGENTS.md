# Agent Entry Point for mpi-kanban

This repository is the source for the Mpi-Kanban Claude Code plugin. It ships
its skills, hooks, and agents from one manifest at
`.claude-plugin/plugin.json`, published through the marketplace entry in
`.claude-plugin/marketplace.json`:

```text
/plugin marketplace add MadPonyInteractive/mpi-kanban
/plugin install mpi-kanban@mad-pony-interactive
```

The plugin is all-or-nothing. The workflow skills depend on
`skills/mpi-lib/`.

## Source of Truth

Read these files only as needed:

- `SPEC.md` before changing workflow behavior.
- `PLAN.md` before continuing implementation work.
- `README.md` and `docs/install.md` before changing user-facing install docs.
- `skills/mpi-lib/` before changing shared references.
- `docs/migrating-to-1.0.md` before advising a project still running the
  pre-1.0 skills pack.
- `docs/archive/mpi-kanban/plans/2026-05-31-skill-onboarding-simplification.md` before changing
  project lifecycle commands or skill surface.
- `docs/archive/mpi-kanban/plans/2026-05-23-cross-agent-skills-distribution-phase-7.md` is history
  only. It describes the npx-only packaging refactor that v1.0 reversed.

If `SPEC.md` and `PLAN.md` disagree, ask the user before choosing an
interpretation.

## Plugin Layout

- Workflow skills live under `skills/mpi-*/SKILL.md`. There are twelve, plus
  the `mpi-lib` support skill.
- Enforcement hooks live under `hooks/`, registered by `hooks/hooks.json`.
  Every hook must exit 0 when the project has no board, and every hook has a
  case in `scripts/smoke_hooks.py`.
- Read-only agents live under `agents/`. A skill that dispatches one must ship
  it; `scripts/validate_plugin.py` checks that.
- The marketplace entry uses `source: "./"`, so the whole repository becomes
  `${CLAUDE_PLUGIN_ROOT}`. `scripts/` is maintainer tooling; no shipped skill
  invokes it. Runtime scripts live in `skills/mpi-lib/scripts/`.
- `skills/mpi-lib/` is a support skill containing shared reference docs and
  board/task templates.
- Shared templates live in `skills/mpi-lib/templates/`.

Consuming skills read `mpi-lib` references at
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/<sub/path>.md`. The placeholder is
substituted anywhere it appears in skill and agent content, so there is no
discovery probe.

## Companion VS Code Extension

The paired VS Code extension lives next to this repository:

- Checkout: `C:\AI\Mpi\Plugins\mpi-kanban-vscode`
- GitHub: `https://github.com/MadPonyInteractive/mpi-kanban-vscode`
- Marketplace ID: `MadPonyInteractive.mpi-kanban`

The extension is moving to the JSON task board contract at
`.agents/mpi-kanban/board.json` plus `.agents/mpi-kanban/tasks/<id>/`.
Legacy `.agents/mpi-kanban/kanban.md` boards are migration inputs or snapshots,
not the primary live board once `board.json` exists.

## Coordination State

The human-visible task board is:

- `.agents/mpi-kanban/board.json`
- `.agents/mpi-kanban/tasks/<id>/`

The canonical machine-readable coordination state lives under:

- `.agents/mpi-kanban/state/`

When coordination state is relevant, read `state/index.json` first. Lifecycle
references live under `skills/mpi-lib/coordination-ops/`.

Do not reuse `.agents/mpi-kanban/state/tasks/` for human board cards; it is
reserved for UUID-based coordination task records. File claims with status
`claimed` are active write locks. Completed or released file ownership does not
equal commit ownership; reread current state before committing or integrating.

## Project Knowledge

Durable per-project knowledge lives outside `state/`:

- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`

When these files exist, read the profile and the matching topic block before
deep-loading rules, docs, or memory. Mode contracts and update rules live under
`skills/mpi-lib/project-intent/` and `skills/mpi-lib/project-knowledge/`.

## Read-Only Boundary

For normal work outside this repository, treat this plugin directory as
read-only reference material. Edit this repository only when the user asks to
modify Mpi-Kanban itself.

