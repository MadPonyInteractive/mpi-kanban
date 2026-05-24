# plan-ops/_shape - compact vs large/adaptive plan detection

Plans live at `docs/plans/YYYY-MM-DD-<slug>.md` and come in compact or
large/adaptive shapes. Read this first when a skill needs to handle a plan it
has not yet inspected. For reading procedures see `read.md`. For mutations see
`mutate.md`. For deriving kanban steps see `derive.md`.

---

## Compact plan

```markdown
# Goal Title

## Current State

Known facts.

## Implementation

- [ ] Implement the planned change end to end. **Verify:** ...

## Completed

## Remaining Work

## Plan Drift

## Verification

## Preservation Notes
```

No `## Phase N` or `## Parallel Batch` headings. It usually has one primary
implementation item and final verification.

---

## Large/adaptive plan

```markdown
# Goal Title

## Current State

## Phase 1: Discovery

- [x] Investigate area A. **Verify:** ...
- [x] Investigate area B. **Verify:** ...

## Phase 2: Implementation

- [ ] Build module X. **Verify:** ...

## Parallel Batch: Independent UI Work

- [ ] Build component A. Ownership: js/components/A.js. Briefings: frontend-worker. **Verify:** ...
- [ ] Build component B. Ownership: js/components/B.js. Briefings: frontend-worker. **Verify:** ...

## Plan Drift

## Verification

## Preservation Notes
```

Each `## Phase N: ...` heading owns the to-dos beneath it until the next
`## ` heading or end of file. Each `## Parallel Batch` owns the batch tasks
beneath it and may only be run by `mpi-execute-parallel` when ownership is
declared and disjoint. Large plans default to `## Parallel Batch` sections for
independent, disjoint-ownership implementation work (see
`skills/mpi-create-large-plan/SKILL.md`); sequential phases are for work that
cannot be split safely.

---

## Detection

### Phase heading regex

```text
^## (?:Phase \d+|\w+ Phase)\b.*$
```

Matches both `## Phase 1: Discovery` and `## Discovery Phase`.

### Decision tree - plan type

1. Read the plan file.
2. Scan all `## ` headings.
3. If ANY heading starts with `## Parallel Batch` -> **parallel-capable large plan**.
4. If ANY heading matches the phase regex -> **large phased plan**.
5. Otherwise -> **compact plan**.

### Mixed plans

A phased plan with stray to-dos at the end (`[ ]` items appearing after the
last phase's to-dos but with no enclosing `## Phase N` heading) is treated as
phased. Stray to-dos belong to the last phase.
