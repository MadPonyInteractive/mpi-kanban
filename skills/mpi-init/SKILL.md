---
name: mpi-init
description: Bootstrap or import into the kanban board from a freeform to-do file. Use when the user says "set up the kanban", "set up kanban based on this file", "initialize kanban", "import backlog", "convert this to kanban", "build the kanban from <file>", or hands over a markdown file of to-dos / bugs / ideas and asks to populate the board. Also use on first invocation in a fresh project where no `.claude/mpi-kanban/kanban.md` exists yet.
---

# mpi-init Skill

Turn a freeform to-do / backlog / ideas markdown file into properly-structured
BACKLOG and COMPLETED entries on `.claude/mpi-kanban/kanban.md`.

This is the on-ramp skill. It exists so a user can hand over any informal
to-do file ("backlog.md", "todo.md", "ideas.md", a section of a README) and
get a working kanban without the agent guessing the plugin internals.

<HARD-GATE>
Do NOT write to `kanban.md` until the user has confirmed the parsed entry list.
Show the planned entries first, ask for approval, THEN write.
</HARD-GATE>

## Inputs

- A path to a markdown source file (the user usually pastes it inline or
  references it). If the user says "this file" without naming one, ask which
  file. Common candidates: `backlog.md`, `todo.md`, `TODO.md`, `ideas.md`,
  `notes.md`, a `## Backlog` section inside `README.md` or `CLAUDE.md`.
- If the user gives no file at all but asks to "set up the kanban", create
  the empty board from the template and stop — there is nothing to import.

## Checklist

1. **Read source file.** Use `Read`. If it does not exist, ask the user for
   the right path. Do not guess.
2. **Read** `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops.md` once for the entry shape and procedures.
3. **Parse the source** per "Parsing rules" below into a list of entry
   candidates: `{title, tags, priority, body, done}`.
4. **Show the user the planned entries** — table or bullet list, grouped by
   target column (BACKLOG vs COMPLETED). Show inferred tag and priority.
5. **Ask for approval.** "Write these N entries to the kanban?" Wait.
6. **On approval:** call `ensureKanban()` (creates the file from template if
   missing, emits the one-time setup notice with the marketplace link).
7. **Write entries** — `createEntry("BACKLOG", e)` or `createEntry("COMPLETED", e)`
   per `done` flag. Preserve source order within each column (top of column =
   first entry from the source).
8. **Confirm** with a clickable kanban link: `[kanban.md](.claude/mpi-kanban/kanban.md)`
   and a one-line summary (`Imported 5 BACKLOG, 2 COMPLETED.`).

## Parsing rules

The source file is freeform. The skill must be permissive but never invent
content the source did not contain.

### Sections → tags

H2 headings in the source map to a default tag for the items underneath:

| Source heading (case-insensitive)       | Tag         |
|-----------------------------------------|-------------|
| `BUGS`, `BUG`, `ISSUES`                 | `[bug]`     |
| `FEATURES`, `FEATURE`                   | `[feature]`|
| `IDEAS`, `IDEA`                         | `[Idea]`    |
| `PLANS`, `PLAN`                         | `[PLAN]`    |
| `TASKS`, `TODO`, `TODOS`, `TO-DO`       | `[feature]` (default — bump to `[bug]` if the line says `bug:` / `fix:`) |
| `DECISIONS`, `NOTES`                    | `[Idea]`    |
| Anything else / no heading              | `[Idea]`    |

If a line begins with a `kind: title` prefix (e.g. `bug:`, `issue:`,
`feature:`, `refactor:`), that prefix overrides the section default and is
stripped from the title.

### Items → entries

Recognized item shapes (any of these counts as one entry):

- `[ ] text` or `[x] text`
- `- [ ] text` or `- [x] text`
- `* text` or `- text` (no checkbox — treat as not-done)
- A standalone non-empty line under a section that isn't itself a heading

`[x]` (lowercase or uppercase) → entry goes to `COMPLETED`. Otherwise → `BACKLOG`.

### Title

- Strip checkbox marker (`[ ]` / `[x]`) and any leading bullet (`-`, `*`).
- Strip `kind:` prefix if present (`bug:`, `issue:`, etc.) AFTER capturing it
  for the tag override.
- Trim trailing punctuation (`.`).
- Shorten to 2-6 words for the H3 title. Keep the full original line as the
  body so context isn't lost. Example:
  - Source: `[x] bug: Disabling plug-ins in global settings doesn't give a visual representation in the project page.`
  - Title: `Disabled plug-ins not shown`
  - Body: the full original sentence (without the `[x] bug:` prefix).
- If two entries collapse to the same title, append a numeric suffix
  (`Disabled plug-ins not shown (2)`).

### Priority

Default `medium`. Bump to `high` if the source line contains `urgent`,
`critical`, `p0`, `blocker`, `asap`. Drop to `low` if it contains `someday`,
`maybe`, `nice-to-have`, `low-pri`, `lowpri`.

Do NOT prompt the user per-entry for priority — that defeats the bulk-import
purpose. The user can edit priorities on the board afterward.

### defaultExpanded

Always `true` for imported entries.

### Body

The original source line, minus the checkbox/bullet/kind prefix, wrapped in
the standard ```` ```md ```` body fence. If the source had multi-line context
(an indented sub-bullet or a paragraph after the item), include it.

### Skip rules

- Skip empty lines.
- Skip H1 headings.
- Skip H2 headings (they are section markers, already consumed for the tag).
- Skip lines that are just commentary (no checkbox, not under a recognized
  section, look like prose). Heuristic: if the line is > 25 words and contains
  no `:` or imperative verb, treat as prose and skip with a note in the
  preview ("Skipped 1 prose line").

## Empty-board case

If the user invokes the skill without a source file (e.g. "set up the kanban
for this project"):

1. Call `ensureKanban()` to create the empty board from the template.
2. Confirm with the kanban link + extension marketplace link.
3. Do NOT prompt for further input. The user will populate the board via
   `mpi-brainstorm`, `mpi-write-plan`, or by re-invoking `mpi-init` with a
   source file.

## Hard rules

- Never write to `kanban.md` before the user approves the parsed entry list
  (except for the empty-board case, which writes only the template).
- Never invent metadata fields beyond the schema in `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops.md`.
- Never delete an existing entry. If the kanban already has entries with
  matching titles, surface the conflict and ask whether to skip, suffix, or
  abort.
- Preserve source order within each target column.
