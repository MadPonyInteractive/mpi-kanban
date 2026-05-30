# JSON Task Board

## Current State

Project mode: scalable-foundation.

The current MPI board is a Markdown monolith at
`.agents/mpi-kanban/kanban.md` with five workflow columns:
`BACKLOG`, `PLANNING`, `IMPLEMENTING`, `VALIDATING`, and `COMPLETED`. That file
is simultaneously the human dashboard, agent coordination surface, persistence
format, planning pointer, and VS Code extension input. In larger projects this
has made the board noisy and hard for humans to scan.

The companion VS Code extension at `C:\AI\Mpi\Plugins\mpi-kanban-vscode` has
been updated and user-verified for the JSON task board. It opens
`.agents/mpi-kanban/board.json`, loads `tasks/<id>/task.json`, writes task
files and event logs, renders `To do`, `Doing`, and `Done`, supports whole-card
dragging, and keeps task workspace links available below the board on narrow
layouts.

The extension now also handles legacy Markdown workspaces explicitly. When
`board.json` is missing but `.agents/mpi-kanban/kanban.md` or
`.claude/mpi-kanban/kanban.md` exists, it prompts before creating the JSON
board, task workspaces, event logs, and a timestamped legacy snapshot. It does
not modify or delete the source Markdown board during migration.

The remaining direction is release readiness for the JSON-first board with
simple human columns:
`To do`, `Doing`, and `Done`. The board should be task-centered, not
agent-centered. Every card gets a system-assigned visible ID such as `MPI-42`;
users may reference that ID to agents without moving the card. The UI should be
directly manipulable: dragging a card moves work intent, double-clicking opens
task details, and all meaningful UI mutations update structured files and append
events.

The new human task files should not use `.agents/mpi-kanban/state/tasks/`
because that path already belongs to the coordination-state contract and stores
UUID-based coordination task records. Use a separate task workspace:

```text
.agents/mpi-kanban/
  board.json
  events.jsonl
  tasks/
    MPI-42/
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

The existing agent message bus idea should not be implemented in this plan. This
plan should introduce passive append-only events as an audit trail and future
protocol shape. A later message bus can consume or emit the same event types.

This plan depends on the `Extension smoke tests` plan. Do not begin the VS Code
extension redesign until the extension can be smoke-tested locally without
publishing builds.

## Completed

- [x] Phase 1: Finalize JSON Board Contract.
- [x] Phase 2: Shared Task Store And Migration.
- [x] Parallel Batch: Skill Workflow Update.
- [x] Parallel Batch: VS Code Extension Update.
- [x] Phase 3: Compatibility, Cleanup, And Release Readiness.

## Remaining Work

## Phase 1: Finalize JSON Board Contract

- [x] Update `SPEC.md`, `README.md`, `docs/install.md`, project knowledge, and
  `skills/mpi-lib/` references to define the JSON-first board contract:
  `.agents/mpi-kanban/board.json` as the board index, top-level
  `.agents/mpi-kanban/tasks/<id>/` as the human task workspace, and
  `.agents/mpi-kanban/kanban.md` as legacy compatibility rather than the
  primary live board. **Verify:** targeted searches show no remaining source of
  truth wording that says the active human board is only `kanban.md`.
- [x] Define the initial `board.json` schema with `schema`, `next_id`, and fixed
  columns `todo`, `doing`, and `done`, where each column stores ordered task
  IDs. **Verify:** docs and examples show no user-editable ID field and no extra
  planning/validation columns.
- [x] Define `tasks/<id>/task.json` with system-assigned `id`, `title`,
  optional short `description`, `column`, maturity/status badges, optional
  `attention`, optional `activeSessionTitle`, timestamps, and relative links to
  task workspace files. **Verify:** the schema supports visible cards without
  embedding plans, handoffs, research, or long implementation notes inline.
- [x] Define passive event records for global `.agents/mpi-kanban/events.jsonl`
  and per-task `tasks/<id>/events.jsonl`: `task.created`, `task.updated`,
  `task.moved`, `task.deleted`, `attention.required`, `checklist.updated`,
  `validation.updated`, and migration events. **Verify:** event examples are
  append-only JSON lines and make no assumption about a live broker, daemon, or
  agent runtime.

## Phase 2: Shared Task Store And Migration

- [x] Add shared task-board operation references or helpers for creating task
  IDs, reading `board.json`, loading task folders, moving cards, writing task
  JSON, ensuring linked files, appending events, and setting/clearing attention.
  Ownership: `skills/mpi-lib/`, `docs/`, validation scripts. **Verify:**
  workflows can describe task operations without parsing Markdown card blocks.
- [x] Add a migration path from the existing Markdown board to the JSON task
  board. The migration must preserve current entries, assign stable `MPI-*`
  IDs, map old columns to `todo` / `doing` / `done` conservatively, preserve
  plan-file links in each task folder, and keep the old `kanban.md` available as
  a legacy snapshot. **Verify:** a fixture board with BACKLOG, PLANNING,
  IMPLEMENTING, VALIDATING, and COMPLETED entries migrates without losing
  titles, descriptions, priorities, steps, or plan links.
- [x] Add repair/validation tooling for the JSON board index and task folders:
  missing task folder, orphaned task folder, duplicate ID, mismatched column,
  invalid JSON, missing linked file, and malformed event line. **Verify:** the
  validator reports actionable errors and does not silently delete user data.

## Parallel Batch: Skill Workflow Update

- [x] Update task discovery and board mutation workflows for `mpi-brainstorm`,
  `mpi-init`, `mpi-create-plan`, and `mpi-create-large-plan`. Ownership:
  `skills/mpi-brainstorm/`, `skills/mpi-init/`, `skills/mpi-create-plan/`,
  `skills/mpi-create-large-plan/`, relevant `mpi-lib` task-board references.
  Briefings: `kanban-board-contract`, `skill-runtime-references`.
  **Verify:** new ideas create `todo` tasks with system-assigned IDs, plan
  skills attach plan links to task folders, and users can still refer to work by
  task ID.
- [x] Update execution and closing workflows for `mpi-continue`,
  `mpi-execute-parallel`, `mpi-handoff`, `mpi-end-session`, `mpi-cleanup`, and
  `mpi-archive`. Ownership: listed skill folders and relevant shared lifecycle
  references. Briefings: `shared-agent-coordination`, `kanban-board-contract`.
  **Verify:** agents prioritize `doing` tasks with `attention.required`, keep
  implementation checklists in task files, move completed work to `done` only
  through the new board operations, and preserve handoffs/validation links
  without stuffing them into card bodies.
- [x] Update Nimbalyst interop handling for the new source-of-truth model.
  Ownership: `skills/mpi-nimbalyst-sync/`, `docs/nimbalyst-interop.md`,
  `skills/mpi-lib/interop-ops/`. Briefings: `nimbalyst-interop`,
  `kanban-board-contract`. **Verify:** `file` mode points to the JSON board as
  canonical, `nimbalyst` mode still avoids dual-writing, and import/export
  boundaries explicitly map Nimbalyst phases into `todo` / `doing` / `done`
  plus maturity badges rather than restoring old MPI columns.

## Parallel Batch: VS Code Extension Update

- [x] Replace the extension's Markdown parser persistence path with a JSON task
  store layer that reads `board.json`, loads visible `tasks/<id>/task.json`
  files, writes task files, and appends events. Ownership:
  `C:\AI\Mpi\Plugins\mpi-kanban-vscode\src\extension.ts`,
  `src\kanbanWebviewPanel.ts`, new extension task-store modules. Briefings:
  extension smoke-test plan, `kanban-board-contract`. **Verify:** the extension
  can open a workspace with JSON board files and render all three fixed columns
  without reading `kanban.md` as the live source.
- [x] Redesign the webview UI around the simple human board:
  `To do`, `Doing`, `Done`; one global Add Task button that creates a `todo`
  task; visible task IDs on every card; title and short description only on
  inactive cards; checklist display only for `Doing`; badges for maturity and
  attention; links to plan/checklist/validation/handoffs; double-click opens a
  detail panel; edit/delete remain as overlay actions. Ownership:
  `src/html/webview.html`, `src/html/webviewScript.js`, `src/html/style.css`.
  Briefings: extension smoke-test plan. **Verify:** a human can understand what
  is to do, doing, and done without reading raw files, and task detail links
  open the relevant task workspace files.
- [x] Replace drag-handle behavior with whole-card dragging. Dragging a card to
  another column updates `board.json`, updates the task's column/state metadata,
  appends events, and sets attention when the move implies agent reconciliation.
  Ownership: `src/html/webviewScript.js`, extension message handlers, task-store
  module. Briefings: extension smoke-test plan. **Verify:** cards drag from any
  non-control part of the card; moving `todo -> doing`, `doing -> done`,
  `done -> doing`, and `doing -> todo` writes the expected task/event updates.
- [x] Add extension commands only where they complement the UI:
  install/update agent skills through the existing skills.sh command, open board,
  open task by ID, and optionally add task for power users. Ownership:
  extension `package.json`, `src/extension.ts`, README. Briefings:
  skills-sh-distribution. **Verify:** commands do not duplicate complex UI flows
  and the install/update command delegates to the existing
  `npx skills add MadPonyInteractive/mpi-kanban --all -y -g` path.

## Phase 3: Compatibility, Cleanup, And Release Readiness

- [x] Decide and implement the minimum supported legacy behavior. At minimum,
  existing `kanban.md` projects need a clear migration prompt or command; avoid
  maintaining two live source-of-truth files. **Verify:** opening a legacy board
  does not silently corrupt or rewrite it, and the user is told exactly what
  migration will create.
- [x] Update tests and smoke fixtures across the skill pack and VS Code
  extension. Include JSON board fixtures, migrated legacy board fixtures,
  whole-card drag scenarios, add/edit/delete flows, detail links, event appends,
  and agent-facing task lookup by ID. **Verify:** skill validator passes and the
  extension smoke-test workflow exercises the new UI/state path locally.
- [x] Update user-facing docs and release notes. Explain the new mental model:
  board as `To do / Doing / Done`, task folders as agent workspaces, JSON files
  as primary state, passive events as audit/future bus protocol, and Markdown
  board files as legacy compatibility. **Verify:** README and install docs do
  not instruct users to edit the old Markdown board as the primary workflow.

## Plan Drift

- 2026-05-30: Phase 1 also needed minimal updates to `AGENTS.md`,
  `CLAUDE.md`, coordination docs, interop references, and Nimbalyst sync
  wording so no live source-of-truth text still described `kanban.md` as the
  primary board.
- 2026-05-30: The VS Code Extension Update batch was not parallel-eligible as
  written because ownership overlapped across `extension.ts`,
  `kanbanWebviewPanel.ts`, `webviewScript.js`, and the new task-store layer.
  Continue handled it sequentially.

## Verification

Final verification requires both repositories:

- In `C:\AI\Mpi\Plugins\Mpi-Kanban`, run the skill-pack validator and targeted
  contradiction searches for old board-source wording.
- In `C:\AI\Mpi\Plugins\mpi-kanban-vscode`, run the local extension smoke-test
  workflow created by the `Extension smoke tests` plan.
- In a fixture workspace, migrate an old five-column `kanban.md`, create a new
  task from the UI, drag cards across `To do`, `Doing`, and `Done`, open a task
  detail view, verify task links, and confirm task/global events are appended.
- In an agent session, reference a task by ID and confirm the agent can locate
  `tasks/<id>/task.json`, linked plan/checklist/validation files, and the
  latest attention/event state without relying on a Markdown card body.

## Preservation Notes

- Do not implement the live agent message bus in this plan. Keep event records
  simple, durable, and transport-agnostic so the later message bus can build on
  the same vocabulary.
- Keep the skills separate from the VS Code extension. The extension may provide
  an install/update command for the Agent Skills pack, but the skills remain the
  agent-facing workflow interface.
- Avoid reusing `.agents/mpi-kanban/state/tasks/` for human board cards; that
  path already belongs to coordination state.
- The companion extension checkout is outside this repository. Implementation
  sessions that edit it should run from or receive write access to
  `C:\AI\Mpi\Plugins\mpi-kanban-vscode`.
- Because this is a breaking board architecture change, update `SPEC.md` before
  changing workflow behavior and keep migration behavior explicit.
