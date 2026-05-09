# kanban-ops/_schema — board file schema

Reference for any skill touching `kanban.md`. Read this first when you do not
already know the column/entry/metadata layout.

---

## File location

```
<project-root>/.claude/mpi-kanban/kanban.md
```

NOT at project root. NOT inside `.claude/` directly. Always inside the
`.claude/mpi-kanban/` subfolder. The board file is separate from per-project
plugin config (`.claude/mpi-kanban.local.md`) so `.claude/*.local.md`
gitignores can cover config without ignoring the board.

---

## Columns (locked, exact order)

```markdown
## BACKLOG

## PLANNING

## IMPLEMENTING

## COMPLETED
```

Four H2 headings, exact spelling, exact order. Never add, rename, or remove a
column. An empty column is just the H2 header, a blank line, and the next H2.

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

- Title is an H3 (`### `). Title text is the entry's identity — duplicates
  within the same `kanban.md` are an error.
- Metadata bullets: 2-space-indented, single-dash, immediately under title.
- Body fence: 4-space-indented ```` ```md ```` block. Belongs with the entry
  (cut/paste during a move includes it).
- `steps` is a nested checklist (4-space-indented under `- steps:`). Only
  IMPLEMENTING entries should carry it.
- For PLANNING and IMPLEMENTING entries, the body fence MUST contain a line
  matching `Plan file: <path>` (case-insensitive on `file`).

---

## Locked metadata fields

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

| Element | Regex | Notes |
|---|---|---|
| Column heading | `^## (BACKLOG\|PLANNING\|IMPLEMENTING\|COMPLETED)\s*$` | Multiline. |
| Entry heading | `^### (.+?)\s*$` | Capture group 1 = title. |
| Metadata bullet | `^  - (\w+):\s*(.*)$` | Capture: field name, raw value. |
| Steps line | `^  - steps:\s*$` | Followed by 6-space-indented `- [ ]` / `- [x]` lines. |
| Step item | `^      - \[( \|x)\] (.+?)\s*$` | Capture: state char, step text. |
| Body fence open | ` ^    ` ```md` | 4-space indent + ```` ```md ````. |
| Body fence close | ` ^    ` ``` ` | 4-space indent + ```` ``` ````. |
| Plan-file ref (in body) | `^Plan [Ff]ile:\s*(.+)$` | Multiline, body content only. |
