# Codex Entry Point for mpi-kanban

This file is the Codex entry point for this repository. Mpi-Kanban has a native
Codex plugin manifest at `.codex-plugin/plugin.json` and a Claude Code manifest
at `.claude-plugin/plugin.json`; both use the same `skills/` workflow tree. When
installed as a Codex plugin, invoke workflows with `$mpi-*` skills or natural
language. Codex exposes plugin skill names with the plugin prefix, such as
`$mpi-kanban:mpi-continue`; older `$mpi-*` references are accepted only as
natural-language trigger phrases when the model routes them. Claude slash
commands such as `/mpi-kanban:mpi-continue` are for Claude Code only.

## Source of Truth

Read these files only as needed:

- `CLAUDE.md` for plugin development constraints and source-of-truth notes.
- `.codex-plugin/plugin.json` for Codex plugin metadata.
- `.claude-plugin/plugin.json` for Claude Code plugin metadata.
- `README.md` for user-facing behavior.
- `SPEC.md` before changing plugin behavior.
- `PLAN.md` before continuing plugin implementation work.
- `docs/coordination/README.md` before changing shared Claude/Codex
  coordination behavior.

If `SPEC.md` and `PLAN.md` disagree, ask the user before choosing an interpretation.

## Companion VS Code Extension

This plugin is paired with the MPI-specific VS Code extension fork:

- Repository checkout: `C:\AI\Mpi\Plugins\mpi-kanban-vscode`
- GitHub: `https://github.com/MadPonyInteractive/mpi-kanban-vscode`
- Extension identity: `MadPonyInteractive.mpi-kanban`
- Display name: `Mpi-Kanban`

The extension is a fork of `holooooo.markdown-kanban`. Keep the upstream MIT
copyright in the extension `LICENSE` and keep fork attribution in the extension
`NOTICE`.

The extension should remain focused on the MPI board contract: it opens and
watches `.claude/mpi-kanban/kanban.md` in the current workspace. It should not
restore the original arbitrary Markdown file-switching behavior unless the MPI
workflow explicitly needs that.

Publishing order can be independent: the VS Code extension depends only on the
stable board file contract, so it does not need to wait for this agent plugin
to become fully universal for Claude Code and Codex. Publish the extension fork
first, then keep this plugin's docs pointing to that extension while universal
agent packaging work continues.

## Available Workflow Skills

The plugin's skills are Markdown workflows under `skills/`. They are the shared
source for both Claude Code and Codex; Codex should load them selectively:

- `skills/mpi-init/SKILL.md` for starting or synchronizing a project kanban workflow.
- `skills/mpi-project-setup/SKILL.md` for establishing project mode and durable project knowledge (profile + index).
- `skills/mpi-project-mode/SKILL.md` for reviewing, reaffirming, or changing project mode.
- `skills/mpi-project-refresh/SKILL.md` for auditing and refreshing project knowledge drift.
- `skills/mpi-brainstorm/SKILL.md` for exploring possible approaches before a plan exists.
- `skills/mpi-create-plan/SKILL.md` for compact/default plans.
- `skills/mpi-create-large-plan/SKILL.md` for adaptive large plans.
- `skills/mpi-continue/SKILL.md` for resuming and implementing active MPI work.
- `skills/mpi-execute-parallel/SKILL.md` for explicit parallel batches.
- `skills/mpi-end-session/SKILL.md` for ending a work session and preserving state.
- `skills/mpi-handoff/SKILL.md` for preparing another agent or future session to continue.
- `skills/mpi-cleanup/SKILL.md` for conservative workflow artifact cleanup.
- `skills/mpi-brief-rule/SKILL.md` for returning configured rule briefings and bundles.

Related reference docs live under `lib/` and templates live under `templates/`. Load them only when the selected skill asks for them or when the task directly concerns kanban/config/plan mechanics.

## Shared Agent Coordination

The human-visible board remains:

- `.claude/mpi-kanban/kanban.md`

The canonical machine-readable coordination state lives under:

- `.agents/mpi-kanban/state/`

When agent coordination state is relevant, read
`docs/coordination/README.md` first, then only the specific referenced
coordination doc needed for the task. `state/index.json` is the first runtime
state file agents should inspect when it exists.

Lifecycle operation references live under:

- `lib/coordination-ops/statuses.md`
- `lib/coordination-ops/lifecycle.md`

Agents must coordinate through `.agents/mpi-kanban/state/` first. The kanban
board is a user display surface; tags are only coarse summaries. A file claim
with status `claimed` is an active write lock. Completed or released file
ownership does not equal commit ownership; the closing or integrating session
must reread current state before committing.

New canonical handoffs live under `.agents/mpi-kanban/state/handoffs/`.
`docs/handoffs/` is legacy compatibility during migration.

## Project Knowledge

Durable per-project knowledge lives outside `state/`:

- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`

When these files exist, agents must read the profile and the topic block in
the index that matches the current task BEFORE deep-loading rules, docs, or
memory. See `lib/project-knowledge/indexing.md` for context-budget rules.

Mode contracts live in `lib/project-intent/modes.md`. Default mode is
`scalable-foundation` when unclear. The active mode is recorded in the
profile frontmatter; only `mpi-project-mode` changes it.

`mpi-project-setup`, `mpi-project-mode`, and `mpi-project-refresh` are the
skills that manage project knowledge. Other skills consume it without
duplicating content; profile/index edits require user approval per the
rules in `lib/project-knowledge/updates.md`.

## Read-Only Boundary

For normal Codex work outside this plugin, treat this plugin directory as read-only reference material.

Do not edit existing files in this directory unless the user explicitly asks to modify the plugin. Creating Codex-only bridge files is allowed, but avoid filenames or locations that Claude Code uses as plugin API surface.

## Live Copy Maintenance

`update_live.py` is the deployment bridge from this development checkout into the agent/plugin locations that actually load the plugin. Keep it aligned with `.gitignore` whenever adding, moving, or renaming plugin functionality, agent support files, build helpers, local state, tests, or generated artifacts.

The live copy must include every file required for Codex and Claude agents to
run the plugin, including `.codex-plugin/plugin.json`, and it must exclude
ignored development-only content, including `.git/` itself. `update_live.py`
mirrors the checkout into the Claude plugin cache, mirrors a home-local Codex
checkout at `~/plugins/mpi-kanban`, updates `~/.agents/plugins/marketplace.json`,
and runs `codex plugin add mpi-kanban@mad-pony-interactive` so Codex installs
the local plugin build into `~/.codex/plugins/cache/...`.

## Project Kanban Usage

When using this plugin from another repository, prefer that repository's local kanban file and plugin state. For CubricStudio, the active project kanban is:

- `C:\AI\Mpi\CubricStudio\.claude\mpi-kanban\kanban.md`

Read that file only when the user asks for MPI kanban workflow actions or when the current task explicitly depends on the kanban state.

## KiloCode

KiloCode auto-discovers Agent Skills from `.claude/skills/`, `.agents/skills/`,
`.kilo/skills/`, `~/.kilo/skills/`, and any path or URL listed in `kilo.jsonc`.
A workspace that already has Mpi-Kanban installed as a Claude plugin therefore
needs no extra setup — KiloCode finds the same skill tree through the
compatibility path.

For Codex-free or Claude-free KiloCode workspaces, see
[`docs/kilocode-install.md`](docs/kilocode-install.md) for the
`kilo.jsonc skills.paths` clone path and the marketplace pull via the
generated `skills-kilo/` tree (built by `python scripts/build_kilo_skills.py`).

