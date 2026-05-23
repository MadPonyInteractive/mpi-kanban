---
name: mpi-continue
description: Continue active MPI work from the real current state. Use when the user says "continue this MPI plan", "MPI continue", "continue", "resume", "keep going", "pick this back up", "read a handoff and continue", "$mpi-continue", or wants implementation to proceed from an MPI plan or handoff.
---

# mpi-continue Skill

## Purpose

Continue active work intelligently. This skill replaces rigid "execute next"
behavior: it reads the active kanban entry, plan, latest handoff, and current
workspace state, then proposes the next best action based on reality.

When shared coordination state exists, `mpi-continue` also reads
`.agents/mpi-kanban/state/index.json` first and follows its pointers only as
needed. The shared contract is documented in
`${CLAUDE_PLUGIN_ROOT}/docs/coordination/README.md`.
Lifecycle operations are documented in
`${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/lifecycle.md` and status values in
`${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/statuses.md`.

Plans are living documents. If implementation has drifted, update or annotate
the plan instead of forcing the next unchecked item.

Invocation: Claude Code users may run `/mpi-kanban:mpi-continue`; Codex users
may run `$mpi-continue` or ask naturally to continue the MPI plan. References
using `${CLAUDE_PLUGIN_ROOT}` mean the installed plugin root; Codex resolves
the same files relative to this plugin root.

## Pre-conditions

Find the active work from the first available source:

1. Handoff path mentioned by the user or visible in context, including either
   `.agents/mpi-kanban/state/handoffs/<uuid>.json` or legacy
   `docs/handoffs/*.json`.
2. Plan path mentioned by the user or visible in context.
3. IMPLEMENTING kanban entry with a `Plan file:` body line.
4. PLANNING kanban entry with a `Plan file:` body line.

If none is visible, ask:

```text
Which MPI plan or handoff should I continue from? Please paste the path.
```

## Session setup

Lib pointers, read only when needed:

- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/find.md` - `findEntry`
- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/mutate.md` - `moveEntry`
- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/steps.md` - `addSteps`, `markStep`
- `${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/lifecycle.md` - session/task/file claim lifecycle
- `${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/statuses.md` - state vocabulary
- `${CLAUDE_PLUGIN_ROOT}/lib/project-knowledge/indexing.md` - context-budget rules

1. Read the handoff if present. If it is a legacy `docs/handoffs/` pointer to a
   canonical `.agents/` handoff, load the canonical handoff before continuing.
2. **Load project knowledge if present.** Read
   `.agents/mpi-kanban/project-profile.md` and
   `.agents/mpi-kanban/project-knowledge-index.md` before the Continue Brief.
   Pick the topic block matching the active plan. Load only the listed
   docs/rules; do not rediscover the whole project. If the profile is
   absent, fall back to the existing pre-condition behavior.
3. Read `lib/coordination-ops/lifecycle.md`. Call `ensureStateRoot()` when
   coordination state is relevant, then read `state/index.json` as the active
   coordination facade.
4. Register or renew an `implementer` session and create or attach a task
   record for the active kanban entry and plan.
5. Read the active plan.
6. Locate the kanban entry whose body contains `Plan file: <planPath>`.
7. If the entry is in PLANNING, move it to IMPLEMENTING and add stable steps:
   - Compact plan: one step, `Implementation`.
   - Large/adaptive plan: phase-level steps when phases exist; otherwise use
     lifecycle steps: `Orient current state`, `Implement active work`,
     `Verify behavior`, `Preserve knowledge`, `Close session`.
8. Inspect current workspace state with small commands (`git status`,
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
- Are there docs/rules/memory notes that should be preserved before handoff?

If the plan is stale, edit the plan before implementation:

- Add a dated bullet under `## Plan Drift`.
- Update `## Current State`.
- Move obsolete work into `## Completed` or remove/rewrite remaining items.
- Keep the plan concise; do not preserve stale tasks for history when a drift
  note explains the change.

## Parallel batch routing

If the next eligible unit is a valid `## Parallel Batch`, make the parallel path
the default. Instead of a sequential continue brief, tell the user:

```text
Next unit is a parallel batch: "<batch title>". Default path is to run it through
$mpi-execute-parallel in Codex or /mpi-kanban:mpi-execute-parallel in Claude Code.
Say "go parallel" to route there, or "sequential" to implement it one task at a time here.
```

Route to `mpi-execute-parallel` on confirmation. `mpi-continue` never spawns
implementation workers itself. Fall back to a sequential continue brief only if
the user explicitly chooses sequential, or the batch fails an eligibility gate.

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
**Coordination:** <active claims, pending file states, or none>
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
   split ownership, or ask the user.
4. If a file has pending state but no active writer, read that state before
   editing and treat it as current provenance.
5. Implement the briefed action. Keep edits scoped to the stated files/modules.
6. If verification needs temporary logs, add them and remove them after the
   user verifies.

After implementation, output:

```markdown
Continue step complete.

**Files changed:** <list>
**Key changes:** <summary>
**Plan updates:** <summary or none>

**Verify:**
<exact verification steps>

**Option 1 - Verified** - say "1" or "verified"
**Option 2 - Keep talking** - say "2" or "keep talking"
```

Stop and wait.

## If user chooses Option 1

1. Remove temporary verification logs.
2. Update the plan:
   - Move or mark completed work under `## Completed`.
   - Update `## Current State`.
   - Keep `## Remaining Work` accurate.
3. Complete or release file claims using the lifecycle operation:
   `complete`, `needs_review`, `needs_verification`, `needs_integration`,
   `verified`, or `released` as appropriate.
4. Update the task record to the appropriate status. Remember that released
   file ownership is not commit ownership; preserve pending-change provenance
   until review/integration/session close resolves it.
5. Flip the relevant kanban step when a lifecycle/phase boundary is complete.
   Update kanban tags only as a coarse user-facing summary and only when useful.
6. If meaningful work remains, say:

```text
Step verified. Say "continue" to keep going, "handoff" to switch sessions, or "end session" to close.
```

7. If the plan is complete, say:

```text
Plan complete. Suggested next step: run $mpi-end-session in Codex or /mpi-kanban:mpi-end-session in Claude Code to preserve docs/rules/memory, commit, and close the kanban entry.
```

## If user chooses Option 2

Do nothing else. Stay in conversation and append once:

```text
Context getting large? Run $mpi-handoff in Codex or /mpi-kanban:mpi-handoff in Claude Code before starting a new session.
```

## Hard rules

- Approval before implementation is mandatory.
- Post-implementation verification choice is mandatory.
- Do not commit or push; committing is `mpi-end-session`'s responsibility.
- Do not force stale plan tasks. Update the plan when reality has changed.
- Do not spawn implementation workers here. When the next eligible unit is a
  valid `## Parallel Batch`, default to routing it to `$mpi-execute-parallel` in
  Codex or `/mpi-kanban:mpi-execute-parallel` in Claude Code; that skill is the
  only worker-spawning implementation path.
