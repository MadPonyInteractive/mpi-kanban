# plan-ops/_shape — flat vs phased plan detection

Plans live at `docs/plans/YYYY-MM-DD-<slug>.md` and come in two shapes. Read
this first when your skill needs to handle a plan it has not yet inspected.
For reading procedures see `read.md`. For mutations see `mutate.md`. For
deriving kanban steps see `derive.md`.

The plan file is the source of truth for to-do completion. Never read the
kanban to decide what's done; always re-read the plan.

---

## Flat plan

```markdown
# Goal Title

## To-do list

- [ ] First task. **Verify:** ...
- [ ] Second task. **Verify:** ...
- [x] Third task (done). **Verify:** ...
```

No `## Phase N` headings. Each `[ ]` / `[x]` bullet is a discrete to-do.

---

## Phased plan

```markdown
# Goal Title

## Phase 1: Discovery

- [x] Investigate area A. **Verify:** ...
- [x] Investigate area B. **Verify:** ...

## Phase 2: Implementation

- [ ] Build module X. **Verify:** ...
- [ ] Build module Y. **Verify:** ...

## Phase 3: Cleanup

- [ ] Remove dead code. **Verify:** ...
```

Each `## Phase N: ...` heading owns the to-dos beneath it (until the next
`## ` heading or end of file).

---

## Detection

### Phase heading regex

```
^## (?:Phase \d+|\w+ Phase)\b.*$
```

Matches both `## Phase 1: Discovery` and `## Discovery Phase`.

### Decision tree — "is this plan phased?"

1. Read the plan file.
2. Scan all `## ` headings.
3. If ANY heading matches the phase regex → **phased**.
4. Otherwise → **flat**.

### Mixed plans

A phased plan with stray flat to-dos at the end (`[ ]` items appearing after
the last phase's to-dos but with no enclosing `## Phase N` heading) is
treated as **phased**. Stray to-dos belong to the last phase.
