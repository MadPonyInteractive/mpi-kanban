---
name: mpi-continue
description: MPI workflow pack - Continue active MPI work, show/read one board task, or update one task-card state. Use when the user says "continue this MPI plan", "MPI continue", "continue", "resume", "keep going", "pick this back up", "read a handoff and continue", "what is MPI-5", "show/read/open MPI-5", "move/update/set MPI-5 to doing/validating/done", "mark the card validating", "run the ready cards", "dispatch ready cards", "work the board", "$mpi-continue", or wants implementation to proceed from an MPI plan/handoff. Board-wide dispatch requests route to mpi-execute-parallel.
---

# mpi-continue Skill

## Purpose

Continue active work intelligently. This skill replaces rigid "execute next"
behavior: it reads the active JSON task card, plan, latest handoff, and current
workspace state, then proposes the next best action based on reality. Legacy
Markdown kanban entries are compatibility inputs only when `board.json` is
absent or unmigrated.

It also owns the read-only board-entry lookup path: "what is MPI-5?", "show
MPI-5", "open MPI-5", "read MPI-5", "what is this card?", "look at the <title>
card" -> run the read-only mode below instead of starting implementation.

It also owns bounded direct card-state updates when the user asks to move or
set one JSON task card, for example "move MPI-42 to doing", "set MPI-42 to
validating", or "mark the current card done". These updates use the same
task-board mutation references as implementation flow; do not infer legal
values by grepping existing cards.

When shared coordination state exists, `mpi-continue` also reads
`.agents/mpi-kanban/state/index.json` first and follows its pointers only as
needed. The shared contract is documented in
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/docs/coordination/README.md`.
Lifecycle operations are documented in
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md` and status values in
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/statuses.md`.

Plans are living documents. If implementation has drifted, update or annotate
the plan instead of forcing the next unchecked item.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Card contract

These are the only legal values. Do not copy them from other cards on the
board; other cards may be wrong.

- `column`: `todo` | `doing` | `done`
- `maturity`:
  - `todo`: `idea` | `planned` | `research` | `needs-decision` | `blocked` | `deferred`
  - `doing`: `in-progress` | `validating`
  - `done`: `complete` | `rejected`
- Coherence: `todo` -> `idea`, `planned`, `research`, `needs-decision`,
  `blocked`, or `deferred`; `doing` -> `in-progress` or `validating`;
  `done` -> `complete` or `rejected`

When to use new `todo` values: `research` — needs investigation before
planning; `needs-decision` — understood but a decision is outstanding;
`blocked` — ready but waiting on another card or an external dependency;
`deferred` — deliberately postponed, not being picked up in the current
stretch. For `done`: `rejected` — closed without being built, kept as a
record of the decision.

These are not maturity values: `active`, `accepted`, `done`, `implementing`,
`implementation`, `validated`, `Validated`, `validation`, `spec`, `scoped`,
`designed`, `review`. Process detail belongs in `status`, `attention`,
`description`, or the linked task workspace files.

## Discovered work

Work found while implementing the active card belongs to the active card. That
is the default and needs no approval.

- Same system, same files, or needed to make this card's verification pass ->
  fold it in: append a `checklist.md` item, extend `plan.md`, note it in
  `validation.md`. Do not create a card.
- Genuinely separate work (different system, not needed for this card's
  verification) -> do not create a card silently. Collect it and report it at
  the end of the step under `Noticed, not actioned:` so the user decides.
- Create a card only when the user explicitly asks for one in the current
  request, through `createTask` in
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md`. Never
  hand-write a `task.json`.

First check the open `todo` and `doing` cards for one already covering the same
system and extend that instead. Several cards on one system is the failure this
rule prevents; an umbrella afterwards is a repair, not the goal.

## Read-only board entry mode

Use this mode when the user asks to inspect one card/task rather than continue
implementation.

1. Check for `.agents/mpi-kanban/board.json`.
2. If present, use it. Ignore `.agents/mpi-kanban/kanban.md` except to mention
   that it is legacy/tombstoned if relevant.
3. If `board.json` is absent, stop and tell the user to run `mpi-init`. A
   legacy `.agents/mpi-kanban/kanban.md` is a migration input, not a board to
   read work from.

For JSON boards, resolve `MPI-*` IDs directly from `board.json`. For title
lookups, load only the visible `task.json` files listed by `board.json` and
match title case-insensitively. If multiple title matches exist, list the
matching IDs and ask the user to choose one. If no match exists, report that
the task was not found on the active JSON board. Do not search sibling repos or
legacy boards to "confirm" unless the user explicitly asks.

Stay inside `.agents/mpi-kanban/tasks/<id>/` and read direct
links only:

1. Required: `task.json`.
2. Summary first: `brief.md`, when present.
3. Current work detail: `plan.md`, then `checklist.md`, when present.
4. Completion evidence: `validation.md`, when present.
5. File context: `files.json`, when present.
6. Recent activity: last 10 lines of `events.jsonl`, when present.
7. Handoffs: list files under `handoffs/` and read only the newest one unless
   the user asks for all.
8. Research: list files under `research/`; read only a named research file or
   the newest one if the task summary depends on it.

Report:

```text
<ID> - <title>
Column: <todo | doing | done>
Status: <status/maturity/attention summary when available>

Summary:
<brief explanation in plain language>

Linked context read:
- <files read or "task.json only">

Next useful action:
<one sentence, e.g. continue, review validation, archive, or no action obvious>
```

After reporting, stop. Do not mutate board, task, state, memory, docs, or plan
files.

## Direct card update mode

Use this mode when the user explicitly asks to move or set one task card's
board state without asking to implement code.

1. Resolve `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib`, then read
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md`,
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md`, and
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` before writing anything. Do not
   derive allowed `column`, `maturity`, or `status` values from existing
   cards.
2. Locate exactly one JSON task by `MPI-*` ID or unambiguous title. If
   `board.json` is absent, stop and report that direct card-state updates
   require the JSON task board.
3. Map the user's requested state through the card contract:
   - `todo`, `to do`, `backlog`, `planned`, `reopen` -> `moveTask(id, "todo",
     actor, reason)` and coherent `maturity: "planned"` unless it is a raw
     idea.
   - `doing`, `in progress`, `implementing`, `implementation started` ->
     `beginImplementation(id, actor, planPath, sessionTitle)` when work is
     starting or the card is in `todo`; otherwise `moveTask(id, "doing", actor,
     reason)` and `writeTask` only if a concise badge/status change is needed.
   - `validating`, `needs validation`, `ready for validation`, yellow card ->
     ensure `validation.md` and `events.jsonl` exist, write or update
     `validation.md` with a short validation-state note if none exists, append
     `validation.updated`, keep/move the card in `doing`, then call
     `writeTask(id, { "maturity": "validating", "status": "active" }, actor)`.
   - `done`, `complete`, `completed` -> move to `done` when `validation.md`
     records the evidence that closes it: the command that ran and passed, or
     the user's own confirmation. Evidence closes a card. Keep it in `doing`
     with `maturity: "validating"` and validation attention only when the
     evidence is missing, the check failed, or the card's verification
     genuinely needs human eyes that have not seen it yet - and say which of
     those it is.
4. Append/verify the required events through `mutate.md` recipes. Meaningful
   card updates append to both `.agents/mpi-kanban/tasks/<id>/events.jsonl`
   and `.agents/mpi-kanban/events.jsonl`.
5. Report the resulting `column`, `maturity`, `status`, and linked task file
   touched, then stop. Do not inspect unrelated tasks or sibling repositories.

## Pre-conditions

Find the active work from the first available source:

1. Handoff path mentioned by the user or visible in context, including either
   `.agents/mpi-kanban/state/handoffs/<uuid>.json` or legacy
   `docs/handoffs/*.json`.
2. JSON task ID mentioned by the user, such as `MPI-42`.
3. Plan path mentioned by the user or visible in context.
4. `doing` task with `attention.state === "required"` or a recent
   `attention.required` event.
5. `doing` task linked to the active plan.
6. Legacy VALIDATING, IMPLEMENTING, or PLANNING kanban entry with a
   `Plan file:` body line, only when no JSON board is available.

If none is visible, ask:

```text
Which MPI plan or handoff should I continue from? Please paste the path.
```

## Session setup

Lib pointers, read only when needed:

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` - JSON board and task-card schema
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md` - `findBoard`, `loadTask`, `findTask`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` - `moveTask`, `writeTask`,
  `ensureLinkedFiles`, `appendEvent`, `setAttention`,
  `beginImplementation`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/plan-ops/derive.md` - derive stable checklist items from the
  active plan
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md` - session/task/file claim lifecycle
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/statuses.md` - state vocabulary
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/indexing.md` - context-budget rules

1. Read the handoff if present. If it is a legacy `docs/handoffs/` pointer to a
   canonical `.agents/` handoff, load the canonical handoff before continuing.
   If the handoff names `task_card.id`, `plan.file`, and task workspace links,
   treat those as the primary route. Do not enumerate unrelated active
   coordination tasks or done board cards unless these pointers are missing,
   contradictory, or blocked.
2. **Load project knowledge if present.** Read
   `.agents/mpi-kanban/project-profile.md` and
   `.agents/mpi-kanban/project-knowledge-index.md` before the Continue Brief.
   Pick the topic block matching the active plan. Load only the listed
   docs/rules; do not rediscover the whole project. If the profile is
   absent, fall back to the existing pre-condition behavior.
3. Read `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md`. Call `ensureStateRoot()` when
   coordination state is relevant, then read `state/index.json` as the active
   coordination facade. For a complete handoff route, use the index only for
   blockers and current pointers: `active_file_claims`, `pending_file_states`,
   `open_messages`, `active_handoffs`, and `active_sessions`.
   Treat stale unrelated `active_tasks` records as cleanup findings, not as a
   reason to scan every task before the Continue Brief.
4. At this continue startup boundary, read any `open_messages` records pointed
   to by the index when they target the active session, task, files, workspace,
   agent, role, or user. Treat statuses `open`, `acknowledged`, and `replied`
   as unresolved. Include relevant messages in the Continue Brief and resolve,
   acknowledge, reply, or ask the user before editing when a message changes
   the next action. This is an async boundary check only; do not promise live
   interruption, remote delivery, broadcast, or a background broker.
5. Register or renew an `implementer` session and create or attach a task
   coordination record for the active JSON task card and plan.
6. Read the active plan.
7. Read `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md` and locate the active task by
   handoff task ID first when available, otherwise by direct task ID, linked
   plan path, or required attention in `doing`.
8. Read `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/plan-ops/derive.md` before presenting the Continue
   Brief so the expected checklist shape is known.
9. When implementation starts or resumes, use
   `beginImplementation(id, actor, planPath, sessionTitle)` from
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md`. It must move `todo -> doing`
   when needed, set `maturity: "in-progress"`, set `status: "active"`, set
   active session context, derive checklist items from the active plan, and
   append events together. Do not leave a `doing` card with
   `maturity: "planned"` or `maturity: "implementing"`.
10. Inspect current workspace state with small commands (`git status`,
   targeted file reads/searches). Do not run large diffs unless needed.

## Orient and detect drift

Before proposing work, compare the plan/handoff with actual state:

- What is complete?
- What is pending?
- What changed since the plan was written?
- Are any remaining plan items obsolete, merged, or blocked?
- Is a `## Parallel Batch` now the next unit? If the next eligible unit is a
  valid batch (disjoint `Ownership:`, per-task `**Verify:**`, no intra-batch
  dependency, no active write claim on owned files), the default is to route to
  `mpi-execute-parallel`, not to implement it sequentially here.
- Do the ready cards split into disjoint work? Run `## Autonomous dispatch` on
  every start, before the Continue Brief, whether or not the user asked for it.
- Are there docs/rules/memory notes that should be preserved before handoff?
- Did `state/index.json` report stale active coordination records tied to done
  cards? Report these as cleanup/refresh findings; do not silently close
  unrelated task records during normal continuation.

If the plan is stale, edit the plan before implementation:

- Add a dated bullet under `## Plan Drift`.
- Update `## Current State`.
- Move obsolete work into `## Completed` or remove/rewrite remaining items.
- Keep the plan concise; do not preserve stale tasks for history when a drift
  note explains the change.

## Parallel batch routing

A card whose `plan.md` carries phases and `## Parallel Batch` sections is an
**umbrella card**: one card holding work that splits. There is no `parent`
field and no umbrella flag - the plan's shape makes it one, deliberately,
because the board contract forbids new card fields.

When the active card's next eligible unit is a valid `## Parallel Batch` -
disjoint `Ownership:`, a per-task `**Verify:**`, no intra-batch dependency, no
fresh write claim on the owned files - route it to `mpi-execute-parallel` and
announce the split. Do not ask first. The batch was written into the plan
deliberately, and the plan was already approved; asking again is the round trip
this pack exists to remove.

```text
Next unit is a parallel batch: "<batch title>". Running its N tasks in parallel.
<one line per task: id or title - owned paths>
```

`mpi-continue` never spawns implementation workers itself; `mpi-execute-parallel`
does. Fall back to a sequential continue brief only when the batch fails an
eligibility gate - and then say which gate - or when the user asks for
sequential.

## Board dispatch routing

When the user asks for the whole board rather than one card - "run the ready
cards", "dispatch ready cards", "work the board", "run everything that's
ready" - that is a board batch, not a continue. Route it to
`mpi-execute-parallel` and use its `## Board batch source` section; do not
implement the cards here one after another, and do not spawn workers here.

Requests naming one card ("continue MPI-42", "what is MPI-42") stay in this
skill.

Being asked is not the only trigger. `## Autonomous dispatch` below runs the
same routing on every start, without being asked; this section only covers the
case where the user says it out loud.

## Autonomous dispatch

Evaluate this on every start, before the Continue Brief. Do not wait to be
asked - the user never types "dispatch", and the work still splits. It is
read-only, costs a few reads, and needs no permission. Skip it entirely when
`board.json` is absent or fewer than two cards are ready.

1. **Collect the ready cards.** A card is ready when it is in `todo` with
   `maturity: "planned"`, has a `plan.md`, and carries no
   `attention.state: "required"`. The active card belongs to
   `## Parallel batch routing`, not here, unless its own next unit is not a
   batch and it is otherwise ready.
2. **Grep each card's footprint.** Do not trust `files.json` - most cards
   predate ownership being written at `todo -> doing`, so it is empty or stale.
   Read each card's `plan.md` and resolve every path, glob and module it names
   against the repo with a bounded search. `files.json` is a hint the grep
   confirms, never a substitute for it.
3. **Build the conflict graph.** Two cards conflict when their footprints share
   a file, when one footprint sits inside a directory the other owns, or when
   either intersects a fresh active write claim in `state/index.json`. A card
   whose footprint came back empty conflicts with everything: it cannot be
   proven disjoint, so it cannot be dispatched.
4. **Select the largest mutually non-conflicting set, capped at 4 workers.** On
   a tie, prefer the smaller footprints - those are the ones the grep pinned
   down most precisely.
5. **Report the whole evaluation before anything runs**, never dropping a card
   silently: every card the board offered appears, every exclusion with its
   reason.

```text
Dispatch: 3 of 7 ready cards are disjoint. Running them in parallel.

Selected:
- MPI-31 - src/api/** (grep: 12 files)
- MPI-34 - docs/install.md (grep: 1 file)
- MPI-37 - tests/e2e/** (grep: 4 files)
Excluded:
- MPI-30 - maturity is `research`, not `planned`
- MPI-33 - no plan.md; needs planning first
- MPI-35 - footprint overlaps MPI-31 on src/api/routes.ts
- MPI-38 - plan names no files; footprint not derivable
```

6. **Hand the selected set to `mpi-execute-parallel`** through its
   `## Board batch source`, which re-runs the board validator and owns worker
   spawning. Announce the split; do not ask permission - each selected card
   carries a `plan.md`, and that plan is the approval that already happened.
7. Fewer than two cards survive -> say nothing, continue with the normal
   single-card brief. "Nothing splits" is the common case; reporting it every
   session is noise.

This evaluation is **read-only**: cards, plans and claims in, nothing written -
not the board, not `files.json`, not a claim. A dispatcher that cannot write
cannot clobber a worker.

When `agents/dispatcher.md` ships with the installed plugin, delegate steps 1-4
to it with `subagent_type: "dispatcher"` - same method, in a subagent that
cannot write, keeping the card and plan reads out of this session's context.
**Running this skill authorizes that dispatch**, exactly as invoking
`mpi-end-session` authorizes its commit; a standing "do not call agents unless
the user asked" instruction is a default against *unprompted* dispatch, not a
veto here. Say so rather than quietly deferring - that reflex is why this agent
went months without running. Absent, or deliberately skipped: do the evaluation
inline and say which.

### `isolation: "worktree"` is not the isolation mechanism here

Do not run these workers in git worktrees, and do not "fix" this in a later
session. A worktree branches from the **default branch, not the parent
session's HEAD**, and MPI commits only at close-out - so a worktree worker
cannot see the session's uncommitted work, and will re-implement or contradict
it. Isolation here is disjoint ownership plus file claims plus the `guard-claim`
hook, all of which operate on the one working tree.

## Gate 1 - Continue brief

Before implementation, output a brief and stop:

```markdown
## Continue Brief: <next action>

**Source:** <plan path and handoff path if any>
**Project mode:** <profile mode, or "no profile">
**Current state:** <1-3 bullets>
**Conventions in play:** <1-3 bullets from matched topic block, or "none">
**Plan drift:** <none or summary of plan edits made/proposed>
**Files likely touched:** <files/modules>
**Coordination:** <active claims, pending file states, relevant open messages, or none>
**Approach:** <2-4 sentences>
**Risk:** Low | Medium | High
**Verify after:** <specific check>

Reply "go" (or "ok", "yes", "proceed") to start implementation.
```

Do not implement before the user approves.

## Implementation

After approval:

1. Renew the session heartbeat.
2. Claim the files/modules likely to be edited before changing them.
3. If another fresh active writer owns a needed file, do not edit it. Choose
   wait, request handoff, create a proposal/review note, ask for an integrator,
   split ownership, or ask the user. Before choosing, reread `state/index.json`
   and any `open_messages` targeting the contested file, owning session, task,
   workspace, agent, or role. If no relevant message exists and coordination is
   needed, create or ask to create a normal message record; it will be checked
   by the recipient at its next safe workflow boundary.
4. If a file has pending state but no active writer, read that state before
   editing and treat it as current provenance.
5. Implement the briefed action. Keep edits scoped to the stated files/modules.
6. If verification needs temporary logs, add them and remove them after the
   user verifies.
7. **Self-verify before deciding whether to stop.** Run the card's verification
   (the plan's `**Verify:**` / `## Verification` steps: tests, build, smoke,
   re-read). Capture whether it passed.

## Post-implementation gate (conditional)

Read `**Verify mode:**` from the active plan's `## Verification` section.
Default to `auto` when the line is absent (legacy/compact plans). For a
multi-phase plan, use the current phase's verify mode if it declares one,
otherwise the plan-level value.

Branch on (verify mode) x (did self-verification pass):

**A. `auto` and self-verification passed → do not stop for the user.**
Report the result and continue straight into the "After verified work" steps
below (plan/board/state update), then move to the next step or completion.
Output:

```markdown
Continue step complete (auto-verified).

**Files changed:** <list>
**Key changes:** <summary>
**Verification run:** <checks executed> -> PASSED
**Plan updates:** <summary or none>

Continuing to the next step.
```

Do not ask the user to press 1. There is nothing for them to verify that the
agent has not already verified.

**B. `user-ux` and self-verification passed → stop for the user's eyes.**
The card has a UI/UX surface only the user can judge. Output:

```markdown
Continue step complete - needs your check in the app.

**Files changed:** <list>
**Key changes:** <summary>
**Automated checks:** <checks executed> -> PASSED

**Check in the app:**
<exact, specific UI/UX steps for the user to look at and feel>

**Option 1 - Looks good** - say "1" or "verified"
**Option 2 - Changes / keep talking** - say "2" (then describe what to change)
```

Stop and wait.

**C. Self-verification failed or could not run (any verify mode) → stop and
report the blocker.** A failed or unrunnable check is a real stop, never an
auto-continue. Output:

```markdown
Continue step complete - verification did not pass.

**Files changed:** <list>
**Key changes:** <summary>
**Verification run:** <checks executed> -> FAILED / could not run
**What failed:** <specific failure / why it could not run>

I will not mark this verified. Say how to proceed, or "2" to keep talking.
```

Stop and wait.

## After verified work

These steps run when path A auto-verified, or after the user chooses Option 1
in path B. (Path C does not reach here until the failure is resolved.)

1. Remove temporary verification logs.
2. Update the plan. This is the session's running notes, and it is what
   `mpi-handoff` reads instead of summarising a huge context later - a few
   lines written now, while the details are fresh, replace ten minutes of
   reconstruction at the switch. Keep it to a few lines; this is a note, not a
   report.
   - Move or mark completed work under `## Completed`. This is plan-level
     progress, separate from the JSON board `done` column.
   - Keep `## Remaining Work` accurate.
   - Update `## Current State` so a fresh session with zero memory could pick
     up from it: where the work stands, the single next action, and any
     decision or gotcha found this step that is not obvious from the diff.
   - Add to `## Plan Drift` when reality diverged from the plan.
3. Complete or release file claims using the lifecycle operation:
   `complete`, `needs_review`, `needs_verification`, `needs_integration`,
   `verified`, or `released` as appropriate.
4. Update the task record to the appropriate status. Remember that released
   file ownership is not commit ownership; preserve pending-change provenance
   until review/integration/session close resolves it.
5. Update the JSON task workspace instead of embedding implementation state in
   `task.json`: mark the relevant item in `checklist.md`, add validation notes
   to `validation.md`, call `writeTask` for concise status/badge changes, and
   append `checklist.updated` or `validation.updated` events when meaningful.
   Move the card to `done` only after validation state is represented in the
   task workspace and the work is verified — by the user for a `user-ux` card,
   or by passing self-verification for an `auto` card.
6. If meaningful work remains, say:

```text
Step verified. Say "continue" to keep going, "handoff" to switch sessions, or "end session" to close.
```

7. If the plan is complete, say:

```text
Plan complete. Suggested next step: run `mpi-end-session` to preserve docs/rules/memory, commit, and close the JSON task card on the evidence in `validation.md`.
```

## If the user chooses "keep talking" / changes (Option 2)

Reached from path B or path C when the user wants changes or to keep talking
rather than accept the step. Do not run the "After verified work" steps. Stay in
conversation, address the requested changes, and append once:

```text
Context getting large? Run `mpi-handoff` - it commits, pushes, and writes the
handoff in about a minute.
```

## Hard rules

- Approval before implementation is mandatory.
- Card-write preflight is mandatory before any `column`, `maturity`, or
  `status` write: use the `## Card contract` values above, and read
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` and
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` for the write recipes. Do not
  derive legal values from existing cards.
- Never create a task card unless the user asked for one in the current
  request. Discovered work folds into the active card by default; see
  `## Discovered work`.
- Never hand-write or hand-edit a `task.json`. Every card write goes through a
  `mutate.md` recipe so the enum, coherence, and events stay correct.
- The card must be in `doing` before any implementation edit. In `file` mode,
  `beginImplementation` must have moved the card `todo -> doing`, set
  `maturity: "in-progress"`, and derived the checklist before you edit any
  file. Never implement a `todo` card in place; the lifecycle is always
  `To do -> Doing -> Done`, never `To do -> Done`. This applies on every entry
  path (direct continue, post-plan, or resumed handoff), not only the
  session-setup flow above.
- Post-implementation self-verification is mandatory: always run the card's
  verification before deciding whether to stop. Stopping for the user is
  mandatory only when the card's `**Verify mode:**` is `user-ux`, or when
  self-verification failed or could not run. For an `auto` card whose checks
  passed, do not stop for the user — report the passing result and continue.
- Do not commit or push; that belongs to `mpi-handoff` or `mpi-end-session`.
- Keep the plan's `## Current State` fresh after every verified step -
  `mpi-handoff` reads it rather than reconstructing; stale costs ten minutes.
- Do not force stale plan tasks. Update the plan when reality has changed.
- Do not spawn implementation workers here. When the next eligible unit is a
  valid `## Parallel Batch`, route it to `mpi-execute-parallel` without asking
  and announce the split; that skill is the only worker-spawning implementation
  path.
- Evaluating `## Autonomous dispatch` on every start is mandatory, and it is
  read-only: it never writes the board, `files.json`, or a claim. Dispatch
  without asking when two or more ready cards are provably disjoint, and report
  every excluded card with its reason.
- In read-only board entry mode, read one named task/card only and do not
  search sibling repositories or unrelated board surfaces.


