---
name: mpi-project-refresh
description: MPI workflow pack - Maintain an existing Mpi-Kanban project. Audits project knowledge, board and state consistency, rules, memory pointers, important commands, architecture summary, source-of-truth mode, and legacy migration drift. Use when the user says "MPI project refresh", "refresh MPI", "refresh project knowledge", "update MPI project", "change project mode", "switch to scalable-foundation", "the profile is stale", "$mpi-project-refresh", or "/mpi-project-refresh".
---

# mpi-project-refresh Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Maintain a project that already uses Mpi-Kanban. Refresh audits drift, proposes
updates, applies approved changes, and handles project mode review or changes.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

`mpi-project-refresh` does not bootstrap a new project. If MPI has not been
initialized, tell the user to run `mpi-init`.

<HARD-GATE>
Refresh inspects and proposes first. It does not write to project profile,
knowledge index, rules, memory, board files, state files, or agent entrypoints
before the user approves the refresh proposal.
</HARD-GATE>

## Required reading

- `<mpi-lib-root>/project-knowledge/updates.md` - approval, preservation, drift
  detection rules.
- `<mpi-lib-root>/project-knowledge/adoption.md` - classification vocabulary for
  newly discovered or changed sources.
- `<mpi-lib-root>/project-knowledge/indexing.md` - context-budget rules.
- `<mpi-lib-root>/project-intent/modes.md` - mode contracts and transitions.
- `<mpi-lib-root>/project-knowledge/profile-schema.md` - profile fields.
- `<mpi-lib-root>/project-knowledge/index-schema.md` - index fields.
- `<mpi-lib-root>/task-board-ops/validate.md` - JSON board validation checks.
- `<mpi-lib-root>/task-board-ops/migrate.md` - legacy board migration proposals.
- `<mpi-lib-root>/interop-ops/modes.md` - source-of-truth mode state.

## Pre-condition

At least one initialized MPI artifact should exist:

- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`
- `.agents/mpi-kanban/board.json`
- `.agents/mpi-kanban/state/index.json`
- `.agents/mpi-kanban/state/interop.json`

If none exist, stop with:

```text
Mpi-Kanban is not initialized in this project. Run `mpi-init` first.
```

If some exist but the profile or index is missing, classify the project as
partial MPI state and propose creating the missing profile/index as part of the
refresh.

## Process

### 1. Load current MPI state

Read the profile and knowledge index when present. Read board/state files only
enough to validate shape and source-of-truth mode:

- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`
- `.agents/mpi-kanban/board.json`
- `.agents/mpi-kanban/state/index.json`
- `.agents/mpi-kanban/state/interop.json`
- legacy `.agents/mpi-kanban/kanban.md` and `.claude/mpi-kanban/kanban.md`
- startup/boot docs that may route agents to board state: `START-HERE.md`,
  `AGENTS.md`, `CLAUDE.md`, `README.md`, project memory indexes, and obvious
  docs under `docs/` that are listed by the profile/index

Skim linked sources; do not deep-load every doc/rule/memory file.

### 2. Detect drift

Report findings in these categories:

- **Profile:** summary, architecture, commands, read-first pointers, open gaps,
  mode fields, setup/refresh dates.
- **Knowledge index:** topic pointers, moved files, stale rules, memory pointers,
  missing topics for newly important subsystems.
- **Rules and docs:** conventions that no longer match repo reality, duplicated
  or conflicting guidance, especially boot docs that still route active work
  through `kanban.md` after `board.json` exists.
- **Board:** JSON schema validity, task folders, linked files, legacy board files
  still treated as live, retained legacy `kanban.md` without a tombstone,
  orphaned task workspaces.
- **State:** missing or invalid interop mode, stale source-of-truth claims,
  coordination state pointing at old board paths, `source_of_truth: file`
  misread as Markdown instead of JSON/file-backed board state.
- **Agent entrypoints:** `AGENTS.md` / `CLAUDE.md` pointers missing or stale.

Cap inspection to a sane budget. If the repo is too large, narrow scope with the
user instead of scanning everything.

### 3. Mode review and change path

Read `<mpi-lib-root>/project-intent/modes.md`. Report:

```text
Current mode: <mode or "not recorded">
Evidence: <one or two lines>
Recommendation: <keep | change to prototype/mvp/scalable-foundation>
```

If the user asked to change mode, include the mode change in the refresh
proposal. Ask for the target mode and one-line reason if not already provided.

Mode changes require explicit approval and update:

- profile frontmatter `mode`, `mode_rationale`, `mode_source`, `last_refresh`;
- `## Mode Notes` with a dated transition note;
- `## Open Gaps` when the user names prior-mode shortcuts or migration debt.

Mode changes do not rewrite code.

### 4. Build the proposal

Single message containing:

1. Drift summary with counts by category.
2. Per-finding details, one line each, with proposed action.
3. Mode review or requested mode change.
4. Missing profile/index creation proposal if the project is partial.
5. Legacy migration proposal if old board files still need JSON migration or
   snapshot cleanup, tombstoning, moving under `.agents/mpi-kanban/legacy/`, or
   boot-doc pointer cleanup.
6. Newly inspected sources with adoption classification, if any.

End with:

```text
Approve this refresh? Reply "yes" to apply all, "yes except <list>" to skip some, "change <item>" to adjust, or "no" to discard.
```

### 5. Apply approved writes

After approval, in order:

1. Create missing profile/index only for partial MPI state, using
   `<mpi-lib-root>/templates/project-profile.md` and
   `<mpi-lib-root>/templates/project-knowledge-index.md`.
2. Update `.agents/mpi-kanban/project-profile.md` per approved findings.
   Bump `last_refresh` to today.
3. Update `.agents/mpi-kanban/project-knowledge-index.md` per approved findings.
   Bump `last_refresh` to today.
4. Apply approved mode changes and mode notes.
5. Apply approved JSON board repairs or legacy migration/snapshot actions.
   When `board.json` exists, approved cleanup should either move
   `.agents/mpi-kanban/kanban.md` under `.agents/mpi-kanban/legacy/` or replace
   it with a tombstone that says `SUPERSEDED - DO NOT EDIT` and points to
   `board.json`.
6. Apply approved interop state changes. Do not switch source of truth silently.
   If `board.json` exists, repair `state/index.json` `board` pointers that
   still point to `kanban.md`.
7. Apply approved rule file creations or edits per file.
8. Apply approved memory pointer edits. Ask before removing or modifying existing
   memory entries.
9. Apply approved boot-doc pointer edits. Preserve existing content; prefer
   small replacements from `kanban.md` to `board.json` / `tasks/<id>/`.
10. Apply approved `AGENTS.md` or `CLAUDE.md` pointer edits. Preserve existing
    content; pointer-first additions only.

### 6. Final report

```text
Refresh applied.
- Profile: <change count or "no changes">.
- Index: <change count or "no changes">.
- Mode: <unchanged | old -> new>.
- Board/state: <change count or "no changes">.
- Rules: <files updated or "none">.
- Memory: <entries updated or "none">.
- Agent entrypoints: <files updated or "none">.
```

## Hard rules

- Inspect first, propose second, write third.
- Do not bootstrap a brand-new project; route to `mpi-init`.
- Do not route to separate setup or mode skills; those flows are retired.
- Never create or edit a rule file without explicit per-file approval.
- Never auto-delete or auto-overwrite a memory entry.
- Never overwrite user-customized profile/index sections without showing the
  proposed change and getting approval.
- Never maintain `board.json` and `kanban.md` as competing live boards.
- Never treat `source_of_truth: file` as permission to read or write
  `kanban.md` when `board.json` exists.
- Never switch Nimbalyst/file source-of-truth mode silently.

## Related invocations

- `mpi-init` to initialize or adopt a project.
- `mpi-end-session` runs the lightweight refresh for session-touched files.
