---
name: mpi-init
description: MPI workflow pack - Initialize MPI kanban or import a freeform to-do / backlog / ideas markdown file into the board. Use ONLY when the user explicitly asks to "MPI init", "set up the kanban", "initialize kanban", "import backlog", "convert this file to kanban", "build the kanban from <file>", "$mpi-init", or hands over markdown to-dos. Do NOT use for a single new idea, creating a plan, or normal kanban mutation.
---

# mpi-init Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`
Turn a freeform to-do / backlog / ideas markdown file into properly-structured
BACKLOG and COMPLETED entries on `.claude/mpi-kanban/kanban.md`.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

This is the on-ramp skill. It exists so a user can hand over any informal
to-do file ("backlog.md", "todo.md", "ideas.md", a section of a README) and
get a working kanban without the agent guessing the plugin internals.

<HARD-GATE>
Only ask for confirmation when importing into an EXISTING `.claude/mpi-kanban/kanban.md`
(risk of overwriting user data) â€” show the parsed entry list, get approval, then write.

Fresh-board creation (no `kanban.md` yet) and empty-template bootstrap: write
directly, no confirmation. Same for the source-file relocation step (moving the
freeform to-do file into `.claude/mpi-kanban/`) â€” just do it.
</HARD-GATE>

## Inputs

- A path to a markdown source file (the user usually pastes it inline or
  references it). If the user says "this file" without naming one, ask which
  file. Common candidates: `backlog.md`, `todo.md`, `TODO.md`, `ideas.md`,
  `notes.md`, a `## Backlog` section inside `README.md` or `CLAUDE.md`.
- If the user gives no file at all but asks to "set up the kanban", create
  the empty board from the template and stop â€” there is nothing to import.

## Checklist

Lib pointers (read each only when its recipe is needed in the steps below):

- `<mpi-lib-root>/kanban-ops/_schema.md` â€” entry shape (read before
  building entries if you need a schema reminder)
- `<mpi-lib-root>/kanban-ops/find.md` â€” `ensureKanban`
- `<mpi-lib-root>/kanban-ops/mutate.md` â€” `createEntry`

Steps:

1. **Read source file.** Use `Read`. If it does not exist, ask the user for
   the right path. Do not guess.
2. **Parse the source** per "Parsing rules" below into a list of entry
   candidates: `{title, tags, priority, body, done}`.
3. **Check if `kanban.md` already exists.** Read `<mpi-lib-root>/kanban-ops/find.md` for
   `ensureKanban`.
   - **Does NOT exist (fresh board):** call `ensureKanban()` to create from
     template, then go to step 5. No preview, no approval.
   - **Exists (existing board):** show parsed entries (table or bullet list,
     grouped by target column, with inferred tag/priority) and ask: "Write
     these N entries to the existing kanban?" Wait for approval. On approval,
     continue to step 5.
4. (folded into step 3)
5. **Write entries** â€” read `<mpi-lib-root>/kanban-ops/mutate.md` for `createEntry`. Call
   `createEntry("BACKLOG", e)` or `createEntry("COMPLETED", e)` per `done`
   flag. Preserve source order within each column (top of column = first
   entry from the source).
6. **Confirm** with a clickable kanban link: `[kanban.md](.claude/mpi-kanban/kanban.md)`
   and a one-line summary (`Imported 5 BACKLOG, 2 COMPLETED.`).

## Parsing rules

The source file is freeform. The skill must be permissive but never invent
content the source did not contain.

### Sections â†’ tags

H2 headings in the source map to a default tag for the items underneath:

| Source heading (case-insensitive)       | Tag         |
|-----------------------------------------|-------------|
| `BUGS`, `BUG`, `ISSUES`                 | `[bug]`     |
| `FEATURES`, `FEATURE`                   | `[feature]`|
| `IDEAS`, `IDEA`                         | `[Idea]`    |
| `PLANS`, `PLAN`                         | `[PLAN]`    |
| `TASKS`, `TODO`, `TODOS`, `TO-DO`       | `[feature]` (default â€” bump to `[bug]` if the line says `bug:` / `fix:`) |
| `DECISIONS`, `NOTES`                    | `[Idea]`    |
| Anything else / no heading              | `[Idea]`    |

If a line begins with a `kind: title` prefix (e.g. `bug:`, `issue:`,
`feature:`, `refactor:`), that prefix overrides the section default and is
stripped from the title.

### Items â†’ entries

Recognized item shapes (any of these counts as one entry):

- `[ ] text` or `[x] text`
- `- [ ] text` or `- [x] text`
- `* text` or `- text` (no checkbox â€” treat as not-done)
- A standalone non-empty line under a section that isn't itself a heading

`[x]` (lowercase or uppercase) â†’ entry goes to `COMPLETED`. Otherwise â†’ `BACKLOG`.

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

Do NOT prompt the user per-entry for priority â€” that defeats the bulk-import
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
2. Confirm with the kanban link + Mpi-Kanban extension link.
3. Do NOT prompt for further input. The user will populate the board via
   `mpi-brainstorm`, `mpi-create-plan`, `mpi-create-large-plan`, or by re-invoking `mpi-init` with a
   source file.

## Hard rules

- When importing into an EXISTING `kanban.md`, get user approval on the parsed
  entry list before writing. Fresh-board creation, empty-template bootstrap,
  and source-file relocation: write directly without asking.
- Never invent metadata fields beyond the schema in `<mpi-lib-root>/kanban-ops/_schema.md`.
- Never delete an existing entry. If the kanban already has entries with
  matching titles, surface the conflict and ask whether to skip, suffix, or
  abort.
- Preserve source order within each target column.



