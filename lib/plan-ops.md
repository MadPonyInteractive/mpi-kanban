# plan-ops — operations on plan files in `docs/plans/`

Reference doc loaded by skills that need to read or update an MPI plan file.
Plan files live at `docs/plans/YYYY-MM-DD-<slug>.md`.

The plan file is the source of truth for to-do completion. The kanban entry's
`steps` block mirrors the plan — when a plan to-do flips, the matching kanban
step flips too (rules below).

---

## Plan file shape

Plans come in two shapes. Skills MUST detect which shape before deriving
kanban steps.

### Flat plan

```markdown
# Goal Title

## To-do list

- [ ] First task. **Verify:** ...
- [ ] Second task. **Verify:** ...
- [x] Third task (done). **Verify:** ...
```

No `## Phase N` headings. Each `[ ]` / `[x]` bullet is a discrete to-do.

### Phased plan

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
the last phase's to-dos but with no enclosing `## Phase N` heading) is treated
as **phased**. Stray to-dos belong to the last phase.

---

## Procedures

### `readTodos(planPath)`

For a flat plan:

1. Read the file.
2. Collect every line matching `^- \[( |x)\] (.+)$` under `## To-do list` (or
   under no specific heading if the plan has none).
3. Return list: `[{ index, text, done }]`. `index` is zero-based.

For a phased plan: prefer `readPhases` instead.

### `readPhases(planPath)`

1. Read the file.
2. For each `## Phase ...` heading:
   - `title`: heading text with `Phase N:` prefix stripped, trimmed.
   - `todos`: every `- [ ]` / `- [x]` bullet between this heading and the next
     `## ` heading (or end of file). Stray to-dos after the last phase belong
     to the last phase (mixed-plan rule).
3. Return list: `[{ index, title, todos: [{ text, done }] }]`. `index` is
   zero-based.

### `markTodoDone(planPath, todoText)`

Flip a single plan to-do from `[ ]` to `[x]`.

1. Read the file.
2. `Edit`:
   - `old_string` = `- [ ] <todoText>` (verbatim — match the exact line text).
   - `new_string` = `- [x] <todoText>`.
3. Scope `old_string` with surrounding context (the line above and below) only
   if the to-do text alone is not unique in the file.

### `phaseAllDone(phase)`

Returns `true` if every to-do in the given phase is `[x]`. Used by
`mpi-execute-next` to decide whether to flip the matching kanban step.

```
phase.todos.every(t => t.done)
```

---

## Step derivation — phases vs flat to-dos

When `mpi-execute-next` transitions PLANNING → IMPLEMENTING, it derives the
kanban entry's `steps` block from the plan:

### Phased plan

- Steps = phase titles, stripped of `Phase N:` prefix, shortened to 3-6 words.
- A kanban step flips to `[x]` when `phaseAllDone(phase)` returns true.

### Flat plan

- Steps = each plan to-do, summarized to 3-6 words.
- A kanban step flips to `[x]` when its corresponding plan to-do is `[x]`.
- Mapping is positional: kanban step at index N ↔ plan to-do at index N.

---

## Worked examples

### Phased plan → kanban steps

Plan file:

```markdown
## Phase 1: Discovery
- [x] Investigate area A
- [x] Investigate area B

## Phase 2: Implementation
- [ ] Build module X
- [ ] Build module Y

## Phase 3: Cleanup
- [ ] Remove dead code
```

Derived kanban steps (3 phases → 3 steps):

```
  - steps:
      - [x] Discovery
      - [ ] Implementation
      - [ ] Cleanup
```

Phase 1 is fully `[x]` in the plan, so its kanban step is `[x]`. Phases 2 and
3 still have `[ ]` to-dos, so their steps stay `[ ]`.

### Flat plan → kanban steps

Plan file:

```markdown
## To-do list

- [ ] Add OpenAPI schema for /users endpoint
- [ ] Wire schema into router
- [ ] Add integration test for /users
```

Derived kanban steps (3 to-dos → 3 steps, summarized):

```
  - steps:
      - [ ] OpenAPI schema for /users
      - [ ] Wire schema into router
      - [ ] Integration test for /users
```

When the user verifies the first to-do, `mpi-execute-next`:

1. Calls `markTodoDone(plan, "Add OpenAPI schema for /users endpoint")`.
2. Looks up the kanban step at the same index (0).
3. Calls `markStep(title, "OpenAPI schema for /users", true)`.

---

## Notes

- Plan files MUST NOT contain `<!-- trackers ... -->` blocks. The Nimbalyst
  tracker logic was removed in the kanban migration.
- Skills are responsible for keeping the kanban steps mirror in sync with the
  plan. The plan is the source of truth — never read the kanban to decide
  what's done; always re-read the plan.
