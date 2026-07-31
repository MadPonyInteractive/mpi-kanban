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

The only supported install and update channel is skills.sh / `npx skills`:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

The `--all` flag is required. Partial installs are unsupported because the
workflow skills depend on the sibling support skill `mpi-lib`.

Claude Code plugin packaging, Codex plugin packaging, Codex marketplace bundles,
Kilo-specific generated skills, and live-copy plugin cache bridges are removed.
Old users must reinstall through the npx command above.

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
- `mpi-execute-parallel` - execute explicit safe `## Parallel Batch` sections.
- `mpi-message` - send, read, acknowledge, reply to, resolve, and explicitly
  route same-filesystem async coordination messages.
- `mpi-nimbalyst-sync` - coordinate Nimbalyst detection, source-of-truth mode,
  dry-run import/export boundaries, and tracker mappings.
- `mpi-handoff` - preserve current state in canonical JSON.
- `mpi-end-session` - sync docs/rules/memory, commit when appropriate, and
  close the active task when complete.
- `mpi-cleanup` - propose conservative cleanup for stale workflow artifacts.
- `mpi-archive` - archive completed board tasks and legacy kanban entries.
- `mpi-brief-rule` - return configured rule briefings or rule bundles.
- `mpi-lib` - shared reference library support skill; not a user workflow.

`mpi-write-plan` and `mpi-execute-next` are removed.

## 4. Shared Reference Model

Shared reference docs live under `skills/mpi-lib/`.

Consuming skills locate `mpi-lib` at first use by checking:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

After resolving the first existing path, the agent caches it as
`<mpi-lib-root>` for the session and reads individual files on demand.

If no candidate exists, the skill must stop and tell the user to reinstall:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

Workflow skills must not rely on `${CLAUDE_PLUGIN_ROOT}`, Claude `!` injection,
Codex plugin roots, or any runtime-specific plugin packaging feature.

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
- `source_of_truth: "file"` in `state/interop.json` means the local JSON/file
  backed board, not the legacy Markdown board;
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
  "activeSessionTitle": "Codex implementation session",
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

JSON task boards must not use legacy Markdown column names or Nimbalyst phase
names as maturity values. In particular, Nimbalyst `implementing` maps to MPI
`maturity: "in-progress"` on a `doing` card; `implementing` is not a
task-card maturity value.

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
{"schema":"mpi-kanban/event/v1","id":"MPI-42","type":"task.moved","at":"2026-05-30T12:30:00Z","actor":"codex","from":"todo","to":"doing","summary":"Moved into active implementation."}
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

Legacy Markdown boards are migration inputs only. Their column/field shape is
documented in `skills/mpi-lib/kanban-ops/_schema.md`; skills read `kanban.md`
solely for migration or compatibility. Once `board.json` exists, normal board
creation, movement, and status updates must use the JSON task board.
Compatibility reads must first prefer `board.json`; they may inspect `kanban.md`
only as legacy migration material, a tombstoned snapshot, or an explicitly
requested compatibility artifact.

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
    "agent": "codex",
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

### 6.3 Interop Mode State

Durable source-of-truth mode state lives at:

```text
<project-root>/.agents/mpi-kanban/state/interop.json
```

When the file is absent, skills must treat the project as `file` mode.

Supported `source_of_truth` values:

- `file` - default portable mode. MPI workflow skills mutate
  `.agents/mpi-kanban/board.json`, task workspaces, passive event logs, and
  coordination state directly. Only unmigrated legacy projects may update
  `kanban.md`; after `board.json` exists, `file` mode means the JSON/file
  backed board.
- `nimbalyst` - Nimbalyst sessions and trackers are canonical. MPI workflow
  skills must not live-update both Nimbalyst and the JSON task board during
  normal work. File import/export happens only through explicit sync
  boundaries.

The interop state records last environment detection, last sync/export times,
and ID mappings between MPI task IDs and Nimbalyst trackers. Skills must not
add Nimbalyst IDs or sync metadata to task card fields.

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
   for blockers such as active file claims, pending file states, open messages,
   handoffs, and interop mode.
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

`mpi-handoff` writes:

```text
.agents/mpi-kanban/state/handoffs/<uuid>.json
```

`docs/handoffs/` is legacy compatibility during migration. New canonical
handoffs live in `.agents/mpi-kanban/state/handoffs/`.

When a JSON task card is active, `mpi-handoff` also writes a lightweight
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

## 13. Cleanup

`mpi-cleanup` classifies workflow artifacts as active, completed, orphaned,
superseded, stale, or uncertain. It proposes cleanup and waits for approval.

It never deletes active files and never deletes archives by default.

Cleanup and refresh workflows should detect coordination task records listed in
`state/index.json` `active_tasks` that are already `closed`, missing, or tied
to a `done` JSON task card without an unresolved coordination status. Approved
repairs remove closed records from active index arrays and preserve or archive
the coordination record according to lifecycle rules.

## 14. Cross-Agent Skill Distribution

Mpi-Kanban is a 15-skill pack distributed through skills.sh. The install
command always uses `--all`; missing `mpi-lib` is a user installation error.

The pack intentionally accepts a non-standard shared support skill to avoid
duplicating the reference library into every workflow skill. This keeps context
use low because `mpi-lib` sibling files are loaded only when a workflow skill
instructs the agent to read them.

Validation must check:

- every `skills/*/SKILL.md` has valid frontmatter;
- every skill name matches its folder;
- skill names/descriptions satisfy Agent Skills limits;
- `skills/mpi-lib/SKILL.md` exists;
- consuming skills include the `mpi-lib` discovery block;
- interop mode templates and references are present;
- no `${CLAUDE_PLUGIN_ROOT}` references remain;
- `skills.sh.json` lists real skills.

## 15. Acceptance Criteria

- `npx skills add MadPonyInteractive/mpi-kanban --all -y -g` installs the pack.
- `npx skills add MadPonyInteractive/mpi-kanban -l` lists all 15 skills.
- Claude, Codex, and Kilo can invoke one workflow skill after npx install.
- Agents can answer "what is MPI-5?" through `mpi-continue`'s bounded
  read-only mode, which reads only the active board entry and direct linked
  task files.
- Workflow skills resolve `mpi-lib` and read shared references successfully.
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
