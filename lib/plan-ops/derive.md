# plan-ops/derive — derive kanban steps from a plan

Read this when transitioning PLANNING → IMPLEMENTING (deciding what `steps`
to put on the kanban entry) or flipping a kanban step after a plan to-do is
verified. For shape see `_shape.md`. For mutations see `mutate.md`.

---

## Phased plan

- Steps = phase titles, stripped of `Phase N:` prefix, shortened to 3-6 words.
- A kanban step flips to `[x]` when `phaseAllDone(phase)` returns true.

### Worked example — phased plan → kanban steps

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

---

## Flat plan

- Steps = each plan to-do, summarized to 3-6 words.
- A kanban step flips to `[x]` when its corresponding plan to-do is `[x]`.
- Mapping is positional: kanban step at index N ↔ plan to-do at index N.

### Worked example — flat plan → kanban steps

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
