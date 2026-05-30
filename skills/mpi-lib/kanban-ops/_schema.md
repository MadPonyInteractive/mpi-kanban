# kanban-ops/_schema â€” board file schema

Reference for legacy compatibility and migration code touching `kanban.md`.
New task-board work should use `task-board-ops/_schema.md` and
`.agents/mpi-kanban/board.json`.

---

## Legacy file location

```
<project-root>/.agents/mpi-kanban/kanban.md
```

NOT at project root. NOT inside `.claude/` for new snapshots. Legacy projects
may still have `.claude/mpi-kanban/kanban.md`.

Once `.agents/mpi-kanban/board.json` exists, this Markdown file is a migration
input or snapshot. Do not update both files as live sources of truth.

---

## Columns (locked, exact order)

```markdown
## BACKLOG

## PLANNING

## IMPLEMENTING

## VALIDATING

## COMPLETED
```

Five H2 headings, exact spelling, exact order. Never add, rename, or remove a
column. An empty column is just the H2 header, a blank line, and the next H2.

Legacy four-column boards that omit `## VALIDATING` are readable, but any skill
that needs to mutate board lifecycle state must pause and ask before inserting
`## VALIDATING` between `## IMPLEMENTING` and `## COMPLETED`. Fresh boards use
the five-column template directly.

### Board-shape drift

A board is "shape-drifted" when any of these is true:

- A locked column (`BACKLOG`, `PLANNING`, `IMPLEMENTING`, `VALIDATING`,
  `COMPLETED`) is missing.
- Columns appear out of order.
- An unknown H2 column is present.

`mpi-project-setup` and `mpi-project-refresh` MUST detect this and propose
migration. The migration proposal lists the columns currently present, the
columns to insert, and the insertion positions. It never reorders user entries
across columns. It only:

- inserts missing locked columns in canonical position with an empty body;
- flags unknown H2 columns for the user to keep, rename, or remove (never
  silently delete);
- leaves entries inside existing columns untouched.

Other skills (`mpi-create-plan`, `mpi-continue`, `mpi-end-session`) must not
silently rewrite the board shape. They may insert a single missing
`## VALIDATING` between `## IMPLEMENTING` and `## COMPLETED` after asking, but
broader shape repair belongs to setup/refresh.

### Forbidden freehand entry format

Entries are ALWAYS `### Title` + 2-space-indented metadata bullets + a fenced
body, as shown above. The following shapes are NOT valid entries and MUST NOT
be written by any skill, even when surrounding entries on the board already use
them:

- A top-level bullet as title: `- **Title**` or `* Title` directly under an H2
  column.
- Free-form numbered or bulleted "Steps:" lines outside the locked `- steps:`
  metadata block.
- A `Plan file:` line outside the 4-space-indented ```` ```md ```` body fence.
- Any metadata key not in the locked metadata table.

If a skill encounters freehand entries on an existing board, treat them as
malformed and surface them to the user. Do not adopt the malformed style for
new entries.

---

## Entry shape

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

- Title is an H3 (`### `). Title text is the entry's identity â€” duplicates
  within the same `kanban.md` are an error.
- Metadata bullets: 2-space-indented, single-dash, immediately under title.
- Body fence: 4-space-indented ```` ```md ```` block. Belongs with the entry
  (cut/paste during a move includes it).
- `steps` is a nested checklist (4-space-indented under `- steps:`). Only
  IMPLEMENTING and VALIDATING entries should carry it.
- For PLANNING, IMPLEMENTING, and VALIDATING entries, the body fence MUST
  contain a line matching `Plan file: <path>` (case-insensitive on `file`).

---

## Locked metadata fields

| Field | Type | Required | Values |
|---|---|---|---|
| `due` | date | No | `YYYY-MM-DD` |
| `tags` | list | Yes | `[bug]`, `[feature]`, `[Idea]`, `[PLAN]`, `[refactor]` |
| `priority` | enum | Yes | `high` \| `medium` \| `low` |
| `workload` | enum | No | `Easy` \| `Medium` \| `Hard` |
| `defaultExpanded` | bool | Yes | `true` \| `false` |
| `steps` | nested checklist | IMPLEMENTING/VALIDATING only | `- [ ] text` / `- [x] text` |

**Never invent new fields.** The VS Code extension breaks on unknown fields.

---

## Parser regexes

| Element | Regex | Notes |
|---|---|---|
| Column heading | `^## (BACKLOG\|PLANNING\|IMPLEMENTING\|VALIDATING\|COMPLETED)\s*$` | Multiline. |
| Entry heading | `^### (.+?)\s*$` | Capture group 1 = title. |
| Metadata bullet | `^  - (\w+):\s*(.*)$` | Capture: field name, raw value. |
| Steps line | `^  - steps:\s*$` | Followed by 6-space-indented `- [ ]` / `- [x]` lines. |
| Step item | `^      - \[( \|x)\] (.+?)\s*$` | Capture: state char, step text. |
| Body fence open | ` ^    ` ```md` | 4-space indent + ```` ```md ````. |
| Body fence close | ` ^    ` ``` ` | 4-space indent + ```` ``` ````. |
| Plan-file ref (in body) | `^Plan [Ff]ile:\s*(.+)$` | Multiline, body content only. |
