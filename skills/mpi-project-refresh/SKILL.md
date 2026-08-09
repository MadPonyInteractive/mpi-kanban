---
name: mpi-project-refresh
description: MPI workflow pack - Maintain an existing Mpi-Kanban project. Audits project knowledge, board and state consistency, rules, memory pointers, important commands, architecture summary, source-of-truth mode, and legacy migration drift. Use when the user says "MPI project refresh", "refresh MPI", "refresh project knowledge", "update MPI project", "change project mode", "switch to scalable-foundation", "the profile is stale", "$mpi-project-refresh", or "/mpi-project-refresh".
---

# mpi-project-refresh Skill

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

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/updates.md` - approval, preservation, drift
  detection rules.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/adoption.md` - classification vocabulary for
  newly discovered or changed sources.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/indexing.md` - context-budget rules.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-intent/modes.md` - mode contracts and transitions.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/profile-schema.md` - profile fields.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/index-schema.md` - index fields.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/validate.md` - JSON board validation checks.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/migrate.md` - legacy board migration proposals.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/interop-ops/modes.md` - source-of-truth mode state.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/config-ops.md` - sub-agent briefing config shape and
  `scaffoldConfig()`.

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

Also read `version` from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`. That is the
installed pack version, and it goes in the final report every time - a refresh
report that does not name the version it was produced by cannot be trusted
later.

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
  orphaned task workspaces, and task-card `maturity` values outside the fixed
  enum (`idea`, `planned`, `research`, `needs-decision`, `blocked`,
  `deferred`, `in-progress`, `validating`, `complete`, `rejected`) or
  incoherent with their column. Treat values such as `Validated`, `spec`,
  `active`, `done`, `implementing`, and `implementation` as repair findings,
  not as new states.
- **Card sprawl:** only when the board holds 8 or more `todo` cards. Cluster
  them by shared file footprint first - `files.json` when it lists files,
  otherwise the paths the card's `plan.md` or description names - and by theme
  second. Report every cluster of three or more as a proposed umbrella: a
  large-plan card whose `plan.md` carries the phases and `## Parallel Batch`
  sections, with the clustered cards as its batch tasks. There is no `parent`
  field and none may be added. Also report `todo` cards whose `files.json` is
  empty, as unownable-and-undispatchable rather than as damage; ownership is
  written at the next `todo -> doing`, never backfilled retroactively.
- **State:** missing or invalid interop mode, stale source-of-truth claims,
  coordination state pointing at old board paths, `source_of_truth: file`
  misread as Markdown instead of JSON/file-backed board state, `active_tasks`
  entries that are missing, closed, or tied to `done` JSON task cards without
  unresolved statuses such as `needs_review`, `needs_verification`, or
  `needs_integration`. Also `state/files/` records: a wrong `schema`, neither or
  both of `path`/`paths`, an unknown claim status, or a leading BOM. Nothing
  validated that folder before, and every one of those shapes was found live.
- **Behaviour rules:** `<rules_dir>/behaviour.md` missing entirely, or missing
  sections the pack's
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/behaviour-rules.md` now
  ships. This file is generic agent conduct, so a section the pack added
  reaches every project through refresh. Propose the missing sections; never
  overwrite text the project changed on purpose.
- **Worker archetypes:** bundles or rules declared in
  `.agents/mpi-kanban.local.md` with no matching `.claude/agents/<name>.md`.
  Propose one stub per declared name from
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/worker-agent.md`. Propose
  only from declarations, never from directory structure.
- **Agent entrypoints:** `AGENTS.md` / `CLAUDE.md` pointers missing or stale.
- **Sub-agent briefing config:** `.agents/mpi-kanban.local.md` missing
  entirely, a `rules_dir` that no longer exists, configured rule files that
  are gone from disk, rule files under `rules_dir` that carry a
  `## Sub-Agent Briefing` heading but are not listed, and a
  `critical_snapshot_file`/`critical_snapshot_anchor` pair that no longer
  resolves. A missing config is a finding, not a silent default: it makes
  `mpi-brief-rule` stop for every rule name, so every sub-agent dispatched
  from this project runs with no briefing.
- **Legacy skills pack:** check `ls -d ~/.claude/skills/mpi-*
  ~/.agents/skills/mpi-* 2>/dev/null` for the 15 pre-1.0 pack names
  (`mpi-archive`, `mpi-brainstorm`, `mpi-brief-rule`, `mpi-cleanup`,
  `mpi-continue`, `mpi-create-large-plan`, `mpi-create-plan`,
  `mpi-end-session`, `mpi-execute-parallel`, `mpi-handoff`, `mpi-init`,
  `mpi-lib`, `mpi-message`, `mpi-nimbalyst-sync`, `mpi-project-refresh`).
  Any survivor means every request matches two skills, one of them running the
  pre-1.0 contract. Report it above every other finding with the removal
  commands from `docs/install.md`. Any other `mpi-*` skill is a project-scope
  skill the user owns; never propose deleting those.
- **Pack install:** compare the installed plugin `version` against
  `pack_version` in the profile frontmatter. Compare the numbers component by
  component, never as strings: `0.9.0` is older than `0.10.0` but sorts after
  it, so a string comparison reports the stale install as current. Cases:
  - installed is **older** than `pack_version` - stale install. Report it
    first, above every other finding, and say plainly that the rest of this
    report was produced by an old auditor and may be missing checks that exist
    in the recorded release. Tell the user to reinstall with
    `/plugin update mpi-kanban@mad-pony-interactive` and re-run the
    refresh. Never reinstall automatically.
  - `pack_version` **missing** - the profile predates the stamp. Propose
    adding it, no warning.
  - installed is **newer**, or equal - normal. Record the installed version.

  This detects a downgrade or a second machine with an old install. It cannot
  detect that a newer release exists upstream; that needs a network call the
  pack does not make.
- **Push policy:** `push_policy` missing from the profile frontmatter. Close-out
  treats an absent value as `auto` and pushes, so a profile written before 1.0
  silently opts into pushing. Propose the explicit line, ask which of `auto`,
  `ask`, or `never` this repo wants, and never change an existing value without
  approval. An invalid value is a finding too - close-out falls back to `auto`.
- **Rules:** a `rules_dir` that does not exist, or exists with no file carrying
  a `## Sub-Agent Briefing` heading. Propose `seedFirstRule()` from
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/config-ops.md`. Also report rules that have drifted from the
  code they govern, and conventions now enforced in several places with no rule
  of their own.

Cap inspection to a sane budget. If the repo is too large, narrow scope with the
user instead of scanning everything.

### 3. Mode review and change path

Read `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-intent/modes.md`. Report:

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
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/project-profile.md` and
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/project-knowledge-index.md`.
2. Update `.agents/mpi-kanban/project-profile.md` per approved findings.
   Bump `last_refresh` to today. Set `pack_version` to the installed plugin
   `version`, unless the installed version is older than the recorded
   one - never lower `pack_version`, or the stale install erases the evidence
   that it is stale.
3. Update `.agents/mpi-kanban/project-knowledge-index.md` per approved findings.
   Bump `last_refresh` to today.
4. Apply approved mode changes and mode notes.
5. Apply approved JSON board repairs or legacy migration/snapshot actions.
   When `board.json` exists, approved cleanup should either move
   `.agents/mpi-kanban/kanban.md` under `.agents/mpi-kanban/legacy/` or replace
   it with a tombstone that says `SUPERSEDED - DO NOT EDIT` and points to
   `board.json`. Create approved umbrella cards one at a time with `createTask`
   and write their phases and `## Parallel Batch` sections into the new card's
   `plan.md`; leave the clustered cards on the board unless the user says to
   close them.
6. Apply approved interop state changes. Do not switch source of truth silently.
   If `board.json` exists, repair `state/index.json` `board` pointers that
   still point to `kanban.md`.
7. Apply approved coordination-state repairs. Remove missing or `closed`
   records from active index arrays. For coordination tasks tied to JSON cards
   in `done`, remove them from `active_tasks` only when their status is
   resolved (`verified`, `completed`, or `closed`); leave unresolved
   `needs_review`, `needs_verification`, or `needs_integration` records active.
8. Apply approved rule file creations or edits per file. This includes
   `<rules_dir>/behaviour.md` and approved `.claude/agents/<name>.md` worker
   stubs: create from the pack templates, add only the approved missing
   sections to a file that already exists, and never overwrite an existing
   agent definition.
9. Apply approved memory pointer edits. Ask before removing or modifying existing
   memory entries.
10. Apply approved boot-doc pointer edits. Preserve existing content; prefer
   small replacements from `kanban.md` to `board.json` / `tasks/<id>/`.
11. Apply approved `AGENTS.md` or `CLAUDE.md` pointer edits. Preserve existing
    content; pointer-first additions only.
12. Apply approved sub-agent briefing config repairs. Create a missing
    `.agents/mpi-kanban.local.md` with `scaffoldConfig()` from
    `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/config-ops.md`, seeding a first rule when the project has
    none. For an existing config, only add or correct approved `rules` entries
    and pointers; never rewrite it wholesale and never drop entries the user
    added by hand.

### 6. Final report

```text
Refresh applied.
- Pack version: <installed version> <"(STALE - project recorded <recorded>)" when older>.
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
- Card-write preflight is mandatory before any approved board repair that
  writes `column`, `maturity`, or `status`: read
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` and
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md`. Do not derive legal values from
  existing cards.
- Never create or edit a rule file without explicit per-file approval.
- Never auto-delete or auto-overwrite a memory entry.
- Never overwrite user-customized profile/index sections without showing the
  proposed change and getting approval.
- Never maintain `board.json` and `kanban.md` as competing live boards.
- Never treat `source_of_truth: file` as permission to read or write
  `kanban.md` when `board.json` exists.
- Never switch Nimbalyst/file source-of-truth mode silently.
- Never reinstall or update the pack. Report the stale install, give the user
  the install command, stop.

## Related invocations

- `mpi-init` to initialize or adopt a project.
- `mpi-end-session` runs the lightweight refresh for session-touched files.
