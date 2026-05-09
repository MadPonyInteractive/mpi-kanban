# Codex Bridge for mpi-kanban

This file is a Codex-only bridge for the Claude Code plugin in this directory. It is intentionally separate from the Claude plugin manifest, commands, skills, library docs, and templates.

## Source of Truth

Read these files only as needed:

- `CLAUDE.md` for plugin development constraints and source-of-truth notes.
- `.claude-plugin/plugin.json` for plugin metadata.
- `README.md` for user-facing behavior.
- `SPEC.md` before changing plugin behavior.
- `PLAN.md` before continuing plugin implementation work.

If `SPEC.md` and `PLAN.md` disagree, ask the user before choosing an interpretation.

## Available Workflow Skills

The plugin's skills are Markdown workflows under `skills/`. They are compatible as reference material for Codex, but Codex should load them selectively:

- `skills/mpi-init/SKILL.md` for starting or synchronizing a project kanban workflow.
- `skills/mpi-brainstorm/SKILL.md` for exploring possible approaches before a plan exists.
- `skills/mpi-write-plan/SKILL.md` for turning a goal into a concrete implementation plan.
- `skills/mpi-execute-next/SKILL.md` for executing the next planned kanban item.
- `skills/mpi-end-session/SKILL.md` for ending a work session and preserving state.
- `skills/mpi-handoff/SKILL.md` for preparing another agent or future session to continue.
- `skills/mpi-brief-rule/SKILL.md` for creating or updating concise project rules.

Related reference docs live under `lib/` and templates live under `templates/`. Load them only when the selected skill asks for them or when the task directly concerns kanban/config/plan mechanics.

## Read-Only Boundary

For normal Codex work outside this plugin, treat this plugin directory as read-only reference material.

Do not edit existing files in this directory unless the user explicitly asks to modify the plugin. Creating Codex-only bridge files is allowed, but avoid filenames or locations that Claude Code uses as plugin API surface.

## Project Kanban Usage

When using this plugin from another repository, prefer that repository's local kanban file and plugin state. For CubricStudio, the active project kanban is:

- `C:\AI\Mpi\CubricStudio\.claude\mpi-kanban\kanban.md`

Read that file only when the user asks for MPI kanban workflow actions or when the current task explicitly depends on the kanban state.
