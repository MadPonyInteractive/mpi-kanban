# Mpi-Kanban — Claude Code Plugin

A Claude Code plugin that bundles the MPI workflow skills (`brainstorm`, `write-plan`,
`execute-next`, `end-session`, `handoff`, `brief-rule`) and drives a per-project
Kanban board (`kanban.md`) rendered by the `holooooo.markdown-kanban` VS Code extension.

## Source of truth

- [SPEC.md](./SPEC.md) — full design spec. Read in full before changing behavior.
- [PLAN.md](./PLAN.md) — phased build to-do list.

If SPEC and PLAN disagree, ask the user — do not silently choose.

## Authoring references (installed as project-scope skills)

Two reference skills are unpacked at [.agents/skills/](.agents/skills/) and
must be consulted while building this plugin. They are gitignored — they are
build-time helpers, not part of the shipped plugin.

- **Plugin Structure** — canonical Claude Code plugin layout. Key rules:
  - `plugin.json` lives at `.claude-plugin/plugin.json` (NOT plugin root).
  - `name` field is kebab-case (`mpi-kanban`).
  - `skills/`, `commands/`, `hooks/` sit at plugin root.
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

## Working directory

This plugin lives at `C:\AI\Mpi\Plugins\Mpi-Kanban`. Do NOT commit anything
to other projects (e.g. CubricStudio) from this build — CubricStudio is the
integration-test target only (PLAN Phase 10).
