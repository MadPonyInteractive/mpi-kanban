# plan-ops/derive - derive task checklist items from a plan

Read this when transitioning a task from `todo` to `doing`, deciding what
checklist items to put in the task workspace, or flipping a checklist item after
a continue action is verified. For shape see `_shape.md`. For mutations see
`mutate.md`.

---

## Phased plan

- Steps = phase titles, stripped of `Phase N:` prefix, shortened to 3-6 words.
- A task checklist item flips to `[x]` when `phaseAllDone(phase)` returns true.
- When every implementation item is `[x]`, validation state should be recorded
  in the task workspace before moving the task to `done`.

### Worked example - phased plan -> task checklist

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

Derived task checklist:

```text
  - steps:
      - [x] Discovery
      - [ ] Implementation
      - [ ] Cleanup
```

---

## Compact plan

- Steps = one stable step: `Implementation`.
- The step flips to `[x]` when the implementation item is verified and the
  plan's `## Remaining Work` is empty or explicitly complete.
- A checked compact-plan item means implementation is ready for validation
  notes in the task workspace.

### Worked example - compact plan -> task checklist

Plan file:

```markdown
## Implementation

- [ ] Implement the planned change end to end. **Verify:** Run the smoke test.
```

Derived task checklist:

```text
  - steps:
      - [ ] Implementation
```

---

## Large adaptive plan without phases

If a large plan has no explicit phase headings, use lifecycle steps:

```text
  - steps:
      - [ ] Orient current state
      - [ ] Implement active work
      - [ ] Verify behavior
      - [ ] Preserve knowledge
      - [ ] Close session
```

These steps are intentionally stable even when the plan drifts.

When all lifecycle items are checked, the implementation phase is complete and
validation state should be recorded in the task workspace before moving the
task to `done`.
