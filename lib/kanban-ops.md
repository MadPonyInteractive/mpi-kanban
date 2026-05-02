# kanban-ops — operations on `.claude/mpi-kanban/kanban.md`

Reference doc loaded by skills that need to read or mutate the Kanban board.
Self-contained: a skill author following this doc should NOT need SPEC.md to
implement any mutation.

The board is plain Markdown rendered as an interactive board by the
`holooooo.markdown-kanban` VS Code extension. Stay strictly within the schema
below — the extension breaks on unknown fields and unknown columns.

---

## File location

```
<project-root>/.claude/mpi-kanban/kanban.md
```

NOT at project root. NOT inside `.claude/` directly. Always inside the
`.claude/mpi-kanban/` subfolder.

The board file is separate from the per-project plugin config
(`.claude/mpi-kanban.local.md`) so `.claude/*.local.md` gitignores can cover
config without ignoring the board.

---

## File schema

### Columns (locked, exact order)

```markdown
## BACKLOG

## PLANNING

## IMPLEMENTING

## COMPLETED
```

Four H2 headings, exact spelling, exact order. Never add, rename, or remove a
column. An empty column is just the H2 header, a blank line, and the next H2.

### Entry shape

```markdown
### Entry Title

  - due: 2026-05-03
  - tags: [bug]
  - priority: high
  - workload: Easy
  - defaultExpanded: true
  - steps:
      - [ ] step text
      - [x] another step
    ```md
    Free-form body. Plan file ref lives here when present:
    Plan file: docs/plans/YYYY-MM-DD-<slug>.md
    ```
```

Notes on shape:

- Title is an H3 (`### `). Title text is the entry's identity — duplicates
  within the same `kanban.md` are an error.
- Metadata bullets are 2-space-indented, single-dash bullets, immediately under
  the title.
- The body fence is a 4-space-indented ```` ```md ```` fenced block. It belongs
  with the entry (so cut/paste during a move includes it).
- `steps` is a nested checklist (4-space-indented under `- steps:`). Only
  IMPLEMENTING entries should carry it.
- For PLANNING and IMPLEMENTING entries, the body fence MUST contain a line
  matching `Plan file: <path>` (case-insensitive on `file`).

### Locked metadata fields

| Field | Type | Required | Values |
|---|---|---|---|
| `due` | date | No | `YYYY-MM-DD` |
| `tags` | list | Yes | `[bug]`, `[feature]`, `[Idea]`, `[PLAN]`, `[refactor]` |
| `priority` | enum | Yes | `high` \| `medium` \| `low` |
| `workload` | enum | No | `Easy` \| `Medium` \| `Hard` |
| `defaultExpanded` | bool | Yes | `true` \| `false` |
| `steps` | nested checklist | IMPLEMENTING only | `- [ ] text` / `- [x] text` |

**Never invent new fields.** The VS Code extension breaks on unknown fields.

---

## Parser regexes

Use these patterns when extracting structure from the file. All examples assume
the file has been read in full with the `Read` tool.

| Element | Regex | Notes |
|---|---|---|
| Column heading | `^## (BACKLOG\|PLANNING\|IMPLEMENTING\|COMPLETED)\s*$` | Multiline. |
| Entry heading | `^### (.+?)\s*$` | Capture group 1 = title. |
| Metadata bullet | `^  - (\w+):\s*(.*)$` | Capture: field name, raw value. |
| Steps line | `^  - steps:\s*$` | Followed by 6-space-indented `- [ ]` / `- [x]` lines. |
| Step item | `^      - \[( \|x)\] (.+?)\s*$` | Capture: state char, step text. |
| Body fence open | ` ^    ` ```md` | 4-space indent + ```` ```md ````. |
| Body fence close | ` ^    ` ``` ` | 4-space indent + ```` ``` ````. |
| Plan-file ref (in body) | `^Plan [Ff]ile:\s*(.+)$` | Multiline, applied to body content only. |

---

## Procedures

Each procedure below is a recipe a skill follows using the `Read`, `Edit`, and
`Write` tools. No JS or external runtime — all mutation is `Edit`/`Write` on
the file.

### `findKanban()`

1. Resolve the path: `<project-root>/.claude/mpi-kanban/kanban.md`.
2. Try to `Read` it.
3. If found → return path + contents.
4. If missing → return `null`. The caller decides whether to bootstrap
   (`ensureKanban`) or surface a setup notice.

### `ensureKanban()`

1. Call `findKanban()`.
2. If found → return the path.
3. If missing:
   a. `Read` `templates/kanban.md` from the plugin root.
   b. `Write` the contents to `<project-root>/.claude/mpi-kanban/kanban.md`.
      The Write tool will create the `.claude/mpi-kanban/` directory.
   c. Emit a one-time setup notice in chat:
      - Clickable link: `[kanban.md](.claude/mpi-kanban/kanban.md)`
      - Marketplace link: `https://marketplace.visualstudio.com/items?itemName=holooooo.markdown-kanban`
      - One-line note: "Install the extension to see this file as an interactive board."
4. Return the path.

**Skip `ensureKanban` for `mpi-brief-rule`** — that skill is board-independent.

### `kanbanLink()`

Return the clickable markdown link the skill should print in chat whenever it
references the board:

```
[kanban.md](.claude/mpi-kanban/kanban.md)
```

### `listEntries(column)`

1. Read the file.
2. Locate the H2 heading that matches `column` (one of the four).
3. Collect every `### ` block until the next H2 (or end of file).
4. For each block: parse title, metadata bullets, body fence (if present),
   steps (if present).
5. Return a list of entry objects.

### `findEntry(predicate)`

1. For each column in order: `BACKLOG`, `PLANNING`, `IMPLEMENTING`, `COMPLETED`.
2. Run `listEntries(column)`.
3. Return the first entry matching `predicate`, plus its column.
4. If none match → return `null`.

Common predicates:

- `entry.title === <title>` — used by `mpi-write-plan` when matching an existing BACKLOG entry by title.
- Body contains `Plan file: <path>` — used by `mpi-execute-next`, `mpi-end-session`, `mpi-handoff` to locate the entry tied to the active plan.

### `createEntry(column, entry)`

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
2. Build the entry block as a single string. Example for a BACKLOG entry with no
   plan file ref:

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

3. Locate the H2 for `column`. The insertion point is immediately after the
   blank line that follows the H2 (i.e. at the top of the column).
4. Use `Edit` with:
   - `old_string`: the H2 line + its trailing blank line.
   - `new_string`: H2 line + blank line + new entry block.
5. Verify uniqueness: if `findEntry(e => e.title === entry.title)` already
   returns a hit, abort with an error — duplicate titles are forbidden.

### `moveEntry(title, fromColumn, toColumn)`

This is the most common mutation. The recipe MUST be followed exactly.

1. Read the file.
2. Locate the entry block under `fromColumn`:
   - Start = the line `### <title>`.
   - End = the line immediately before either the next `### ` heading in the
     same column OR the next `## ` heading. Include the trailing blank line
     that belongs to the entry.
3. Capture that block verbatim into a variable `block`.
4. **First Edit — remove the block from its current column.**
   - `old_string` = `block` (verbatim).
   - `new_string` = empty string.
5. **Second Edit — insert the block at the top of `toColumn`.**
   - `old_string` = the H2 line for `toColumn` plus its trailing blank line.
   - `new_string` = H2 line + blank line + `block`.
6. Optionally apply `updateEntry` mutations on the moved block (e.g. tag
   change, body fence rewrite) — see below.

**Worked example.**

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

### `updateEntry(title, mutations)`

Generic in-place edit of an entry. Used after `moveEntry` to swap tags, set the
plan file body, or change priority.

Common mutations:

- **Replace tag list** (e.g. on PLANNING transition):
  - `Edit`: `old_string` = `  - tags: [feature]` (or whatever the current tag is),
    `new_string` = `  - tags: [PLAN]`.
  - Scope the `old_string` so it's unique within the file — include the title
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

### `addSteps(title, steps)`

Add a `- steps:` block to an entry that does not yet have one. Used by
`mpi-execute-next` on the PLANNING → IMPLEMENTING transition.

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

3. Insert it as the LAST metadata bullet — between the existing
   `- defaultExpanded: ...` line (or whichever is last) and the body fence.
4. Use `Edit` with `old_string` spanning the last metadata bullet and the
   opening of the body fence (` ```md`), `new_string` = same span with the
   steps block inserted before the fence.

### `markStep(title, stepIndexOrText, done)`

Flip a single step's checkbox.

1. Read the file. Locate the entry, then the step.
2. Match the step by text (preferred) or by zero-based index in the steps list.
3. `Edit`:
   - `old_string` = `      - [ ] <step text>` (or `[x]` if flipping back).
   - `new_string` = `      - [x] <step text>` (or `[ ]`).
4. Scope `old_string` to be unique — if the same step text appears in another
   entry, include the entry title line above as context.

### `allStepsDone(title)`

1. Read the file. Locate the entry.
2. If the entry has no `- steps:` block → return `false`.
   (This protects `mpi-end-session`: an IMPLEMENTING entry with no steps yet
   is mid-flight, not complete.)
3. If every step matches `^      - \[x\] `, return `true`.
4. Otherwise return `false`.

---

## Error cases

| Case | Detection | Behavior |
|---|---|---|
| Duplicate title | `findEntry` returns a hit before `createEntry` runs | Abort with `Error: Duplicate kanban entry title: "<title>". Resolve manually before continuing.` |
| Missing column | One of the 4 H2 headings is absent | Abort with `Error: kanban.md is missing the "## <COLUMN>" heading. Restore from templates/kanban.md.` |
| Malformed entry | `### ` block missing required metadata bullets (tags, priority, defaultExpanded) | Report which entry, do not auto-fix. |
| Unknown metadata field | Bullet matches `- (\w+):` where `\w+` is outside the locked schema | Refuse to write it. If reading, ignore + warn. |
| `Plan file:` ref absent on PLANNING/IMPLEMENTING entry | Body fence contains no matching line | Abort the move and ask the user which plan to attach. |

Skills MUST surface errors to the user instead of silently editing around them.
