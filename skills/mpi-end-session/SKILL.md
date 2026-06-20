---
name: mpi-end-session
description: MPI workflow pack - MPI end session workflow. Close session, sync rules/docs, commit touched files, update JSON task-board state, and close explicitly validated work. Use when user says "MPI end session", "end session", "wrap up", "commit and close", "$mpi-end-session", or "/mpi-end-session".
---

# mpi-end-session Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

Wrap up the current session cleanly: sync docs/rules with code changes, commit
touched files, persist any new memory, and close out the active JSON task card.
Legacy Markdown kanban close-out is compatibility behavior only when no JSON
board exists.

This skill is the LAST step in the brainstorm -> create-plan/create-large-plan
-> continue -> handoff/continue -> end-session loop. Run it when the user
signals the session is done.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Process

### 0. Read coordination state

Read these references when `.agents/mpi-kanban/state/index.json` exists:

- `<mpi-lib-root>/docs/coordination/README.md`
- `<mpi-lib-root>/coordination-ops/lifecycle.md`
- `<mpi-lib-root>/coordination-ops/statuses.md`
- `<mpi-lib-root>/interop-ops/modes.md`
- `<mpi-lib-root>/task-board-ops/_schema.md`
- `<mpi-lib-root>/task-board-ops/read.md`
- `<mpi-lib-root>/task-board-ops/mutate.md`

Reread the active session, task, file claim, and handoff records before
committing. A released file claim means no active writer owns the file; it does
not mean the pending changes are independently safe to commit.

At this end-session and commit boundary, read any `open_messages` records
pointed to by `state/index.json` when they target the current session, task,
changed files, workspace, agent, role, or user. Treat `open`, `acknowledged`,
and `replied` as unresolved. Relevant unresolved messages can block commit,
require a reply/acknowledgement, require an integrator, or require a handoff
before close-out. This is an async boundary check only; do not promise live
interruption, remote delivery, global broadcast, or a background broker.

Read `.agents/mpi-kanban/state/interop.json` when present. If it is missing,
assume `file` mode. In `nimbalyst` mode, Nimbalyst trackers/sessions are
canonical: do not move JSON task cards or legacy MPI board entries during
close-out. Commit/session cleanup may proceed, but board snapshots require an
explicit `mpi-nimbalyst-sync` boundary.

If this session owns active `claimed` files, complete, release, or hand them off
before committing. If another fresh active session owns claimed files that are
part of the current task, do not commit those changes; ask the user or assign an
integrator. Before deciding, reread relevant `open_messages` for those
contested files, owning sessions, task, workspace, agent, or role.

### 1. Survey what changed

Run, in this order using small commands only to protect context on big sessions:

- `git status` - working tree state.
- `git diff --stat HEAD` - file list with line counts. Do not run
  `git diff HEAD` here; the file list is enough to make decisions, and the full
  diff can be huge.

List the changed files back to the user before doing anything else.

### 2. Identify rule/doc impact

For each changed file, decide whether a rule or doc needs to update:

- New workspace, component, event, state key, or other architectural concept
  introduced or changed -> relevant `.agents/rules/*.md` file may need an edit.
- Architectural shift large enough to affect onboarding -> `docs/PROJECT.md`
  pointer may need an edit.

Cardinal rule: ask the user before modifying any architectural rule file.
Surface a one-line proposal per file and wait for explicit approval per file.

Edits must be concise: short bullets, no prose bloat, no new headings unless
strictly required.

### 2b. Lightweight project knowledge refresh

When `.agents/mpi-kanban/project-profile.md` or
`.agents/mpi-kanban/project-knowledge-index.md` exists, check whether this
session's changes affected architecture, conventions, important commands, or
agent guidance. Refer to `<mpi-lib-root>/project-knowledge/updates.md` for the
update shape.

If architecture, commands, conventions, topic coverage, or AGENTS/CLAUDE
pointers drifted, propose one concise edit per affected file with current vs.
proposed content. Wait for per-file approval. If nothing has drifted, say so in
one line. For broader drift, recommend `mpi-project-refresh`.

### 3. Memory pass

Per `~/.claude/CLAUDE.md`:

- Anything learned worth keeping? Write to the right file under the project's
  memory directory or `~/.claude/memory/`.
- Update `MEMORY.md` index entry with one dated line.
- Ask before removing or modifying an existing memory entry; show current
  content plus the proposed change.

### 4. Commit

Running `mpi-end-session` IS the user's explicit request to commit this
session's touched files. Commit without asking again, even if a general "commit
only when the user asks" instruction is otherwise in effect — invoking this
skill is that ask. Do not report "did not commit"; the only thing this skill
never does is `git push`.

- Stage files by name; never use `git add -A` or `git add .`.
- The session running `mpi-end-session`, or an explicit integrator, owns the
  final commit summary. Base the message on current coordination state and the
  current Git state, not stale assumptions from a previous file claim.
- Commit message follows this repo's recent conventional style. Read
  `git log --oneline -10` if uncertain. Write a clear "why" subject and a body
  if multiple distinct changes are bundled.

### 5. Close out the task-board item

Lib pointers, read each only when its recipe is needed:

- `<mpi-lib-root>/task-board-ops/read.md` - `findBoard`, `findTask`, `loadTask`
- `<mpi-lib-root>/task-board-ops/mutate.md` - `moveTask`, `writeTask`,
  `ensureLinkedFiles`, `appendEvent`, `setAttention`
- `<mpi-lib-root>/task-board-ops/validate.md` - validation checks when board
  state is inconsistent
- `<mpi-lib-root>/kanban-ops/find.md` - legacy `findKanban`, `findEntry`
- `<mpi-lib-root>/kanban-ops/steps.md` - legacy `allStepsDone`
- `<mpi-lib-root>/kanban-ops/mutate.md` - legacy `moveEntry`

JSON board steps:

`validation.md` is the gate between implementation and final completion. A JSON
task card moves to `done` only when validation state is represented in the task
workspace and the user explicitly approves final completion for that task in
the current request. Keep implementation checklists, validation notes, and
handoffs in linked task workspace files, not in `task.json`.

If interop mode is `nimbalyst`, skip all MPI board movement in this section and
report: "Interop mode is nimbalyst - Nimbalyst trackers/sessions are canonical.
Skipping task-board close-out; use mpi-nimbalyst-sync for a board snapshot."

1. Read `<mpi-lib-root>/task-board-ops/read.md` and call `findBoard()`.
2. Identify the active plan: the plan file most recently touched in this
   session from `git diff --stat HEAD` or conversation context.
3. If `board.json` exists, locate the task by explicit task ID, active plan
   link, required attention in `doing`, or active coordination task
   `task_card`. If no matching task is found, report that no JSON task-card
   close-out was performed.
4. If the matching task is in `todo` or `doing`, inspect `checklist.md` for
   implementation progress and `validation.md` for validation state. If
   implementation remains incomplete, leave the card in place and include
   `Note: session ended mid-implementation; task "<id>" still has open
   implementation work.` in the commit body when appropriate.

   Skipped-Doing auto-correct: if the card is in `todo` but real implementation
   work exists for it (checked items in `checklist.md`, OR changed files in this
   session's `git diff --stat HEAD` that belong to this task's plan), the Doing
   phase was skipped. Before any `done` move, call
   `beginImplementation(id, actor, planPath, sessionTitle)` from
   `<mpi-lib-root>/task-board-ops/mutate.md` to backfill `todo -> doing`, set
   `maturity: "in-progress"`, and derive the checklist, then continue with the
   normal completion gate below. Print one line:
   `Note: card "<id>" skipped the Doing phase; auto-corrected through doing before done.`
   A card with no implementation work keeps moving `todo -> done` with no
   warning. The lifecycle is always `To do -> Doing -> Done`, never
   `To do -> Done` for implemented work.
   Maturity auto-correct: before any move, read the card's `maturity` and check
   it against the enum (`idea`, `planned`, `in-progress`, `validating`,
   `complete`) and its column. If the value is invalid (e.g. `active`,
   `accepted`, `deferred`, `done`, `Validated`, `validated`, `validation`,
   `spec`, `implementing`, `implementation`) or incoherent with the column,
   call `writeTask(id, { "maturity": "<corrected>" }, actor)` to set the
   coherent value (`todo` -> `planned` or `idea`; `doing` -> `in-progress` or,
   when validation is represented, `validating`; `done` -> `complete`). Print:
   `Note: card "<id>" had invalid maturity "<old>"; corrected to "<new>".`

5. If validation is represented and the user explicitly approved final
   completion in the current request, call `moveTask(id, "done", actor,
   reason)` and update concise status/badges with `writeTask` if useful.
   Then close resolved coordination task records tied to that `task_card` and
   remove them from `state/index.json` `active_tasks`. Leave unresolved
   `needs_review`, `needs_verification`, or `needs_integration` records active.
6. If validation is not represented, keep the card in `doing` and call
   `setAttention(id, "required", reason, actor)` when the next action needs
   user validation.
7. If the task is already in `done`, do not move it again. Update only concise
   summary fields or attention state when needed.
8. If `board.json` is missing, fall back to legacy kanban compatibility:
   locate the PLANNING, IMPLEMENTING, VALIDATING, or COMPLETED entry tied to
   the active plan. All done IMPLEMENTING steps move to VALIDATING. A
   VALIDATING entry moves to COMPLETED only when the user explicitly approves
   final completion in the current request.

After commit/task-board close-out, close or complete the active coordination
session and task according to `<mpi-lib-root>/coordination-ops/lifecycle.md`.
Remove closed records from active index arrays, but preserve pending records
that still need cleanup, review, verification, or integration.

### 6. Final report

Output to the user:

- Files committed, one line each.
- Rules/docs updated, one line each, or "none".
- Project profile/index updates, one line each, or "none".
- Memory entries written/updated, one line each, or "none".
- Task-board result should distinguish moved to `done`, still in `doing`,
  attention required for validation, already `done`, no matching JSON task, and
  legacy kanban fallback.
- Message result should distinguish no relevant open messages, messages
  resolved/acknowledged/replied during close-out, or messages left unresolved
  with their paths and next action.
- Task-board result - one of:
  - `Task board: "MPI-42" -> done. [task.json](.agents/mpi-kanban/tasks/MPI-42/task.json)`
  - `Task board: "MPI-42" still in doing - validation or implementation remains. [task.json](.agents/mpi-kanban/tasks/MPI-42/task.json)`
  - `Task board: "MPI-42" attention required for validation. [validation.md](.agents/mpi-kanban/tasks/MPI-42/validation.md)`
  - `Task board: no matching JSON task / no board.json.`
  - `Legacy kanban: "<title>" -> VALIDATING or COMPLETED. [kanban.md](.agents/mpi-kanban/kanban.md)`

Then a final `git status` confirms the working tree is clean, or lists deferred
items explicitly.

## Hard rules

- Never use `git add -A` or `git add .`.
- Never modify a rule file in `.agents/rules/` without explicit user approval.
- Never auto-overwrite or delete a memory entry; ask first.
- Committing is in scope and authorized by invoking this skill; do not defer
  the commit to a separate user confirmation. Never push (`git push`);
  committing is enough, and the user pushes when ready.
- Never commit over another fresh active writer's claim.
- Card-write preflight is mandatory before any `column`, `maturity`, or
  `status` write: read `<mpi-lib-root>/task-board-ops/_schema.md` and
  `<mpi-lib-root>/task-board-ops/mutate.md`. Do not derive legal values from
  existing cards.
- Never treat task-card badges, attention, or legacy kanban tags as
  coordination authority; reread `.agents/mpi-kanban/state/`.
- Never move a JSON task card to `done` unless validation state is represented
  in the task workspace and final completion was explicitly approved.

## Success criteria

- All session-touched files committed, or explicitly deferred with reason.
- Rules/docs reflect any architectural change with the user's per-file approval.
- Memory entries written for non-obvious learnings; `MEMORY.md` index current.
- JSON task card moved to `done` only after validation state is represented and
  explicit user approval is present. Legacy kanban entries may move to
  VALIDATING or COMPLETED only as compatibility fallback.
- `git status` clean, or remaining items explained.
- Suggest `mpi-cleanup` after a completed entry if old plans, handoffs, closed
  coordination state, or archived task workspaces are likely stale. Do not run
  cleanup automatically.
