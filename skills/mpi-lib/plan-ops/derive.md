# plan-ops/derive - derive kanban steps from a plan

Read this when transitioning PLANNING -> IMPLEMENTING (deciding what `steps`
to put on the kanban entry), moving IMPLEMENTING -> VALIDATING after all
implementation steps are verified, or flipping a kanban step after a continue
action is verified. For shape see `_shape.md`. For mutations see `mutate.md`.

---

## Phased plan

- Steps = phase titles, stripped of `Phase N:` prefix, shortened to 3-6 words.
- A kanban step flips to `[x]` when `phaseAllDone(phase)` returns true.
- When every implementation step is `[x]`, the entry is ready to move from
  `IMPLEMENTING` to `VALIDATING`, not directly to `COMPLETED`.

### Worked example - phased plan -> kanban steps

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

Derived kanban steps:

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
- A checked compact-plan step means the entry is ready for `VALIDATING`.

### Worked example - compact plan -> kanban steps

Plan file:

```markdown
## Implementation

- [ ] Implement the planned change end to end. **Verify:** Run the smoke test.
```

Derived kanban steps:

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

When all lifecycle steps are checked, the implementation phase is complete and
the entry is ready for `VALIDATING`. `COMPLETED` requires an explicit user
approval gate after validation.
