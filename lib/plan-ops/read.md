# plan-ops/read - read plan work units

Read this to extract structured work units from a plan. For shape detection
see `_shape.md`.

---

## `readTodos(planPath)` - for compact plans or non-phased sections

1. Read the file.
2. Collect every line matching `^- \[( |x)\] (.+)$` under
   `## Implementation`, `## Remaining Work`, or under no specific heading if
   the plan has none.
3. Return list: `[{ index, text, done }]`. `index` is zero-based.

For a phased plan, prefer `readPhases` instead.

---

## `readPhases(planPath)` - for phased plans

1. Read the file.
2. For each `## Phase ...` heading:
   - `title`: heading text with `Phase N:` prefix stripped, trimmed.
   - `todos`: every `- [ ]` / `- [x]` bullet between this heading and the next
     `## ` heading (or end of file). Stray to-dos after the last phase belong
     to the last phase (mixed-plan rule).
3. Return list: `[{ index, title, todos: [{ text, done }] }]`. `index` is
   zero-based.

---

## `readParallelBatches(planPath)` - for parallel execution

1. Read the file.
2. For each `## Parallel Batch` heading:
   - `title`: heading text after `Parallel Batch:`.
   - `todos`: every `- [ ]` / `- [x]` bullet until the next `## ` heading.
   - Parse `Ownership:`, `Briefings:`, and `**Verify:**` from each todo.
3. Return list:
   `[{ index, title, todos: [{ text, done, ownership, briefings, verify }] }]`.
