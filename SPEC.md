# Mpi-Kanban - Plugin Specification

> Status: active development. This plugin is unreleased and breaking workflow
> changes are allowed.

## 1. Purpose

Bundle MPI workflow skills into a Claude Code plugin that drives a per-project
Kanban board and supports a conversational agent workflow:

```text
brainstorm -> create-plan/create-large-plan -> continue -> handoff/continue -> end-session -> cleanup
```

The kanban board tracks high-level human-visible work state. Plan files are
living documents that may drift and be revised as implementation reveals new
facts. Shared Claude/Codex machine-readable coordination state lives outside
the board under `.agents/mpi-kanban/state/`.

## 2. Skill Set

- `mpi-init` - bootstrap/import a board.
- `mpi-brainstorm` - explore an idea and capture a BACKLOG entry.
- `mpi-create-plan` - create a compact/default plan.
- `mpi-create-large-plan` - create an adaptive, investigation-backed large plan.
- `mpi-continue` - resume/implement from the active plan, handoff, kanban
  entry, and current repo state.
- `mpi-execute-parallel` - execute explicit `## Parallel Batch` sections with
  worker sub-agents.
- `mpi-handoff` - preserve current state and print a mandatory copy/paste
  resume prompt for `mpi-continue`.
- `mpi-end-session` - sync docs/rules/memory, commit, and close the active
  kanban entry when complete.
- `mpi-cleanup` - propose conservative cleanup for stale plans, handoffs, and
  workflow artifacts.
- `mpi-archive` - archive kanban entries out of the active board.
- `mpi-brief-rule` - return configured rule briefings or rule bundles for
  sub-agent dispatch.

`mpi-write-plan` and `mpi-execute-next` are removed. Their roles are replaced
by `mpi-create-plan` / `mpi-create-large-plan` and `mpi-continue`.

## 3. Kanban Contract

The board lives at:

```text
<project-root>/.claude/mpi-kanban/kanban.md
```

Fixed columns:

```markdown
## BACKLOG
## PLANNING
## IMPLEMENTING
## COMPLETED
```

Entry metadata fields are locked for VS Code extension compatibility:

- `due`
- `tags`
- `priority`
- `workload`
- `defaultExpanded`
- `steps`

For PLANNING and IMPLEMENTING entries, the body fence must contain:

```text
Plan file: docs/plans/YYYY-MM-DD-<slug>.md
```

Skills must not add columns or metadata fields.

## 4. Shared Coordination Contract

Phase 1 defines a shared Claude/Codex coordination contract. Phase 2 adds the
shared lifecycle procedures agents use to create, update, release, reclaim, and
clean up coordination records.

Canonical machine-readable coordination state lives at:

```text
<project-root>/.agents/mpi-kanban/state/
```

The state root contains:

- `index.json` - small facade read first by every agent.
- `sessions/<uuid>.json` - active agent session records.
- `tasks/<uuid>.json` - active coordination task records.
- `files/<uuid>.json` - file ownership or claim records.
- `handoffs/<uuid>.json` - canonical machine-readable handoffs.

Core record IDs are UUIDs. Agents should generate them with the shared helper
documented in `docs/coordination/uuid-helper.md`.

`state/index.json` directly lists active record paths, active write claims,
pending file states, and handoff pointers so agents do not need to scan every
state directory before deciding what to read. The default heartbeat timeout is 2
hours. Stale claims are reclaimable by an orchestrator or integrator when
ownership intent is clear; uncertain cases ask the user.

Roles are lightweight behavior contracts:

- orchestrator
- planner
- implementer
- reviewer
- verifier
- integrator
- docs

Session records include explicit `allowed_actions`. Reviewer is first-class and
read/review by default; it does not take write ownership unless explicitly
reassigned. User-owned/manual kanban tasks stay board-only unless agent
coordination is needed.

Active records should keep only a short recent history window, roughly 5-10
events. `mpi-cleanup` owns conservative coordination-state garbage collection.

Shared lifecycle operation docs live under `lib/coordination-ops/`:

- `statuses.md` - session, task, file-claim, and handoff status vocabulary.
- `lifecycle.md` - index, session, task, file-claim, handoff, close, and kanban
  summary tag operations.

File ownership and commit ownership are separate. A file claim with status
`claimed` is an active write lock. Statuses such as `complete`,
`needs_review`, `needs_verification`, and `needs_integration` mean no active
writer owns the file, but pending-change provenance still matters. The session
running `mpi-end-session`, or an explicit integrator, owns the final commit
summary after rereading current coordination and Git state.

Reference docs live under `docs/coordination/`:

- `state-layout.md`
- `schemas.md`
- `roles.md`
- `uuid-helper.md`
- `handoff-migration.md`

## 5. Plan Model

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

Plans are living documents. `mpi-continue` may update current state, drift,
completed work, and remaining work before implementation when the repo state no
longer matches the written plan.

## 6. Continue Model

`mpi-continue` is the normal implementation skill. It:

1. Finds active work from a handoff path, plan path, IMPLEMENTING entry, or
   PLANNING entry.
2. Reads the latest handoff and plan when present.
3. Locates the kanban entry by `Plan file:`.
4. Moves PLANNING -> IMPLEMENTING when needed.
5. Adds stable kanban steps:
   - compact plan: `Implementation`;
   - phased large plan: phase titles;
   - large plan without phases: lifecycle steps.
6. Inspects current repo state.
7. Updates/annotates plan drift when needed.
8. Presents a continue brief and waits for approval before implementation.
9. Presents a post-implementation verification gate before marking work done.

`mpi-continue` does not commit or push.

When present, `mpi-continue` should read `.agents/mpi-kanban/state/index.json`
before inspecting individual coordination records. It should register or renew
an implementer session, attach a task record, and claim files before editing.
Kanban tags may summarize coordination state for the user, but `.agents/`
records remain the coordination source.

## 7. Parallel Execution

`mpi-execute-parallel` only runs explicit `## Parallel Batch` sections.

Each batch task must include:

- unchecked task text,
- `Ownership:` with files/modules,
- disjoint ownership from every other task,
- `Briefings:` rule names or bundle names when relevant,
- `**Verify:**`.

The main agent spawns workers, integrates their changes, verifies the batch,
and updates plan/kanban state. Workers must not edit plan, kanban, handoff,
rules, or memory files unless explicitly owned.

## 8. Handoff

`mpi-handoff` writes:

```text
.agents/mpi-kanban/state/handoffs/<uuid>.json
```

`docs/handoffs/` is legacy compatibility during migration. New canonical
handoffs live in `.agents/mpi-kanban/state/handoffs/`. When an older resume flow
needs a `docs/handoffs/` file, `mpi-handoff` may write a small legacy pointer to
the canonical handoff; the `.agents/` record remains the source of truth.

Before writing, it performs a preservation pass:

- update active plan current state/drift/preservation notes when stale;
- make known docs/rules/memory updates when accurate and allowed;
- record blocked or deferred preservation items in JSON.

The final chat output must include a copy/paste resume block pointing the next
session to `mpi-continue`.

## 9. Brief Rule Bundles

Project config lives at:

```text
<project-root>/.claude/mpi-kanban.local.md
```

It may define `rules:` and optional `bundles:`. `mpi-brief-rule <name>` returns
either one rule's `## Sub-Agent Briefing` or all rule briefings in a named
bundle.

The plugin does not hardcode project rules.

## 10. Cleanup

`mpi-cleanup` classifies workflow artifacts as active, completed, orphaned,
superseded, stale, or uncertain. It proposes cleanup and waits for approval.

It never deletes active files and never deletes archives by default.

Coordination-state cleanup under `.agents/mpi-kanban/state/` is conservative:
`mpi-cleanup` proposes changes first, never deletes active state, and prefers
moving closed coordination records to archive over deletion.

## 11. External Dependency

The board is designed for the MPI-specific VS Code extension fork:

- Mpi-Kanban
- Id: `MadPonyInteractive.mpi-kanban`
- Repository: <https://github.com/MadPonyInteractive/mpi-kanban-vscode>

The plugin still works without the extension; the board remains Markdown.

## 12. Acceptance Criteria

- Plugin registers all current skills.
- Brainstorm can capture BACKLOG and route to compact or large plan creation.
- Plan creation moves/creates a PLANNING entry with a `Plan file:` body line.
- Continue moves active work to IMPLEMENTING and uses stable kanban steps.
- Handoff writes JSON and always prints a pasteable `mpi-continue` resume block.
- Parallel execution refuses non-batch or unsafe batch work.
- Brief-rule supports single rules and bundles.
- Cleanup proposes changes before mutating files.
- Shared coordination docs consistently describe `.agents/mpi-kanban/state/` as
  canonical machine state while preserving `.claude/mpi-kanban/kanban.md` as the
  stable board path.
