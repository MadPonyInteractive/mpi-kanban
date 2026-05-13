---
name: mpi-continue
description: Continue active MPI work from the real current state. Use when the user says continue, resume, keep going, pick this back up, read a handoff and continue, continue this plan, or wants implementation to proceed from an MPI plan or handoff.
---

# mpi-continue Skill

## Purpose

Continue active work intelligently. This skill replaces rigid "execute next"
behavior: it reads the active kanban entry, plan, latest handoff, and current
workspace state, then proposes the next best action based on reality.

Plans are living documents. If implementation has drifted, update or annotate
the plan instead of forcing the next unchecked item.

## Pre-conditions

Find the active work from the first available source:

1. Handoff path mentioned by the user or visible in context.
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

1. Read the handoff if present.
2. Read the active plan.
3. Locate the kanban entry whose body contains `Plan file: <planPath>`.
4. If the entry is in PLANNING, move it to IMPLEMENTING and add stable steps:
   - Compact plan: one step, `Implementation`.
   - Large/adaptive plan: phase-level steps when phases exist; otherwise use
     lifecycle steps: `Orient current state`, `Implement active work`,
     `Verify behavior`, `Preserve knowledge`, `Close session`.
5. Inspect current workspace state with small commands (`git status`,
   targeted file reads/searches). Do not run large diffs unless needed.

## Orient and detect drift

Before proposing work, compare the plan/handoff with actual state:

- What is complete?
- What is pending?
- What changed since the plan was written?
- Are any remaining plan items obsolete, merged, or blocked?
- Is a `## Parallel Batch` now the right next unit?
- Are there docs/rules/memory notes that should be preserved before handoff?

If the plan is stale, edit the plan before implementation:

- Add a dated bullet under `## Plan Drift`.
- Update `## Current State`.
- Move obsolete work into `## Completed` or remove/rewrite remaining items.
- Keep the plan concise; do not preserve stale tasks for history when a drift
  note explains the change.

## Gate 1 - Continue brief

Before implementation, output a brief and stop:

```markdown
## Continue Brief: <next action>

**Source:** <plan path and handoff path if any>
**Current state:** <1-3 bullets>
**Plan drift:** <none or summary of plan edits made/proposed>
**Files likely touched:** <files/modules>
**Approach:** <2-4 sentences>
**Risk:** Low | Medium | High
**Verify after:** <specific check>

Reply "go" (or "ok", "yes", "proceed") to start implementation.
```

Do not implement before the user approves.

## Implementation

After approval, implement the briefed action. Keep edits scoped to the stated
files/modules. If verification needs temporary logs, add them and remove them
after the user verifies.

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
3. Flip the relevant kanban step when a lifecycle/phase boundary is complete.
4. If meaningful work remains, say:

```text
Step verified. Say "continue" to keep going, "handoff" to switch sessions, or "end session" to close.
```

5. If the plan is complete, say:

```text
Plan complete. Suggested next step: run /mpi-kanban:mpi-end-session to preserve docs/rules/memory, commit, and close the kanban entry.
```

## If user chooses Option 2

Do nothing else. Stay in conversation and append once:

```text
Context getting large? Run /mpi-kanban:mpi-handoff before starting a new session.
```

## Hard rules

- Approval before implementation is mandatory.
- Post-implementation verification choice is mandatory.
- Do not commit or push; committing is `mpi-end-session`'s responsibility.
- Do not force stale plan tasks. Update the plan when reality has changed.
- Do not run parallel implementation. Use `/mpi-kanban:mpi-execute-parallel`
  only for explicit `## Parallel Batch` sections.
