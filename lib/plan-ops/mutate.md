# plan-ops/mutate — flip plan checkboxes

Read this when marking a plan to-do done or checking phase completion. For
shape detection see `_shape.md`. For step derivation see `derive.md`.

---

## `markTodoDone(planPath, todoText)`

Flip a single plan to-do from `[ ]` to `[x]`.

1. Read the file.
2. `Edit`:
   - `old_string` = `- [ ] <todoText>` (verbatim — match the exact line text).
   - `new_string` = `- [x] <todoText>`.
3. Scope `old_string` with surrounding context (line above and below) only if
   the to-do text alone is not unique in the file.

---

## `phaseAllDone(phase)`

Returns `true` if every to-do in the given phase is `[x]`. Used by
`mpi-execute-next` to decide whether to flip the matching kanban step.

```
phase.todos.every(t => t.done)
```
