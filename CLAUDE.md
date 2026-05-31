# Mpi-Kanban Agent Skills Pack

Mpi-Kanban is distributed as an all-or-nothing Agent Skills pack through
skills.sh / `npx skills`.

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

Claude Code and Codex plugin manifests are intentionally removed. Do not
restore `.claude-plugin/`, `.codex-plugin/`, Codex marketplace bundles, or
Kilo-specific generated skill trees unless the user explicitly reverses the
Phase 7 distribution decision.

## Companion VS Code Extension

The paired VS Code extension lives next to this repository:

```text
C:\AI\Mpi\Plugins\mpi-kanban-vscode
```

It is published from:

```text
https://github.com/MadPonyInteractive/mpi-kanban-vscode
```

The extension name is `Mpi-Kanban` and the VS Code Marketplace identity should
be `MadPonyInteractive.mpi-kanban`. It is a fork of
`holooooo.markdown-kanban`; keep the original MIT copyright in the extension
`LICENSE` and keep fork attribution in the extension `NOTICE`.

The fork is moving to the JSON task board contract at
`.agents/mpi-kanban/board.json` plus `.agents/mpi-kanban/tasks/<id>/`. Legacy
`.agents/mpi-kanban/kanban.md` boards are migration inputs or snapshots, not
the primary live board once `board.json` exists.

## Source of Truth

- [SPEC.md](./SPEC.md) - design source of truth.
- [PLAN.md](./PLAN.md) - phased implementation state.
- [README.md](./README.md) and [docs/install.md](./docs/install.md) -
  user-facing installation and usage.
- [skills/mpi-lib/](./skills/mpi-lib/) - shared references consumed by the
  workflow skills.

If SPEC and PLAN disagree, ask the user before choosing.

## Hard Constraints

- Do not add task-board columns or task-card fields beyond the SPEC board
  contract; the VS Code extension expects the fixed JSON board schema.
- Skills are pure Markdown. Shared reference docs live in `skills/mpi-lib/`.
- Do not use `${CLAUDE_PLUGIN_ROOT}`, Claude `!` injection, Codex plugin
  manifests, or plugin-scoped install assumptions in workflow skills.
- The pack is all-or-nothing. Every consuming skill must fail clearly when
  `mpi-lib` is missing and tell the user to reinstall with `npx skills add
  MadPonyInteractive/mpi-kanban --all -y -g`.
- Project onboarding uses `mpi-init`; project maintenance and mode changes use
  `mpi-project-refresh`. Do not restore separate `mpi-project-setup` or
  `mpi-project-mode` skills unless the user explicitly reverses the lifecycle
  simplification decision.

## Maintenance

- Run `python scripts/validate_plugin.py` before release.
- Release by updating `CHANGELOG.md`, tagging `v<version>`, and pushing the
  tag. `.github/workflows/release.yml` creates the GitHub Release.
- Use `npx skills add MadPonyInteractive/mpi-kanban --all -y -g` for local
  smoke testing after push, or the supported local-path `npx skills` flow when
  testing a checkout.

## Working Directory

This repository lives at:

```text
C:\AI\Mpi\Plugins\Mpi-Kanban
```

Do not commit anything to other projects from this build. CubricStudio and
other workspaces are integration-test targets only.

