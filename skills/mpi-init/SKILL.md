---
name: mpi-init
description: MPI workflow pack - Initialize or adopt Mpi-Kanban in a new or existing project. Creates or migrates the JSON task board, establishes project profile and knowledge index, records project mode, and can import freeform backlog files. Use when the user says "MPI init", "initialize MPI", "set up MPI", "set up the kanban", "adopt this project", "set up project knowledge", "import backlog", "convert this file to kanban", "$mpi-init", or hands over markdown to-dos.
---

# mpi-init Skill

## Purpose

Onboard a project into Mpi-Kanban. This is the single entrypoint for new
projects, existing projects, legacy MPI installs, project knowledge creation,
project mode selection, JSON board bootstrap, and backlog import.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

`mpi-init` replaces the old separate project setup flow. Do not tell users to
run a separate setup skill.

<HARD-GATE>
Do not overwrite existing project knowledge, rule files, memory entries, legacy
boards, or existing `board.json` tasks without showing a proposal and getting
explicit approval.

Fresh empty-board creation is safe to write directly when no board exists and
no legacy board needs migration. Everything else that changes existing project
state requires an approval proposal.
</HARD-GATE>

## Required reading

Read only the references needed for the path being executed:

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` - JSON board and task-card shape.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md` - `findBoard`, `ensureBoard`.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` - `createTask`.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/migrate.md` - legacy Markdown board migration.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/interop-ops/modes.md` - source-of-truth mode state.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-intent/modes.md` - mode contracts and defaults.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/profile-schema.md` - profile shape.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/index-schema.md` - index shape.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/adoption.md` - source inspection and
  adoption map.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/updates.md` - approval and preservation
  rules.
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/config-ops.md` - `scaffoldConfig()`, the sub-agent briefing
  config at `.agents/mpi-kanban.local.md`.

## Inputs

- No source file: initialize or adopt the project.
- A freeform markdown source file: import to-do/backlog/idea items into the JSON
  task board after initialization.

Legacy compatibility: if the project still carries a Markdown board
(`.agents/mpi-kanban/kanban.md` or `.claude/mpi-kanban/kanban.md`), propose a
one-time migration to the JSON task board after approval. This is a migration
input, not a primary onboarding path.

If the user says "this file" without naming one, ask which file. Common
candidates are `backlog.md`, `todo.md`, `TODO.md`, `ideas.md`, `notes.md`, or a
`## Backlog` section inside `README.md` or `CLAUDE.md`.

## Process

### 0. Legacy skills-pack preflight

Before anything else, check whether the pre-1.0 Agent Skills pack is still
installed:

```text
ls -d ~/.claude/skills/mpi-* ~/.agents/skills/mpi-* 2>/dev/null
```

Exactly these 15 names are the old pack: `mpi-archive`, `mpi-brainstorm`, `mpi-brief-rule`, `mpi-cleanup`,
`mpi-continue`, `mpi-create-large-plan`, `mpi-create-plan`,
`mpi-end-session`, `mpi-execute-parallel`, `mpi-handoff`, `mpi-init`,
`mpi-lib`, `mpi-message`, `mpi-nimbalyst-sync`, `mpi-project-refresh`.

If any of them exists, stop and report it as a blocking finding before doing
any other work. Plugin skills are namespaced, so they cannot collide by name,
but both sets load their descriptions and those descriptions carry the same
trigger phrases - every request then matches two skills, one of them running
the pre-1.0 contract. Give the removal commands from `docs/install.md`
(symlinks under `~/.claude/skills/` first, then the real directories under
`~/.agents/skills/`) and do not initialize until the user confirms removal.

Any other `mpi-*` skill is a project-scope skill the user owns - `mpi-end`,
`mpi-release`, `mpi-version-bump` and similar. Never propose deleting those.

### 1. Detect project state

Inspect these paths, without deep-loading the entire repo:

- `.agents/mpi-kanban/board.json`
- `.agents/mpi-kanban/tasks/`
- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`
- `.agents/mpi-kanban/state/interop.json`
- `.agents/mpi-kanban/kanban.md`
- `.claude/mpi-kanban/kanban.md`
- `.claude/mpi-kanban/archived*.md`
- `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/`, `.agents/rules/`

Classify the project:

- **fresh:** no MPI files exist.
- **legacy:** Markdown board or old `.claude/mpi-kanban/` files exist.
- **partial:** some MPI files exist but board/profile/index/state are missing.
- **initialized:** JSON board, profile, index, and interop mode are present.

If the project is already initialized and the user did not provide a backlog
file, say it is already initialized and suggest `mpi-project-refresh` for
maintenance. Do not rewrite files.

### 2. Ask or infer project mode

Read `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-intent/modes.md`.

For fresh or partial projects, ask:

```text
What project mode should this be?
- prototype (throwaway, exploratory)
- mvp (first real version, correctness over polish)
- scalable-foundation (intended to grow; default)
```

Default to `scalable-foundation` if the user declines to answer. For existing
projects, briefly note repo evidence only when it meaningfully suggests a
different mode.

Record mode in `.agents/mpi-kanban/project-profile.md` as `mode`,
`mode_rationale`, and `mode_source`.

### 3. Build the adoption proposal

For existing or partial projects, read
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/adoption.md` and inspect the conventional
sources within the listed budget.

The proposal must include:

1. Detected project state.
2. Project mode and rationale.
3. Board action:
   - create empty `board.json`;
   - migrate legacy `kanban.md` to JSON task workspaces;
   - move migrated `kanban.md` to `.agents/mpi-kanban/legacy/` or leave a
     tombstoned compatibility file at the old path;
   - import a freeform backlog into existing JSON board;
   - leave existing JSON board unchanged.
4. Project knowledge action:
   - create profile/index;
   - update missing profile/index pointers;
   - leave existing profile/index unchanged.
5. Interop action:
   - create default `state/interop.json` in `file` mode;
   - preserve existing source-of-truth mode;
   - surface a Nimbalyst conflict for explicit user direction.
6. Agent entrypoint changes, if any, limited to short pointer additions.
7. Boot-doc cleanup for `START-HERE.md`, `AGENTS.md`, `CLAUDE.md`,
   `README.md`, project memory indexes, and similar startup docs that still
   point active task continuation at `kanban.md`.
8. Rule or memory changes, if any, with per-file approval requirements.
9. Sub-agent briefing config action: create `.agents/mpi-kanban.local.md`
   when missing, listing the `rules_dir` that will be scanned and the rule
   files that carry a `## Sub-Agent Briefing` heading. Without this file
   `mpi-brief-rule` stops for every rule name and sub-agents dispatch with no
   briefing, so propose it even when the scan finds no rules yet.
10. First-rule action when the project has no rule file carrying a briefing:
   propose seeding `<rules_dir>/project.md` with `seedFirstRule()` from
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/config-ops.md`, drafted only from what this adoption pass
   actually read. Show the drafted file in the proposal; it is a rule file, so
   it needs its own approval.

End with:

```text
Approve this MPI init proposal? Reply "yes" to apply all, "yes except <list>" to skip some, "change <item>" to adjust, or "no" to discard.
```

For a truly fresh empty board with no source file and no existing knowledge,
the proposal can be compact, but still show the project mode and files to
create before writing profile/index.

### 4. Apply approved initialization

After approval, apply only approved changes:

1. Create `.agents/mpi-kanban/` and `.agents/mpi-kanban/state/` when needed.
2. Create or migrate `.agents/mpi-kanban/board.json`, `events.jsonl`, and
   `tasks/`:
   - use `ensureBoard()` for empty boards;
   - use `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/migrate.md` for legacy boards;
   - preserve legacy snapshots;
   - prefer moving migrated `.agents/mpi-kanban/kanban.md` to
     `.agents/mpi-kanban/legacy/kanban-<timestamp>.md`;
   - if the old path remains, replace it only after approval with a tombstone
     that says `SUPERSEDED - DO NOT EDIT` and points to `board.json`;
   - never delete legacy directories without explicit approval.
3. Create `.agents/mpi-kanban/state/interop.json` from
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/interop.json` when missing. Default
   `source_of_truth` is `file`.
   In file mode, `file` means the JSON board and task workspaces, not
   `kanban.md`.
4. Create or update `.agents/mpi-kanban/project-profile.md` from
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/project-profile.md`. Set `pack_version` to the
   `version` field in `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`; that is what
   `mpi-project-refresh` later compares an install against.
5. Create or update `.agents/mpi-kanban/project-knowledge-index.md` from
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/project-knowledge-index.md`.
6. Update `.agents/mpi-kanban/state/index.json` so `board` points at
   `.agents/mpi-kanban/board.json` when that file exists.
7. Apply approved `AGENTS.md` / `CLAUDE.md` pointer additions only.
8. Apply approved boot-doc repairs that remove active `kanban.md`
   continuation instructions.
9. Apply approved rule-file or memory-pointer changes per
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/updates.md`.
10. If a backlog source was provided, import parsed tasks after the board
    exists.
11. Write the approved seed rule file, if any, from
    `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/rule.md`.
12. Create `.agents/mpi-kanban.local.md` with `scaffoldConfig()` from
    `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/config-ops.md` when it is missing. Run this after any
    approved rule-file writes so the briefing scan sees them. Never overwrite
    an existing config.

### 5. Import freeform tasks

If a source file was provided, parse it permissively but do not invent content.

Recognized item shapes:

- `[ ] text` or `[x] text`
- `- [ ] text` or `- [x] text`
- `* text` or `- text`
- a standalone non-empty line under a recognized to-do/backlog/idea section

`[x]` maps to `done`; everything else maps to `todo`.

For each parsed task:

- title: short 2-6 word title derived from the source line;
- description: original source line, minus checkbox/bullet prefix;
- `column: "todo"`, `maturity: "idea"`, `status: "active"` when not done;
- `column: "done"`, `maturity: "complete"`, `status: "accepted"` when done;
- `position: "bottom"` to preserve source order.

When importing into an existing `board.json`, show parsed tasks and get
approval before writing. Never accept task IDs from source text.

### 6. Final report

Report:

```text
MPI initialized.
- Mode: <mode> (<source>).
- Board: <created | migrated | unchanged>. [board.json](.agents/mpi-kanban/board.json)
- Profile: <created | updated | unchanged>.
- Knowledge index: <created | updated | unchanged>.
- Interop mode: <file | nimbalyst>.
- Imported tasks: <count or "none">.
Next: use `mpi-brainstorm`, `mpi-create-plan`, or `mpi-continue`.
```

## Hard rules

- `mpi-init` is the only onboarding/adoption skill. Do not route to a separate
  setup flow.
- Card-write preflight is mandatory before creating or importing JSON tasks:
  read `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` and
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md`. Do not derive legal values from
  existing cards or legacy Markdown entries.
- `mpi-init` may create the initial profile/index and record project mode.
- `mpi-init` is the only skill that creates `.agents/mpi-kanban.local.md`.
  Consumers such as `mpi-brief-rule` must keep refusing to auto-create it.
- Mode changes after initialization are handled by `mpi-project-refresh`.
- Never maintain `board.json` and `kanban.md` as competing live boards.
- Never let `source_of_truth: file` mean the legacy Markdown board when
  `board.json` exists.
- Never overwrite existing profile/index/rules/memory without approval.
- Never create task-card fields beyond `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md`.
- Never delete legacy MPI files automatically.
