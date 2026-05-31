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
- `mpi-show` - show/read one board task by ID or title without mutating state.
- `mpi-project-refresh` - audit drift between project knowledge and repo
  reality, maintain board/state consistency, and handle project mode changes.
- `mpi-brainstorm` - explore an idea and capture a `todo` task.
- `mpi-create-plan` - create a compact/default plan.
- `mpi-create-large-plan` - create an adaptive, investigation-backed large
  plan.
- `mpi-continue` - resume/implement from the active task, plan, handoff, and
  current repo state.
- `mpi-execute-parallel` - execute explicit safe `## Parallel Batch` sections.
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
  "maturity": "planned",
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
and future protocol shape only; this release does not require a daemon, broker,
or live message bus.

Legacy Markdown boards use the old five-column lifecycle `BACKLOG`,
`PLANNING`, `IMPLEMENTING`, `VALIDATING`, and `COMPLETED` with the locked
metadata fields `due`, `tags`, `priority`, `workload`, `defaultExpanded`, and
`steps`. Skills may read `kanban.md` for migration or compatibility. Once
`board.json` exists, normal board creation, movement, and status updates must
use the JSON task board. Compatibility reads must first prefer `board.json`;
they may inspect `kanban.md` only as legacy migration material, a tombstoned
snapshot, or an explicitly requested compatibility artifact.

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
- `handoffs/<uuid>.json`
- `archive/`

Agents read `state/index.json` first when it exists. Its `board` pointer should
refer to `.agents/mpi-kanban/board.json` for JSON-board projects and may refer
to `.agents/mpi-kanban/kanban.md` only for unmigrated legacy projects. File
claims with status `claimed` are active write locks. Completed or released file
ownership does not grant commit ownership; the closing or integrating session
must reread current state and Git state before committing.

Lifecycle references live in `skills/mpi-lib/coordination-ops/`.

### 6.1 Interop Mode State

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
5. Moves `todo` to `doing` when needed.
6. Adds stable checklist items in the task workspace.
7. Inspects current repo state.
8. Updates/annotates plan drift when needed.
9. Presents a continue brief before implementation.
10. Presents a post-implementation verification gate before marking work done.
11. Moves fully implemented work toward `done` only after validation state is
    represented in the task workspace.

`mpi-continue` does not commit or push.

## 10. Parallel Execution

`mpi-execute-parallel` only runs explicit `## Parallel Batch` sections.
Each batch task must include:

- unchecked task text;
- `Ownership:` with files/modules;
- disjoint ownership from every other task;
- `Briefings:` rule names or bundle names when relevant;
- `**Verify:**`.

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
- Agents can answer "what is MPI-5?" through a bounded read-only skill that
  reads only the active board entry and direct linked task files.
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


