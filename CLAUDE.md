# Mpi-Kanban — Claude Code Plugin

A Claude Code plugin that bundles the MPI workflow skills (`brainstorm`, `create-plan`,
`create-large-plan`, `continue`, `execute-parallel`, `end-session`, `cleanup`, `archive`,
`handoff`, `brief-rule`) and drives a per-project Kanban board (`kanban.md`) rendered by
the `MadPonyInteractive.mpi-kanban` VS Code extension fork.

## Companion VS Code extension

The paired VS Code extension lives next to this plugin at:

```
C:\AI\Mpi\Plugins\mpi-kanban-vscode
```

It is published from:

```
https://github.com/MadPonyInteractive/mpi-kanban-vscode
```

The extension name is `Mpi-Kanban` and the VS Code Marketplace identity should
be `MadPonyInteractive.mpi-kanban`. It is a fork of
`holooooo.markdown-kanban`; keep the original MIT copyright in the extension
`LICENSE` and keep fork attribution in the extension `NOTICE`.

The fork intentionally watches only the workspace MPI board at
`.claude/mpi-kanban/kanban.md`. Do not reintroduce generic Markdown file
switching unless the MPI workflow spec changes.

Machine-readable Claude/Codex coordination state is separate from the board and
lives under `.agents/mpi-kanban/state/`. Do not add agent coordination details
as new board columns or metadata fields.

The extension can be published before this agent plugin becomes universal for
Claude Code and Codex because the extension depends only on the stable kanban
file contract.

## Source of truth

- [SPEC.md](./SPEC.md) — full design spec. Read in full before changing behavior.
- [PLAN.md](./PLAN.md) — phased build to-do list.

If SPEC and PLAN disagree, ask the user — do not silently choose.

Also read [docs/coordination/README.md](./docs/coordination/README.md) before
changing shared Claude/Codex coordination behavior.

## Authoring references (installed as project-scope skills)

Two reference skills are unpacked at [.agents/skills/](.agents/skills/) and
must be consulted while building this plugin. They are gitignored — they are
build-time helpers, not part of the shipped plugin.

- **Plugin Structure** — canonical Claude Code plugin layout. Key rules:
  - `plugin.json` lives at `.claude-plugin/plugin.json` (NOT plugin root).
  - `name` field is kebab-case (`mpi-kanban`).
  - `skills/`, `hooks/` sit at plugin root. (No `commands/` — skills auto-trigger from description; direct invoke via `/mpi-kanban:mpi-X`.)
  - Use `${CLAUDE_PLUGIN_ROOT}` for any intra-plugin path reference.
- **Plugin Settings** — `.claude/<plugin>.local.md` pattern (frontmatter + body)
  for per-project plugin state. Relevant if the build agent decides to use it
  for `mpi-brief-rule`'s config instead of the SPEC's `config.json` approach.

## Migration source

The existing user-scope skills being migrated into this plugin live at:

```
C:\Users\Fabio\.claude\skills\mpi-*
```

The user has already backed these up. They will be removed before integration
testing (Phase 10) so they don't conflict with the plugin's bundled versions.

## Hard constraints

- Do NOT add columns or metadata fields beyond SPEC §4.4 — the VS Code
  extension breaks on unknown fields.
- Skills are pure markdown; `lib/*.md` are reference docs, not executable code
  (see SPEC §7.4 trade-off — JS layer deferred).

## Maintenance commands

Two project-scope slash commands live at `.claude/commands/` (gitignored — they
exist only in the maintainer's working copy):

- `/update-live` — runs `update_live.py`, then tells the user whether a
  `/plugin install ...` reinstall is required (skill set changed) or a Claude
  Code restart is enough (only file contents changed).
- `/release <version>` — bumps `.claude-plugin/plugin.json`, rewrites
  `CHANGELOG.md`, commits, tags `v<version>`, pushes both branch and tag. The
  `.github/workflows/release.yml` workflow then creates the GitHub Release.

Prefer these over running the underlying steps by hand — they enforce the
pre-flight checks (validator, clean tree, branch) and keep the CHANGELOG in
sync with the tag.

## Live copy maintenance

`update_live.py` copies this development checkout into the filesystem location
where agents load the plugin. When adding, moving, or renaming plugin behavior,
agent support files, build helpers, local state, tests, or generated artifacts,
update either `update_live.py` or `.gitignore` as needed so the live copy remains
correct.

The live copy must include every file required for Codex and Claude agents to run
the plugin, and it must exclude ignored development-only content, including the
`.git/` directory itself. Future work may make this plugin standard for both
Codex and Claude and may require copying to multiple filesystem destinations; in
that case, update `update_live.py` so destination handling is explicit rather
than assuming the current single Claude plugin cache path.

## Working directory

This plugin lives at `C:\AI\Mpi\Plugins\Mpi-Kanban`. Do NOT commit anything
to other projects (e.g. CubricStudio) from this build — CubricStudio is the
integration-test target only (PLAN Phase 10).
