# kanban-ops/steps — `- steps:` block manipulation

Read this when adding or flipping IMPLEMENTING entry steps. For schema see
`_schema.md`.

---

## `addSteps(title, steps)`

Add a `- steps:` block to an entry that does not yet have one. Used by
`mpi-continue` on the PLANNING → IMPLEMENTING transition.

`steps` is a list of strings (each step's text — 3-6 word summaries).

1. Read the file. Locate the entry block.
2. Build the steps block:

   ```
     - steps:
         - [ ] first step
         - [ ] second step
         - [ ] third step
   ```

   (2 spaces before `- steps:`, 6 spaces before each `- [ ]` item.)

3. Insert as the LAST metadata bullet — between the existing
   `- defaultExpanded: ...` line (or whichever is last) and the body fence.
4. Use `Edit` with `old_string` spanning the last metadata bullet and the
   opening of the body fence (` ```md`), `new_string` = same span with the
   steps block inserted before the fence.

---

## `markStep(title, stepIndexOrText, done)`

Flip a single step's checkbox.

1. Read the file. Locate the entry, then the step.
2. Match the step by text (preferred) or by zero-based index in the steps list.
3. `Edit`:
   - `old_string` = `      - [ ] <step text>` (or `[x]` if flipping back).
   - `new_string` = `      - [x] <step text>` (or `[ ]`).
4. Scope `old_string` to be unique — if the same step text appears in another
   entry, include the entry title line above as context.

---

## `allStepsDone(title)`

1. Read the file. Locate the entry.
2. If the entry has no `- steps:` block → return `false`.
   (Protects `mpi-end-session`: an IMPLEMENTING entry with no steps yet is
   mid-flight, not complete.)
3. If every step matches `^      - \[x\] ` → return `true`.
4. Otherwise return `false`.
