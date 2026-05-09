# plan-ops/read — read to-dos and phases

Read this to extract structured to-dos from a plan. For shape detection see
`_shape.md`.

---

## `readTodos(planPath)` — for flat plans

1. Read the file.
2. Collect every line matching `^- \[( |x)\] (.+)$` under `## To-do list` (or
   under no specific heading if the plan has none).
3. Return list: `[{ index, text, done }]`. `index` is zero-based.

For a phased plan: prefer `readPhases` instead.

---

## `readPhases(planPath)` — for phased plans

1. Read the file.
2. For each `## Phase ...` heading:
   - `title`: heading text with `Phase N:` prefix stripped, trimmed.
   - `todos`: every `- [ ]` / `- [x]` bullet between this heading and the next
     `## ` heading (or end of file). Stray to-dos after the last phase belong
     to the last phase (mixed-plan rule).
3. Return list: `[{ index, title, todos: [{ text, done }] }]`. `index` is
   zero-based.
