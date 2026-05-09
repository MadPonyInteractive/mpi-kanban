# kanban-ops/find — locate the board and its entries

Read this when you need to find the board, ensure it exists, list entries, or
find a specific entry. For schema/regexes see `_schema.md`. For mutations see
`mutate.md`.

---

## `findKanban()`

1. Resolve path: `<project-root>/.claude/mpi-kanban/kanban.md`.
2. Try `Read`.
3. If found → return path + contents.
4. If missing → return `null`. Caller decides: bootstrap (`ensureKanban`) or
   surface a setup notice.

---

## `ensureKanban()`

1. Call `findKanban()`.
2. If found → return path.
3. If missing:
   a. `Read` `${CLAUDE_PLUGIN_ROOT}/templates/kanban.md`.
   b. `Write` contents to `<project-root>/.claude/mpi-kanban/kanban.md`. The
      Write tool will create the `.claude/mpi-kanban/` directory.
   c. Emit one-time setup notice in chat:
      - Clickable link: `[kanban.md](.claude/mpi-kanban/kanban.md)`
      - Marketplace link: `https://marketplace.visualstudio.com/items?itemName=holooooo.markdown-kanban`
      - One-line note: "Install the extension to see this file as an interactive board."
4. Return path.

**Skip `ensureKanban` for `mpi-brief-rule`** — that skill is board-independent.

---

## `kanbanLink()`

Return the clickable markdown link to print in chat whenever referencing the board:

```
[kanban.md](.claude/mpi-kanban/kanban.md)
```

---

## `listEntries(column)`

1. Read the file.
2. Locate the H2 heading matching `column` (one of the four).
3. Collect every `### ` block until the next H2 (or end of file).
4. For each block: parse title, metadata bullets, body fence (if present),
   steps (if present).
5. Return list of entry objects.

---

## `findEntry(predicate)`

1. For each column in order: `BACKLOG`, `PLANNING`, `IMPLEMENTING`, `COMPLETED`.
2. Run `listEntries(column)`.
3. Return first entry matching `predicate`, plus its column.
4. None match → return `null`.

Common predicates:

- `entry.title === <title>` — `mpi-write-plan` matching an existing BACKLOG
  entry by title.
- Body contains `Plan file: <path>` — `mpi-execute-next`, `mpi-end-session`,
  `mpi-handoff` locating the entry tied to the active plan.
