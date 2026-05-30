---
name: mpi-init
description: MPI workflow pack - Initialize the MPI JSON task board or import a freeform to-do / backlog / ideas markdown file into JSON task cards. Use ONLY when the user explicitly asks to "MPI init", "set up the kanban", "initialize kanban", "import backlog", "convert this file to kanban", "build the kanban from <file>", "$mpi-init", or hands over markdown to-dos. Do NOT use for a single new idea, creating a plan, or normal board mutation.
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

Turn a freeform to-do / backlog / ideas markdown file into properly structured
tasks on `.agents/mpi-kanban/board.json` with task workspaces under
`.agents/mpi-kanban/tasks/<id>/`.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

This is the on-ramp skill. It exists so a user can hand over any informal
to-do file ("backlog.md", "todo.md", "ideas.md", a section of a README) and
get a working JSON task board without the agent guessing the plugin internals.

<HARD-GATE>
Only ask for confirmation when importing into an EXISTING
`.agents/mpi-kanban/board.json` (risk of appending unwanted tasks): show the
parsed task list, get approval, then write.

Fresh-board creation and empty-template bootstrap: write directly, no
confirmation. Same for the source-file relocation step (moving the freeform
to-do file into `.agents/mpi-kanban/`): just do it.
</HARD-GATE>

## Inputs

- A path to a markdown source file (the user usually pastes it inline or
  references it). If the user says "this file" without naming one, ask which
  file. Common candidates: `backlog.md`, `todo.md`, `TODO.md`, `ideas.md`,
  `notes.md`, a `## Backlog` section inside `README.md` or `CLAUDE.md`.
- If the user gives no file at all but asks to "set up the kanban", create
  the empty JSON board from the template and stop. There is nothing to import.

## Checklist

Lib pointers, read each only when its recipe is needed in the steps below:

- `<mpi-lib-root>/task-board-ops/_schema.md` - JSON board and task-card shape.
- `<mpi-lib-root>/task-board-ops/read.md` - `findBoard`, `ensureBoard`.
- `<mpi-lib-root>/task-board-ops/mutate.md` - `createTask`.
- `<mpi-lib-root>/task-board-ops/migrate.md` - only when the user explicitly
  asks to migrate an existing legacy Markdown board.

Steps:

1. **Read source file.** Use `Read`. If it does not exist, ask the user for
   the right path. Do not guess.
2. **Parse the source** per "Parsing rules" below into a list of task
   candidates: `{title, description, done}`.
3. **Check if `board.json` already exists.** Read
   `<mpi-lib-root>/task-board-ops/read.md` for `findBoard` and `ensureBoard`.
   - **Does NOT exist (fresh board):** call `ensureBoard()` to create
     `.agents/mpi-kanban/board.json`, `.agents/mpi-kanban/events.jsonl`, and
     `.agents/mpi-kanban/tasks/`, then go to step 5. No preview, no approval.
   - **Exists (existing board):** show parsed tasks (table or bullet list,
     grouped by target column, with title and short description) and ask:
     "Write these N tasks to the existing JSON task board?" Wait for approval.
     On approval, continue to step 5.
4. (folded into step 3)
5. **Write tasks**: read `<mpi-lib-root>/task-board-ops/mutate.md` for
   `createTask`. For each parsed candidate in source order, call
   `createTask(input)` with:
   - `column: "todo"`, `maturity: "idea"`, `status: "active"` when `done`
     is false.
   - `column: "done"`, `maturity: "complete"`, `status: "accepted"` when
     `done` is true.
   - `position: "bottom"` so source order is preserved within each target
     column.
   The recipe allocates `MPI-*` IDs; never accept task IDs from the source text.
6. **Confirm** with a clickable board link:
   `[board.json](.agents/mpi-kanban/board.json)` and a one-line summary such
   as `Imported 5 To do, 2 Done.`

If legacy `.agents/mpi-kanban/kanban.md` or `.claude/mpi-kanban/kanban.md`
exists, tell the user it remains available as a legacy migration source or
snapshot. Do not write it as the live board.

## Parsing rules

The source file is freeform. The skill must be permissive but never invent
content the source did not contain.

### Sections to task kind hints

H2 headings in the source provide a hint for the task description:

| Source heading (case-insensitive)       | Kind hint   |
|-----------------------------------------|-------------|
| `BUGS`, `BUG`, `ISSUES`                 | bug         |
| `FEATURES`, `FEATURE`                   | feature     |
| `IDEAS`, `IDEA`                         | idea        |
| `PLANS`, `PLAN`                         | plan        |
| `TASKS`, `TODO`, `TODOS`, `TO-DO`       | task        |
| `DECISIONS`, `NOTES`                    | idea        |
| Anything else / no heading              | idea        |

If a line begins with a `kind: title` prefix (e.g. `bug:`, `issue:`,
`feature:`, `refactor:`), that prefix overrides the section hint and is
stripped from the title.

### Items to tasks

Recognized item shapes (any of these counts as one task):

- `[ ] text` or `[x] text`
- `- [ ] text` or `- [x] text`
- `* text` or `- text` (no checkbox: treat as not-done)
- A standalone non-empty line under a section that isn't itself a heading

`[x]` (lowercase or uppercase) maps to column `done`. Otherwise map to
column `todo`.

### Title

- Strip checkbox marker (`[ ]` / `[x]`) and any leading bullet (`-`, `*`).
- Strip `kind:` prefix if present (`bug:`, `issue:`, etc.) AFTER capturing it
  for the kind hint.
- Trim trailing punctuation (`.`).
- Shorten to 2-6 words for the task title. Keep the full original line as the
  description so context is not lost. Example:
  - Source: `[x] bug: Disabling plug-ins in global settings doesn't give a visual representation in the project page.`
  - Title: `Disabled plug-ins not shown`
  - Description: `bug: Disabling plug-ins in global settings doesn't give a visual representation in the project page.`
- If two tasks collapse to the same title, append a numeric suffix
  (`Disabled plug-ins not shown (2)`).

### Description

Use the original source line, minus the checkbox/bullet prefix. Include a
short kind hint only when it came from the source heading or prefix. If the
source had multi-line context (an indented sub-bullet or a paragraph after the
item), include a concise summary rather than embedding a long note in
`task.json`; longer context belongs in the task workspace after planning.

### Priority and metadata

The JSON task-card schema does not have priority, tag, workload, or
default-expanded fields. Do not invent them. If the source line contains
words like `urgent`, `critical`, `p0`, `blocker`, or `asap`, keep that wording
in the short description so a human can still see it on the card.

### Skip rules

- Skip empty lines.
- Skip H1 headings.
- Skip H2 headings (they are section markers, already consumed for kind hints).
- Skip lines that are just commentary (no checkbox, not under a recognized
  section, look like prose). Heuristic: if the line is > 25 words and contains
  no `:` or imperative verb, treat as prose and skip with a note in the
  preview ("Skipped 1 prose line").

## Empty-board case

If the user invokes the skill without a source file (e.g. "set up the kanban
for this project"):

1. Call `ensureBoard()` to create the empty JSON board from the template.
2. Confirm with the board link + Mpi-Kanban extension link.
3. Do NOT prompt for further input. The user will populate the board via
   `mpi-brainstorm`, `mpi-create-plan`, `mpi-create-large-plan`, or by
   re-invoking `mpi-init` with a source file.

## Hard rules

- When importing into an EXISTING `board.json`, get user approval on the
  parsed task list before writing. Fresh-board creation, empty-template
  bootstrap, and source-file relocation: write directly without asking.
- Never invent metadata fields beyond the schema in
  `<mpi-lib-root>/task-board-ops/_schema.md`.
- Never delete an existing task. If the board already has tasks with matching
  titles, surface the conflict and ask whether to skip, suffix, or abort.
- Preserve source order within each target column.
- Legacy `kanban.md` files are migration inputs or snapshots after
  `board.json` exists. Do not update them as the primary live board.
