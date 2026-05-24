# kanban-ops/mutate — create, move, update entries

Read this when you need to add an entry, move one between columns, or change
fields on an existing entry. For schema see `_schema.md`. For step
manipulation see `steps.md`. For errors see `errors.md`.

---

## `createEntry(column, entry)`

`entry` shape (only required fields shown — caller may include `due`, `workload`):

```js
{
  title: "Short Title",
  tags: "[feature]",
  priority: "medium",
  defaultExpanded: true,
  body: "2-3 line summary."   // optional
}
```

1. Read the file.
2. Build the entry block as a single string. Example for a BACKLOG entry with
   no plan file ref:

   ```markdown
   ### Short Title

     - tags: [feature]
     - priority: medium
     - defaultExpanded: true
       ```md
       2-3 line summary.
       ```

   ```

   (Trailing blank line is significant — keeps the next entry separated.)

3. Locate the H2 for `column`. Insertion point is immediately after the blank
   line that follows the H2 (top of the column).
4. Use `Edit`:
   - `old_string`: H2 line + trailing blank line.
   - `new_string`: H2 line + blank line + new entry block.
5. Verify uniqueness: if `findEntry(e => e.title === entry.title)` already
   returns a hit, abort with the duplicate-title error from `errors.md`.

---

## `moveEntry(title, fromColumn, toColumn)`

Most common mutation. Recipe MUST be followed exactly.

1. Read the file.
2. Locate the entry block under `fromColumn`:
   - Start = the line `### <title>`.
   - End = the line immediately before either the next `### ` heading in the
     same column OR the next `## ` heading. Include the trailing blank line
     belonging to the entry.
3. Capture the block verbatim into a variable `block`.
4. **First Edit — remove from current column.**
   - `old_string` = `block` (verbatim).
   - `new_string` = empty string.
5. **Second Edit — insert at top of `toColumn`.**
   - `old_string` = the H2 line for `toColumn` plus its trailing blank line.
   - `new_string` = H2 line + blank line + `block`.
6. Optionally apply `updateEntry` mutations on the moved block (e.g. tag
   change, body fence rewrite) — see below.

### Worked example

Before — entry `Foo Bar` in BACKLOG, moving to PLANNING:

```markdown
## BACKLOG

### Foo Bar

  - tags: [feature]
  - priority: medium
  - defaultExpanded: true
    ```md
    Idea summary.
    ```

### Other Entry

  - tags: [bug]
  ...

## PLANNING

## IMPLEMENTING
```

After step 4 (block removed):

```markdown
## BACKLOG

### Other Entry

  - tags: [bug]
  ...

## PLANNING

## IMPLEMENTING
```

After step 5 (block reinserted at top of PLANNING):

```markdown
## BACKLOG

### Other Entry

  - tags: [bug]
  ...

## PLANNING

### Foo Bar

  - tags: [feature]
  - priority: medium
  - defaultExpanded: true
    ```md
    Idea summary.
    ```

## IMPLEMENTING
```

---

## `updateEntry(title, mutations)`

Generic in-place edit of an entry. Used after `moveEntry` to swap tags, set
the plan file body, or change priority.

Common mutations:

- **Replace tag list** (e.g. on PLANNING transition):
  - `Edit`: `old_string` = `  - tags: [feature]` (or whatever the current tag is),
    `new_string` = `  - tags: [PLAN]`.
  - Scope `old_string` so it's unique within the file — include the title
    line above as context if needed.
- **Set body fence to plan file ref**:
  - Replace the existing body fence (whatever it contains) with:
    ```
        ```md
        Plan file: docs/plans/YYYY-MM-DD-<slug>.md
        ```
    ```
  - Use enough surrounding context (title line + metadata) to make the Edit
    unique.
