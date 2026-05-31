---
name: mpi-init
description: MPI workflow pack - Initialize or adopt Mpi-Kanban in a new or existing project. Creates or migrates the JSON task board, establishes project profile and knowledge index, records project mode, and can import freeform backlog files. Use when the user says "MPI init", "initialize MPI", "set up MPI", "set up the kanban", "adopt this project", "set up project knowledge", "import backlog", "convert this file to kanban", "$mpi-init", or hands over markdown to-dos.
---

# mpi-init Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

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

- `<mpi-lib-root>/task-board-ops/_schema.md` - JSON board and task-card shape.
- `<mpi-lib-root>/task-board-ops/read.md` - `findBoard`, `ensureBoard`.
- `<mpi-lib-root>/task-board-ops/mutate.md` - `createTask`.
- `<mpi-lib-root>/task-board-ops/migrate.md` - legacy Markdown board migration.
- `<mpi-lib-root>/interop-ops/modes.md` - source-of-truth mode state.
- `<mpi-lib-root>/project-intent/modes.md` - mode contracts and defaults.
- `<mpi-lib-root>/project-knowledge/profile-schema.md` - profile shape.
- `<mpi-lib-root>/project-knowledge/index-schema.md` - index shape.
- `<mpi-lib-root>/project-knowledge/adoption.md` - source inspection and
  adoption map.
- `<mpi-lib-root>/project-knowledge/updates.md` - approval and preservation
  rules.

## Inputs

- No source file: initialize or adopt the project.
- A freeform markdown source file: import to-do/backlog/idea items into the JSON
  task board after initialization.
- An existing legacy board: migrate `.agents/mpi-kanban/kanban.md` or
  `.claude/mpi-kanban/kanban.md` to the JSON task board after approval.

If the user says "this file" without naming one, ask which file. Common
candidates are `backlog.md`, `todo.md`, `TODO.md`, `ideas.md`, `notes.md`, or a
`## Backlog` section inside `README.md` or `CLAUDE.md`.

## Process

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

Read `<mpi-lib-root>/project-intent/modes.md`.

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
`<mpi-lib-root>/project-knowledge/adoption.md` and inspect the conventional
sources within the listed budget.

The proposal must include:

1. Detected project state.
2. Project mode and rationale.
3. Board action:
   - create empty `board.json`;
   - migrate legacy `kanban.md` to JSON task workspaces;
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
7. Rule or memory changes, if any, with per-file approval requirements.

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
   - use `<mpi-lib-root>/task-board-ops/migrate.md` for legacy boards;
   - preserve legacy snapshots and never delete legacy directories without
     explicit approval.
3. Create `.agents/mpi-kanban/state/interop.json` from
   `<mpi-lib-root>/templates/interop.json` when missing. Default
   `source_of_truth` is `file`.
4. Create or update `.agents/mpi-kanban/project-profile.md` from
   `<mpi-lib-root>/templates/project-profile.md`.
5. Create or update `.agents/mpi-kanban/project-knowledge-index.md` from
   `<mpi-lib-root>/templates/project-knowledge-index.md`.
6. Apply approved `AGENTS.md` / `CLAUDE.md` pointer additions only.
7. Apply approved rule-file or memory-pointer changes per
   `<mpi-lib-root>/project-knowledge/updates.md`.
8. If a backlog source was provided, import parsed tasks after the board exists.

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
- `mpi-init` may create the initial profile/index and record project mode.
- Mode changes after initialization are handled by `mpi-project-refresh`.
- Never maintain `board.json` and `kanban.md` as competing live boards.
- Never overwrite existing profile/index/rules/memory without approval.
- Never create task-card fields beyond `<mpi-lib-root>/task-board-ops/_schema.md`.
- Never delete legacy MPI files automatically.
