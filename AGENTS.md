# Codex Entry Point for mpi-kanban

This repository is the source for the Mpi-Kanban Agent Skills pack.
Distribution is npx-only through skills.sh:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

The pack is all-or-nothing. The workflow skills depend on `skills/mpi-lib/`;
partial installs are unsupported.

## Source of Truth

Read these files only as needed:

- `SPEC.md` before changing workflow behavior.
- `PLAN.md` before continuing implementation work.
- `README.md` and `docs/install.md` before changing user-facing install docs.
- `skills/mpi-lib/` before changing shared references.
- `docs/plans/2026-05-23-cross-agent-skills-distribution-phase-7.md` for the
  npx-only packaging refactor.

If `SPEC.md` and `PLAN.md` disagree, ask the user before choosing an
interpretation.

## Skill Layout

- Workflow skills live under `skills/mpi-*/SKILL.md`.
- `skills/mpi-lib/` is a support skill containing shared reference docs and
  the board bootstrap template.
- Skill-private templates live inside the consuming skill folder, such as
  `skills/mpi-project-setup/templates/`.

Consuming skills locate `mpi-lib` by checking standard Agent Skills install
paths such as `~/.agents/skills/mpi-lib`, `.agents/skills/mpi-lib`,
`~/.claude/skills/mpi-lib`, and `.claude/skills/mpi-lib`.

## Companion VS Code Extension

The paired VS Code extension lives next to this repository:

- Checkout: `C:\AI\Mpi\Plugins\mpi-kanban-vscode`
- GitHub: `https://github.com/MadPonyInteractive/mpi-kanban-vscode`
- Marketplace ID: `MadPonyInteractive.mpi-kanban`

The extension watches `.agents/mpi-kanban/kanban.md`. Do not change the board
path or schema unless the extension contract also changes.

## Coordination State

The human-visible board remains:

- `.agents/mpi-kanban/kanban.md`

The canonical machine-readable coordination state lives under:

- `.agents/mpi-kanban/state/`

When coordination state is relevant, read `state/index.json` first. Lifecycle
references live under `skills/mpi-lib/coordination-ops/`.

File claims with status `claimed` are active write locks. Completed or
released file ownership does not equal commit ownership; reread current state
before committing or integrating.

## Project Knowledge

Durable per-project knowledge lives outside `state/`:

- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`

When these files exist, read the profile and the matching topic block before
deep-loading rules, docs, or memory. Mode contracts and update rules live under
`skills/mpi-lib/project-intent/` and `skills/mpi-lib/project-knowledge/`.

## Read-Only Boundary

For normal Codex work outside this repository, treat this plugin directory as
read-only reference material. Edit this repository only when the user asks to
modify Mpi-Kanban itself.

