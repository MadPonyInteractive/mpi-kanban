# Mpi-Kanban Specification

> Status: active development. Breaking workflow and packaging changes are
> allowed before the next release.

## 1. Purpose

Mpi-Kanban is an all-or-nothing Agent Skills pack for planning, kanban
coordination, handoffs, cleanup, and multi-agent file ownership.

The workflow is:

```text
brainstorm -> create-plan/create-large-plan -> continue -> handoff/continue -> end-session -> cleanup
```

The human task board lives at `.agents/mpi-kanban/board.json` with per-task
workspaces under `.agents/mpi-kanban/tasks/<id>/`. Machine-readable agent
coordination state lives separately under `.agents/mpi-kanban/state/`. Legacy
projects may still have `.agents/mpi-kanban/kanban.md`; that Markdown file is
a migration input or snapshot, not the primary live board after the JSON task
board is present. After migration, skills should move the old Markdown board
under `.agents/mpi-kanban/legacy/` or leave only a tombstoned compatibility
file at the old path.

An MPI Kanban root represents one work context. That context may be a single
project folder, or it may be a VS Code `.code-workspace` whose `folders`
entries define the member folders for the shared board, coordination state, and
same-filesystem message inbox. Separate workspace roots remain separate work
contexts unless an agent explicitly routes a message to a known peer root.
The v0.8.0 mental model is one Kanban per VS Code work context, not one Kanban
per folder.

## 2. Distribution

The only supported install and update channel is the Claude Code plugin
marketplace:

```text
/plugin marketplace add MadPonyInteractive/mpi-kanban
/plugin install mpi-kanban@mad-pony-interactive
/plugin update mpi-kanban@mad-pony-interactive
```

Skills, hooks, and agents ship from one manifest at
`.claude-plugin/plugin.json`, published through
`.claude-plugin/marketplace.json` with source `./`. The install is
all-or-nothing: the workflow skills depend on the support skill `mpi-lib`, and
partial installs are unsupported.

The marketplace entry uses `source: "./"`, so the whole repository becomes
`${CLAUDE_PLUGIN_ROOT}`. `scripts/` is maintainer tooling and no shipped skill
may invoke it; a script a skill runs at runtime lives in
`skills/mpi-lib/scripts/`.

The plugin ships exactly one version stamp: the `version` field in
`.claude-plugin/plugin.json`. Claude Code uses it as the plugin update cache
key. `validate_pack_version()` fails a release whose stamp does not match the
latest released `## [x.y.z]` heading in `CHANGELOG.md`.

The pre-1.0 skills.sh / `npx skills` channel is retired, along with Codex
plugin packaging, Codex marketplace bundles, Kilo-specific generated skills,
and live-copy plugin cache bridges. A user on the pre-1.0 pack must remove its
15 skill folders before installing the plugin; both copies otherwise match the
same trigger phrases and one of them carries the pre-1.0 contract. See
`docs/migrating-to-1.0.md`.

## 3. Skill Set

- `mpi-init` - initialize/adopt a project, including JSON board bootstrap or
  migration, project mode, durable project knowledge, and backlog import.
- `mpi-project-refresh` - audit drift between project knowledge and repo
  reality, maintain board/state consistency, and handle project mode changes.
- `mpi-brainstorm` - explore an idea and capture a `todo` task.
- `mpi-create-plan` - create a compact/default plan.
- `mpi-create-large-plan` - create an adaptive, investigation-backed large
  plan.
- `mpi-continue` - resume/implement from the active task, plan, handoff, and
  current repo state; show one task card; or perform a bounded direct
  task-card state update such as moving one `MPI-*` card to `doing`,
  `validating`, or `done`.
- `mpi-execute-parallel` - execute explicit safe `## Parallel Batch` sections,
  and dispatch the ready cards on the board.
- `mpi-message` - send, read, acknowledge, reply to, resolve, and explicitly
  route same-filesystem async coordination messages.
- `mpi-end-session` - close out through one of two exits. Both sync
  docs/rules/memory, commit and push per `push_policy`, run the claim auditor,
  and resolve every card parked in `validating`. The **resume** exit writes a
  handoff JSON for a fresh session; the **done** exit closes the task card.
- `mpi-cleanup` - propose conservative cleanup for stale workflow artifacts.
- `mpi-archive` - archive completed board tasks.
- `mpi-brief-rule` - return configured rule briefings or rule bundles.
- `mpi-lib` - shared reference library support skill; not a user workflow.

Twelve workflow skills plus `mpi-lib`. `mpi-write-plan` and `mpi-execute-next`
were removed before 1.0. `mpi-handoff` merged into `mpi-end-session` in 1.0;
`mpi-nimbalyst-sync` and `mpi-project-setup`/`mpi-project-mode` are removed.

### 3a. Hooks

Six hooks ship in `hooks/`, registered by `hooks/hooks.json`. Each one exits 0
immediately when the project has no `.agents/mpi-kanban/board.json`, and each
fails closed with a printed reason rather than silently.

- `guard-git` (`PreToolUse`/Bash) - refuse `git checkout -- <path>`,
  `git checkout .`, `git restore` without `--staged`, destructive `git stash`,
  `git reset --hard`, and `git clean -f/-d/-x`. Branch operations,
  `restore --staged`, and read-only `stash` subcommands pass.
- `guard-card` (`PreToolUse`/Edit,Write) - refuse a code edit outside
  `.agents/` when no card is in `doing`, with the card contract inline and the
  file named so ownership seeds from the first real touch; and refuse a second
  card created in one session, which passes on retry once approved.
- `guard-claim` (`PreToolUse`/Edit,Write) - refuse a write to a path claimed by
  another live session. Reads both the `path` and `paths` claim shapes.
- `guard-shell` (`PreToolUse`/Bash) - refuse heredocs and multi-line escaped
  strings; require a script file or a single-quoted `python -c`.
- `session-start` (`SessionStart`) - report open claims, unresolved messages,
  active handoffs, and `doing` cards.
- `precompact-handoff` (`PreCompact`) - offer a handoff before auto-compaction.

Every hook has a case in `scripts/smoke_hooks.py`, which runs each one as a
real subprocess.

### 3b. Agents

Two read-only agents ship in `agents/`. A skill that dispatches an agent must
ship it; `validate_plugin.py` enforces that.

- `dispatcher` - plans the parallel split. Read-only, so it cannot clobber a
  worker.
- `claim-auditor` - runs at close-out. Classifies each factual assertion in the
  changelog, release notes, and cards closed this cycle as PROVEN, UNPROVEN,
  FALSE, or OVERSTATED, with the commit and source line that proves it, worst
  first, capped at 40 lines.

## 4. Shared Reference Model

Shared reference docs live under `skills/mpi-lib/`.

Consuming skills reference a shared file as
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/<sub/path>.md`. The placeholder is
substituted anywhere it appears in skill and agent content, including inside
hook `command` strings, so there is no discovery probe and no cached root.

A project-relative path such as `scripts/foo.py` resolves against the
*consuming project*, not the plugin, and is always a bug.
`validate_lib_references()` fails the run when a skill points at an `mpi-lib`
file that does not exist.

If a workflow skill cannot find `mpi-lib`, the install is broken; the skill
must say so and tell the user to reinstall the plugin.

## 5. Task Board Contract

The primary board index lives at:

```text
<project-root>/.agents/mpi-kanban/board.json
```

Human task workspaces live at:

```text
<project-root>/.agents/mpi-kanban/tasks/<id>/
```

Legacy projects may still contain:

```text
<project-root>/.agents/mpi-kanban/kanban.md
<project-root>/.claude/mpi-kanban/kanban.md
```

`mpi-init` is responsible for proposing migration of legacy board files during
project adoption. Migration must list files to move or snapshot, preserve
unknown files, and ask before overwriting an existing target or deleting a
legacy directory. Skills must not maintain both `board.json` and `kanban.md` as
competing live sources of truth.

After a JSON board exists:

- normal MPI skills must read and write `.agents/mpi-kanban/board.json` and
  `.agents/mpi-kanban/tasks/<id>/`;
- `.agents/mpi-kanban/state/index.json` must point at
  `.agents/mpi-kanban/board.json`;
- any retained `.agents/mpi-kanban/kanban.md` must be tombstoned as
  generated/display-only compatibility and must not be a canonical input;
- project boot docs such as `START-HERE.md`, `AGENTS.md`, `CLAUDE.md`,
  `README.md`, or project memory must not instruct agents to continue active
  work from `kanban.md`.

Fixed JSON board columns:

```json
{
  "schema": "mpi-kanban/board/v1",
  "next_id": 43,
  "columns": {
    "todo": ["MPI-40"],
    "doing": ["MPI-41"],
    "done": ["MPI-42"]
  }
}
```

Column IDs are locked as `todo`, `doing`, and `done`. User-facing labels are
`To do`, `Doing`, and `Done`. Each column stores ordered task IDs only. Task
IDs are system-assigned visible IDs in the form `MPI-<number>`; users may
reference these IDs, but must not edit or choose them.

`next_id` is the next integer to allocate for an `MPI-*` ID. It must only move
forward. If migration imports existing IDs, set `next_id` higher than the
largest imported numeric suffix.

Each task folder contains `task.json` plus optional linked work files:

```text
.agents/mpi-kanban/tasks/MPI-42/
  task.json
  brief.md
  plan.md
  checklist.md
  validation.md
  files.json
  events.jsonl
  handoffs/
  research/
```

Initial `task.json` shape:

```json
{
  "schema": "mpi-kanban/task-card/v1",
  "id": "MPI-42",
  "title": "Short task title",
  "description": "Optional short card summary.",
  "column": "doing",
  "maturity": "in-progress",
  "status": "active",
  "attention": {
    "state": "required",
    "reason": "Needs user decision before validation.",
    "updated_at": "2026-05-30T12:00:00Z"
  },
  "activeSessionTitle": "MPI-42 implementation session",
  "created_at": "2026-05-30T12:00:00Z",
  "updated_at": "2026-05-30T12:30:00Z",
  "links": {
    "brief": "brief.md",
    "plan": "plan.md",
    "checklist": "checklist.md",
    "validation": "validation.md",
    "files": "files.json",
    "events": "events.jsonl",
    "handoffs": "handoffs/",
    "research": "research/"
  }
}
```

Required fields are `schema`, `id`, `title`, `column`, `created_at`,
`updated_at`, and `links`. `description`, `attention`, and
`activeSessionTitle` are optional. `maturity` and `status` are compact badges
for UI scanning; they must not duplicate long plans, handoffs, research, or
implementation notes. Long-form work belongs in the linked task workspace
files.

Canonical task-card `maturity` values are:

| Column  | Values |
| ------- | ------ |
| `todo`  | `idea`, `planned`, `research`, `needs-decision`, `blocked`, `deferred` |
| `doing` | `in-progress`, `validating` |
| `done`  | `complete`, `rejected` |

When to use each `todo` value: `idea` for raw unplanned items; `planned` for
scoped, ready work; `research` — the card needs investigation before it can be
planned; `needs-decision` — the work is understood but a user/product decision
is outstanding; `blocked` — ready in principle but waiting on another card or
an external dependency; `deferred` — deliberately postponed, not being picked
up in the current stretch.

For `done`: `complete` for finished work; `rejected` — closed without being
built, kept in `done` as a record of the decision.

JSON task boards must not use legacy Markdown column names or external tracker
phase names as maturity values. `implementing` in particular is not a task-card
maturity value; a card being implemented is `doing` with
`maturity: "in-progress"`.

Process labels such as `Validated`, `validated`, `validation`, `spec`,
`scoped`, `review`, `active`, `accepted`, `done`, `implementing`, or
`implementation` are not maturity values; represent them in `status`,
`attention`, `description`, or linked task workspace files.

Column and maturity must stay coherent:

- `todo` cards use `idea`, `planned`, `research`, `needs-decision`, `blocked`, or `deferred`.
- `doing` cards use `in-progress` or `validating`.
- `done` cards use `complete` or `rejected`.

Companion renderers should surface unknown maturity values as invalid with an
obvious fallback badge or board notice instead of rendering them as an unstyled
normal card.

Passive append-only event records live in:

```text
.agents/mpi-kanban/events.jsonl
.agents/mpi-kanban/tasks/<id>/events.jsonl
```

Each line is one JSON object:

```json
{"schema":"mpi-kanban/event/v1","id":"MPI-42","type":"task.moved","at":"2026-05-30T12:30:00Z","actor":"claude","from":"todo","to":"doing","summary":"Moved into active implementation."}
```

Supported initial event types are `task.created`, `task.updated`,
`task.moved`, `task.deleted`, `attention.required`, `attention.cleared`,
`checklist.updated`, `checklist.item_checked`,
`checklist.item_unchecked`, `validation.updated`, `migration.started`,
`migration.task_imported`, and `migration.completed`. Events are an audit trail
and task-board history. They are not a live interruption channel and do not
require a daemon, broker, remote service, or real-time delivery.

Task-card events are appended to both
`.agents/mpi-kanban/tasks/<id>/events.jsonl` and
`.agents/mpi-kanban/events.jsonl`. The task log gives local card history; the
global log gives board-wide history.

Legacy Markdown boards are migration inputs only. `skills/mpi-lib/kanban-ops/`
was removed in 1.0 along with the ability to *operate* a Markdown board; the
one surviving path is adoption, through
`skills/mpi-lib/task-board-ops/migrate.md`. Once `board.json` exists, all board
creation, movement, and status updates use the JSON task board. A remaining
`kanban.md` is a tombstoned snapshot, never a second live board.

## 6. Coordination State

Canonical machine-readable coordination state lives at:

```text
<project-root>/.agents/mpi-kanban/state/
```

The state root contains:

- `index.json`
- `sessions/<uuid>.json`
- `tasks/<uuid>.json`
- `files/<uuid>.json`
- `messages/<uuid>.json`
- `handoffs/<uuid>.json`
- `archive/`

Agents read `state/index.json` first when it exists. Its `board` pointer should
refer to `.agents/mpi-kanban/board.json` for JSON-board projects and may refer
to `.agents/mpi-kanban/kanban.md` only for unmigrated legacy projects. File
claims with status `claimed` are active write locks. Completed or released file
ownership does not grant commit ownership; the closing or integrating session
must reread current state and Git state before committing.

`active_tasks` must not retain closed coordination task records. When a JSON
task card is moved to `done`, any coordination task record tied to that
`task_card` should be closed and removed from `active_tasks` unless it remains
explicitly unresolved, such as `needs_review`, `needs_verification`, or
`needs_integration`. Stale active coordination records for done cards are drift
to be repaired by `mpi-project-refresh`, `mpi-cleanup`, or session close-out;
normal continuation should report them without silently mutating unrelated
tasks.

Lifecycle references live in `skills/mpi-lib/coordination-ops/`.

### 6.1 Workspace Scope

The active Kanban root owns the coordination state for one work context:

- **single-folder context** - `.agents/mpi-kanban/board.json` lives directly
  under the project folder and paths are relative to that folder unless a
  record says otherwise;
- **VS Code workspace context** - a `.code-workspace` file is the primary scope
  map, and each `folders` entry is a member folder of the same board,
  coordination state, and message inbox;
- **peer workspace context** - a separate Kanban root may receive explicit
  same-machine messages, but it is not discovered or broadcast to implicitly.

Agents must not silently treat sibling folders as in scope. If the user asks an
agent to work in a related folder that is outside the active `.code-workspace`
scope, the agent should recommend adding that folder to the workspace before
treating it as part of the shared work context.

Workspace discovery references live in
`skills/mpi-lib/workspace-ops/discovery.md`. Workflow skills that need
folder-aware behavior should use that reference before deciding that a path
belongs to the active work context.

Active root selection follows this order:

1. Use an explicit root from the user's prompt, handoff, task card, or
   coordination record.
2. If the session is attached to a `.code-workspace`, parse that workspace file
   and treat its `folders` entries as the complete member list.
3. If exactly one member folder contains `.agents/mpi-kanban/board.json`, use
   that folder as the Kanban root.
4. If multiple member folders contain a board, ask the user or use an existing
   persisted project setting; do not pick silently.
5. If no board exists, initialize only the selected project folder through
   `mpi-init`, not every workspace member.

For `.code-workspace` parsing, resolve each `folders[].path` relative to the
directory containing the workspace file unless it is already absolute. Use
`folders[].name` as the member alias when present; otherwise use the final path
segment of the resolved folder. If a workspace file contains JSONC features,
use a JSONC-capable parser when available or inspect the `folders` entries
conservatively.

For example, `Mpi-Kanban.code-workspace` in this repository resolves:

| Alias | Resolved folder | Role |
|---|---|---|
| `Mpi-Kanban` | `C:/AI/Mpi/Plugins/Mpi-Kanban` | skill-pack source and active Kanban root |
| `mpi-kanban-vscode` | `C:/AI/Mpi/Plugins/mpi-kanban-vscode` | companion extension member folder |

No other `C:/AI/Mpi/Plugins/*` sibling is in scope unless it is added to the
workspace file or identified as a separate peer Kanban root.

Folder-aware coordination references must disambiguate files in multi-folder
workspaces. Message and claim records may use this shape when a plain
project-relative path is ambiguous:

```json
{
  "workspace_folder": "Website",
  "workspace_root": "C:/work/Website",
  "path": "src/App.tsx"
}
```

`workspace_folder` is the display alias from the workspace member entry when
available. `workspace_root` is the resolved folder root. `path` is relative to
that root. This lets records distinguish, for example, `Website/src/App.tsx`
from `App/src/App.tsx`.

### 6.2 Message Records

Same-filesystem async messages live under:

```text
<project-root>/.agents/mpi-kanban/state/messages/<uuid>.json
```

Messages are durable coordination records checked by agents at workflow
boundaries, claim conflicts, handoff, continue, parallel execution, cleanup,
and end-session. They do not interrupt running agents and do not require a
daemon, broker, remote service, global machine-wide broadcast, or live
subscription.

`state/index.json` may include `open_messages` pointing to message records with
status `open`, `acknowledged`, or `replied`. The index must remain small and
pointer-driven; message bodies and thread details stay in
`state/messages/<uuid>.json`.

Minimal message shape:

```json
{
  "schema": "mpi-kanban/message/v1",
  "id": "018f6e8a-7b9f-4f0b-85f3-6a11f6de2b1a",
  "status": "open",
  "created_at": "2026-05-31T12:00:00Z",
  "updated_at": "2026-05-31T12:00:00Z",
  "from": {
    "session": ".agents/mpi-kanban/state/sessions/source.json",
    "agent": "claude",
    "role": "implementer"
  },
  "to": {
    "selector": "file",
    "value": {
      "workspace_folder": "Website",
      "workspace_root": "C:/work/Website",
      "path": "src/App.tsx"
    }
  },
  "subject": "Request claim handoff for src/App.tsx",
  "body": "I need to edit this file for MPI-2. Can you release or hand off the claim?",
  "related": {
    "task_card": "MPI-2",
    "task": ".agents/mpi-kanban/state/tasks/task.json",
    "files": [
      {
        "workspace_folder": "Website",
        "workspace_root": "C:/work/Website",
        "path": "src/App.tsx"
      }
    ]
  },
  "thread": {
    "root": null,
    "parent": null
  },
  "recent_events": [
    {
      "at": "2026-05-31T12:00:00Z",
      "event": "created"
    }
  ]
}
```

Message statuses are `open`, `acknowledged`, `replied`, `resolved`,
`superseded`, and `closed`. Recipient selector values are `session`, `agent`,
`role`, `task`, `file`, `workspace`, and `user`.

Explicit same-machine peer routing writes a message record into the known peer
workspace root's `.agents/mpi-kanban/state/messages/` folder and records
provenance:

```json
{
  "from_workspace": "C:/work/Mpi-Kanban",
  "to_workspace": "C:/work/mpi-kanban-vscode"
}
```

Peer routing is opt-in and same-filesystem only. It must not scan every MPI
project on the machine, broadcast globally, deliver across machines, or start a
background delivery process.

### 6.3 Source Of Truth

The JSON task board and the coordination state under
`.agents/mpi-kanban/state/` are the source of truth. There is no pluggable
source-of-truth mode.

`state/interop.json` was the mode file for the removed Nimbalyst integration.
Skills must not read it, write it, or branch on it. `mpi-project-refresh`
reports an orphaned copy left by an older install and offers to delete it.

## 7. Project Knowledge

Durable project knowledge lives outside coordination state:

```text
<project-root>/.agents/mpi-kanban/project-profile.md
<project-root>/.agents/mpi-kanban/project-knowledge-index.md
```

The profile records project mode, summary, architecture, conventions, important
commands, files to read first, setup/refresh dates, and open gaps. The index
maps task topics to specific docs/rules/memory pointers.

Mode contracts and schemas live under `skills/mpi-lib/project-intent/` and
`skills/mpi-lib/project-knowledge/`.

`mpi-init` owns first-time project knowledge creation. `mpi-project-refresh`
owns maintenance and later project mode changes. Other skills consume project
knowledge without duplicating content.

## 8. Plan Model

Compact plans are created by `mpi-create-plan` and use one coherent
implementation flow with final verification.

Large plans are created by `mpi-create-large-plan` and may include:

- `## Current State`
- `## Phase N: ...`
- `## Parallel Batch: ...`
- `## Completed`
- `## Remaining Work`
- `## Plan Drift`
- `## Verification`
- `## Preservation Notes`

Parallelism is the default for eligible large-plan work. Parallel batches still
require disjoint `Ownership:`, per-task `**Verify:**`, no intra-batch
dependencies, and no active write claim conflict.

Plans are living documents. `mpi-continue` may update current state, drift,
completed work, and remaining work before implementation when reality no longer
matches the written plan.

## 9. Continue Model

`mpi-continue` is the normal implementation skill. It:

1. Finds active work from a handoff, task ID, plan path, `doing` task with
   attention, or legacy IMPLEMENTING/VALIDATING/PLANNING entry.
2. Reads project profile/index when present.
3. Reads coordination state when present.
4. Locates the task by task ID, plan link, active attention state, or legacy
   `Plan file:` during migration.
5. If a complete handoff identifies the task card, plan, and task workspace,
   uses those pointers as the primary route and reads `state/index.json` only
   for blockers such as active file claims, pending file states, open
   messages, and handoffs.
6. Moves `todo` to `doing` when needed through the shared begin-implementation
   flow, setting `maturity: "in-progress"`, `status: "active"`, active session
   context, derived checklist items, and task events together.
7. Adds stable checklist items in the task workspace.
8. Inspects current repo state.
9. Updates/annotates plan drift when needed.
10. Presents a continue brief before implementation.
11. Presents a post-implementation verification gate before marking work done.
12. Moves fully implemented work toward `done` only after validation state is
    represented in the task workspace.

`mpi-continue` does not commit or push.

`mpi-continue` also owns direct JSON task-card state updates when the user asks
to move or set one visible card without asking for code implementation. That
path must read `skills/mpi-lib/task-board-ops/_schema.md` and
`skills/mpi-lib/task-board-ops/mutate.md` before writing card state. It must
not infer legal `column`, `maturity`, or `status` values from existing cards.
Requests such as "set MPI-42 to validating" map to `column: "doing"` plus
`maturity: "validating"` only after `validation.md` exists or is written with
validation state. Requests to mark a card done require represented validation
state and explicit final-completion approval in the current request.

## 10. Parallel Execution

`mpi-execute-parallel` runs from one of two batch sources:

1. **Plan batch** - an explicit `## Parallel Batch` section inside one card's
   plan. Each task must include unchecked task text, `Ownership:` with
   files/modules, disjoint ownership from every other task, optional
   `Briefings:` rule or bundle names, and `**Verify:**`.

2. **Board batch** - ready cards selected from `.agents/mpi-kanban/board.json`.
   Requires a passing `python validate_board.py` run before dispatch; a
   validator failure stops selection entirely. A card is selectable when it is
   in `todo`, its `maturity` is exactly `planned`, its task workspace has a
   `plan.md`, it carries no `attention.state: "required"`, and its ownership is
   derivable and disjoint from every other selected card and every active write
   claim in `state/index.json`. A card's `plan.md` is the approval; dispatch
   does not stop to ask.

Both batch sources share the same coordination lifecycle, worker briefing, and
integration flow. The only worker-to-worker messaging case is a file-ownership
block: a worker that needs a file outside its ownership files one `mpi-message`
record pointing at the file and stops that line of work without waiting for a
reply.

The main agent spawns workers, integrates results, verifies the batch, and
updates plan/task-board state. Workers must not edit plan, board, task
workspace, handoff, rules, or memory files unless explicitly owned.

## 11. Handoff

The **resume** exit of `mpi-end-session` writes:

```text
.agents/mpi-kanban/state/handoffs/<uuid>.json
```

`docs/handoffs/` is legacy compatibility during migration. New canonical
handoffs live in `.agents/mpi-kanban/state/handoffs/`.

When a JSON task card is active, the resume exit also writes a lightweight
task-local pointer under `.agents/mpi-kanban/tasks/<id>/handoffs/` that
references the canonical state handoff. The canonical handoff remains under
`state/handoffs/`; task-local pointers are discovery aids for task lookup and
must not duplicate long handoff state.

The final chat output must include a pasteable resume block pointing the next
session to `mpi-continue`.

## 12. Brief Rule Bundles

Project config lives at:

```text
<project-root>/.agents/mpi-kanban.local.md
```

It may define `rules:` and optional `bundles:`. `mpi-brief-rule <name>` returns
either one rule's `## Sub-Agent Briefing` or all rule briefings in a named
bundle.

The pack does not hardcode project rules.

`mpi-init` creates this file during adoption and is the only skill that does;
`mpi-project-refresh` reports it missing. A consumer that finds no config stops
and says so - it never auto-creates one. A project whose rules folder holds no
file with a `## Sub-Agent Briefing` heading gets a first rule seeded from what
adoption actually read, and `mpi-end-session` proposes further rules as real
work proves real conventions. Without any of this the skill answers every rule
name with a bootstrap notice and sub-agents dispatch unbriefed.

## 13. Cleanup

`mpi-cleanup` classifies workflow artifacts as active, completed, orphaned,
superseded, stale, or uncertain. It proposes cleanup and waits for approval.

It never deletes active files and never deletes archives by default.

Cleanup and refresh workflows should detect coordination task records listed in
`state/index.json` `active_tasks` that are already `closed`, missing, or tied
to a `done` JSON task card without an unresolved coordination status. Approved
repairs remove closed records from active index arrays and preserve or archive
the coordination record according to lifecycle rules.

## 14. Packaging And Validation

Mpi-Kanban is one Claude Code plugin: twelve workflow skills, the `mpi-lib`
support skill, six hooks, and two agents, all from
`.claude-plugin/plugin.json`. The install is all-or-nothing; a missing
`mpi-lib` is a broken install, not a supported configuration.

The plugin intentionally accepts a non-standard shared support skill rather
than duplicating the reference library into every workflow skill. That keeps
context use low: `mpi-lib` files load only when a workflow skill says to read
one.

`scripts/validate_plugin.py` must check:

- every `skills/*/SKILL.md` has valid frontmatter, and each skill name matches
  its folder;
- skill names and descriptions satisfy Agent Skills limits;
- `skills/mpi-lib/SKILL.md` exists;
- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` are valid,
  and the manifest `version` matches the latest released `CHANGELOG.md`
  heading (`validate_pack_version()`);
- every hook named in `hooks/hooks.json` exists and is registered;
- every agent a skill dispatches ships in `agents/`;
- every `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/...` reference resolves to a real
  file (`validate_lib_references()`);
- the inline `maturity` lists in `mpi-continue` and `mpi-execute-parallel`
  match `TASK_MATURITIES` in `skills/mpi-lib/scripts/validate_board.py`
  (`validate_maturity_contract_docs()`);
- the surfaces removed before 1.0 stay removed (`REMOVED_PATHS`);
- stale-install detection stays wired: `pack_version` in the project-profile
  template, `mpi-init`, and `mpi-project-refresh`.

`scripts/smoke_hooks.py` runs every hook as a real subprocess, including the
no-board case for each.

## 15. Acceptance Criteria

- `/plugin marketplace add MadPonyInteractive/mpi-kanban` followed by
  `/plugin install mpi-kanban@mad-pony-interactive` installs skills, hooks, and
  agents together, and creates no `~/.claude/skills/mpi-*` entries.
- `/plugin list` reports the `version` from `.claude-plugin/plugin.json`.
- Agents can answer "what is MPI-5?" through `mpi-continue`'s bounded
  read-only mode, which reads only the active board entry and direct linked
  task files.
- `${CLAUDE_PLUGIN_ROOT}` resolves in skill, agent, and hook content, and
  workflow skills read shared references successfully.
- Every hook is inert in a project with no `board.json`, and blocks with a
  printed reason in a project that has one.
- A destructive `git checkout -- <path>` is blocked; a code edit with no card
  in `doing` is blocked; a write to another live session's claimed path is
  blocked.
- Work that splits into disjoint, independently verifiable file sets is
  dispatched by `mpi-continue` without the user asking, with every excluded
  card reported.
- Two concurrent `createTask` calls never overwrite a card.
- Task board schema uses locked JSON columns `todo`, `doing`, and `done`.
- Task card IDs are system-assigned visible IDs such as `MPI-42`.
- Legacy Markdown boards remain readable for migration and compatibility.
- Migration validation warns when boot docs still route active work through
  `kanban.md` after `board.json` exists.
- Coordination state remains under `.agents/mpi-kanban/state/`.
- Project profile/index remain under `.agents/mpi-kanban/`.
- `mpi-init` can migrate legacy `.claude/mpi-kanban/` board files to
  `.agents/mpi-kanban/` with explicit approval and no silent overwrites.
- Validator passes.
