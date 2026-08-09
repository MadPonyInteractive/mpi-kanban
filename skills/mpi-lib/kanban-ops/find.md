# kanban-ops/find â€” locate the board and its entries

Read this only for legacy Markdown board compatibility and migration. New task
board work should use `task-board-ops/_schema.md` and
`.agents/mpi-kanban/board.json`. For legacy schema/regexes see `_schema.md`.
For legacy mutations see `mutate.md`.

References in this file resolve relative to `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib`, the installed
root of the sibling `mpi-lib` support skill.

---

## `findKanban()` legacy helper

1. Resolve path: `<project-root>/.agents/mpi-kanban/kanban.md`.
2. Try `Read`.
3. If found â†’ return path + contents.
4. If missing â†’ return `null`. Caller decides: bootstrap (`ensureKanban`) or
   surface a setup notice.

---

## `ensureKanban()` legacy helper

1. Call `findKanban()`.
2. If found â†’ return path.
3. If missing:
   a. `Read` `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/kanban.md`.
   b. `Write` contents to `<project-root>/.agents/mpi-kanban/kanban.md`. The
      Write tool will create the `.agents/mpi-kanban/` directory.
   c. Emit one-time setup notice in chat:
      - Clickable link: `[kanban.md](.agents/mpi-kanban/kanban.md)`
      - Extension link: `https://github.com/MadPonyInteractive/mpi-kanban-vscode`
      - One-line note: "Install the extension to see this file as an interactive board."
4. Return path.

Do not call `ensureKanban()` once `.agents/mpi-kanban/board.json` exists; avoid
creating a competing live Markdown board.

If a found board has the legacy four-column shape without `## VALIDATING`,
return the path without silently rewriting it. Skills that need to mutate board
lifecycle state must ask the user before inserting `## VALIDATING` between
`## IMPLEMENTING` and `## COMPLETED`.

**Skip `ensureKanban` for `mpi-brief-rule`** â€” that skill is board-independent.

---

## `kanbanLink()`

Return the clickable markdown link to print in chat whenever referencing the board:

```
[kanban.md](.agents/mpi-kanban/kanban.md)
```

---

## `listEntries(column)`

1. Read the file.
2. Locate the H2 heading matching `column` (one of the five).
3. Collect every `### ` block until the next H2 (or end of file).
4. For each block: parse title, metadata bullets, body fence (if present),
   steps (if present).
5. Return list of entry objects.

---

## `findEntry(predicate)`

1. For each column in order: `BACKLOG`, `PLANNING`, `IMPLEMENTING`,
   `VALIDATING`, `COMPLETED`.
2. Run `listEntries(column)`.
3. Return first entry matching `predicate`, plus its column.
4. None match â†’ return `null`.

Common predicates:

- `entry.title === <title>` â€” `mpi-create-plan` / `mpi-create-large-plan`
  matching an existing BACKLOG entry by title.
- Body contains `Plan file: <path>` â€” `mpi-continue`, `mpi-end-session`,
  `mpi-handoff`, and `mpi-cleanup` locating the entry tied to the active plan.

