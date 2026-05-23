# Mpi-Kanban - Plugin Specification

> Status: active development. This plugin is unreleased and breaking workflow
> changes are allowed.

## 1. Purpose

Bundle MPI workflow skills into a dual Claude Code and Codex plugin that drives
a per-project Kanban board and supports a conversational agent workflow:

```text
brainstorm -> create-plan/create-large-plan -> continue -> handoff/continue -> end-session -> cleanup
```

The kanban board tracks high-level human-visible work state. Plan files are
living documents that may drift and be revised as implementation reveals new
facts. Shared Claude/Codex machine-readable coordination state lives outside
the board under `.agents/mpi-kanban/state/`.

## 2. Packaging and Invocation

This repository ships two native manifests that share one workflow source:

- Claude Code manifest: `.claude-plugin/plugin.json`
- Codex manifest: `.codex-plugin/plugin.json`
- Shared skill tree: `skills/mpi-*/SKILL.md`

Claude Code users invoke workflows with `/mpi-kanban:mpi-*` slash commands and
natural language. Codex exposes plugin skills with the plugin prefix, such as
`$mpi-kanban:mpi-continue`, and also routes from natural language. Short
`$mpi-*` phrases may appear in trigger descriptions, but autocomplete and direct
skill invocation use the prefixed Codex skill names. Custom Codex slash commands
are out of scope unless Codex adds official plugin slash-command support.

The Codex manifest points to `./skills/` and includes only native Codex
metadata required for display and discovery. The Claude manifest remains the
source for Claude Code marketplace packaging. Public identity fields shared by
both manifests must stay synchronized: name, version, description, author,
repository, license, and keywords.

Codex public distribution uses the repository as a Codex marketplace source.
The repo root contains `.agents/plugins/marketplace.json`, whose marketplace
name is `mad-pony-interactive` and whose `mpi-kanban` entry points at `.`. A
Codex user can install from GitHub with:

```text
codex plugin marketplace add MadPonyInteractive/mpi-kanban --ref main
codex plugin add mpi-kanban@mad-pony-interactive
```

Updates use:

```text
codex plugin marketplace upgrade mad-pony-interactive
codex plugin add mpi-kanban@mad-pony-interactive
```

For local development, `scripts/register_codex_plugin.py` may still write a
home-local `~/.agents/plugins/marketplace.json` entry pointing at a checkout
under the user's home directory. That helper is a development convenience, not
the public install path.

## 3. Skill Set

- `mpi-init` - bootstrap/import a board.
- `mpi-project-setup` - establish project mode and durable project knowledge
  (profile and knowledge index), adopting existing docs/rules/memory.
- `mpi-project-mode` - review, reaffirm, or change project mode without
  rerunning setup.
- `mpi-project-refresh` - audit drift between project knowledge and repo
  reality; propose updates.
- `mpi-brainstorm` - explore an idea and capture a BACKLOG entry.
- `mpi-create-plan` - create a compact/default plan.
- `mpi-create-large-plan` - create an adaptive, investigation-backed large plan.
- `mpi-continue` - resume/implement from the active plan, handoff, kanban
  entry, and current repo state.
- `mpi-execute-parallel` - execute explicit `## Parallel Batch` sections with
  worker sub-agents.
- `mpi-handoff` - preserve current state and print a mandatory copy/paste
  resume prompt for `mpi-continue`.
- `mpi-end-session` - sync docs/rules/memory, commit, run a lightweight
  project-knowledge refresh, and close the active kanban entry when complete.
- `mpi-cleanup` - propose conservative cleanup for stale plans, handoffs, and
  workflow artifacts.
- `mpi-archive` - archive kanban entries out of the active board.
- `mpi-brief-rule` - return configured rule briefings or rule bundles for
  sub-agent dispatch.

`mpi-write-plan` and `mpi-execute-next` are removed. Their roles are replaced
by `mpi-create-plan` / `mpi-create-large-plan` and `mpi-continue`.

## 4. Kanban Contract

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

## 5. Shared Coordination Contract

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

## 6. Plan Model

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

Parallelism is the default for eligible work, not an opt-in extra:

- During investigation, large planning defaults to spawning read-only sub-agents
  for independent investigation areas.
- For implementation, large planning defaults to writing `## Parallel Batch`
  sections whenever tasks have disjoint, declarable ownership and batch-safe
  verification. When work is large but cannot be split safely, the plan keeps
  normal phases and states why no batch was created.

This default never overrides the safety gates. Parallel batches still require
disjoint `Ownership:`, a per-task `**Verify:**`, no intra-batch dependencies,
and no active write claim on owned files. Compact plans never gain parallel
batches; parallel-capable work belongs in a large plan.

Plans are living documents. `mpi-continue` may update current state, drift,
completed work, and remaining work before implementation when the repo state no
longer matches the written plan.

## 7. Continue Model

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

When the next eligible unit is a valid `## Parallel Batch`, `mpi-continue`
defaults to routing it to `mpi-execute-parallel` rather than offering sequential
implementation. It still does not spawn workers itself.

`mpi-continue` does not commit or push.

When present, `mpi-continue` should read `.agents/mpi-kanban/state/index.json`
before inspecting individual coordination records. It should register or renew
an implementer session, attach a task record, and claim files before editing.
Kanban tags may summarize coordination state for the user, but `.agents/`
records remain the coordination source.

## 8. Parallel Execution

`mpi-execute-parallel` only runs explicit `## Parallel Batch` sections. For
eligible batches it is the default execution path, not an opt-in extra:
`mpi-continue` routes a valid next batch here before offering sequential
implementation, and `mpi-continue` never spawns implementation workers itself.

Each batch task must include:

- unchecked task text,
- `Ownership:` with files/modules,
- disjoint ownership from every other task,
- `Briefings:` rule names or bundle names when relevant,
- `**Verify:**`.

The main agent spawns workers, integrates their changes, verifies the batch,
and updates plan/kanban state. Workers must not edit plan, kanban, handoff,
rules, or memory files unless explicitly owned.

## 9. Handoff

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

## 10. Brief Rule Bundles

Project config lives at:

```text
<project-root>/.claude/mpi-kanban.local.md
```

It may define `rules:` and optional `bundles:`. `mpi-brief-rule <name>` returns
either one rule's `## Sub-Agent Briefing` or all rule briefings in a named
bundle.

The plugin does not hardcode project rules.

## 10b. Project Knowledge

Mpi-Kanban includes a model-neutral project knowledge layer so fresh agent
sessions do not rediscover architecture, conventions, important commands,
and engineering intent each time.

Project knowledge files (outside `.agents/mpi-kanban/state/`):

```text
<project-root>/.agents/mpi-kanban/project-profile.md
<project-root>/.agents/mpi-kanban/project-knowledge-index.md
```

The profile records project mode (`prototype`, `mvp`, `scalable-foundation`),
mode rationale and source, a project summary, an architecture summary, a
short conventions list, important commands, files to read first, setup and
refresh dates, and open knowledge gaps. The knowledge index maps task
topics to specific docs/rules/memory pointers so agents load only relevant
context.

Mode contracts and the default-mode rule live in
`lib/project-intent/modes.md`. The default is `scalable-foundation` when
project mode is unclear. Profile/index schemas, adoption procedures,
indexing rules, and update rules live under `lib/project-knowledge/`.

The three skills that own this layer are:

- `mpi-project-setup` - first-time establishment. Inspects existing docs,
  rules, memory, and backlog/process files. Produces an adoption map and a
  full proposal before writing.
- `mpi-project-mode` - mode review/change. Records rationale and migration
  notes. Does not rewrite code.
- `mpi-project-refresh` - on-demand drift audit. Includes a lightweight
  mode reassessment but does not change mode.

Existing skills consume project knowledge without duplicating it:

- `mpi-brainstorm` recommends `mpi-project-setup` for new projects after
  design approval.
- `mpi-create-plan` and `mpi-create-large-plan` read profile/index when
  present and include project mode in plan current state.
- `mpi-continue` reads profile/index before the Continue Brief and includes
  mode + matched topic conventions in the brief.
- `mpi-handoff` records profile/index pointers and relevant topic blocks in
  the canonical handoff JSON.
- `mpi-end-session` runs a lightweight refresh on session-touched files.
- `mpi-cleanup` treats the profile and index as active by default; recommends
  `mpi-project-refresh` instead of editing them.

Setup and refresh inspect the repo and propose changes, but never write to
project files, rules, or memory before the user approves the proposal.
`AGENTS.md` may be created or updated directly after the setup proposal is
approved, pointer-first: existing entrypoints stay concise and link to the
profile/index.

## 11. Cleanup

`mpi-cleanup` classifies workflow artifacts as active, completed, orphaned,
superseded, stale, or uncertain. It proposes cleanup and waits for approval.

It never deletes active files and never deletes archives by default.

Coordination-state cleanup under `.agents/mpi-kanban/state/` is conservative:
`mpi-cleanup` proposes changes first, never deletes active state, and prefers
moving closed coordination records to archive over deletion.

## 12. External Dependency

The board is designed for the MPI-specific VS Code extension fork:

- Mpi-Kanban
- Id: `MadPonyInteractive.mpi-kanban`
- Repository: <https://github.com/MadPonyInteractive/mpi-kanban-vscode>

The plugin still works without the extension; the board remains Markdown.

## 13. Acceptance Criteria

- Plugin registers all current skills, including `mpi-project-setup`,
  `mpi-project-mode`, and `mpi-project-refresh`.
- Claude and Codex manifests both register the shared `skills/` tree without
  duplicating workflow implementation.
- Codex invocation is through prefixed `$mpi-kanban:mpi-*` plugin skills and
  natural language, while Claude Code retains `/mpi-kanban:mpi-*`.
- Public Codex installation works through `codex plugin marketplace add
  MadPonyInteractive/mpi-kanban` followed by `codex plugin add
  mpi-kanban@mad-pony-interactive`; local checkout registration remains a
  development helper.
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
- Project knowledge artifacts live at `.agents/mpi-kanban/project-profile.md`
  and `.agents/mpi-kanban/project-knowledge-index.md`; the kanban schema is
  unchanged.
