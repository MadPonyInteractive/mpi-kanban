# task-board-ops/implement - move a card and write its state

The recipes the implementation path calls: `moveTask`, `writeTask`,
`ensureLinkedFiles`, `beginImplementation`, `appendEvent`. Legal values and
the card-write preflight are in `mutate.md` (and inline in `mpi-continue`'s
`## Card contract`); schema detail is in `_schema.md`.

---

## `moveTask(id, toColumn, actor, reason)`

One command, for the same reason - a move is four writes too, and a half-done
one leaves `board.json` saying `doing` while the card says `todo`:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/task_ops.py" move MPI-42 --to doing --reason "Implementation started." --root <project-root>
```

It moves the id between columns in `board.json`, updates `column`, `maturity`
and `updated_at` in `task.json`, sets `status` to `done` on a move into `done`,
appends `task.moved` to both event logs, and validates before it exits.

Maturity is reconciled from the destination column unless `--maturity` says
otherwise: a value that is legal for the destination survives the move, anything
else becomes that column's default (`todo` -> `planned`, `doing` ->
`in-progress`, `done` -> `complete`). Use `--maturity rejected` for a card
closed without being built, and `--maturity validating` once validation state
exists.

The move is refused before anything is written when the destination's linked
file is missing - `checklist.md` for `doing`, `validation.md` for `done`. Write
the file, then repeat the command. A card in `done` is never silently reopened
by this: moving it back is a deliberate `--to doing` with a reason.

If the move implies agent reconciliation, follow it with `writeTask` to set:

```json
"attention": {
  "state": "required",
  "reason": "<reason>",
  "updated_at": "<timestamp>"
}
```

Typical reconciliation moves:

- `done -> doing`
- `doing -> todo`
- any move requested by a user that conflicts with active coordination state

---

## `writeTask(id, patch, actor)`

Use structured JSON updates rather than string manipulation.

Allowed direct task-card updates:

- `title`
- `description`
- `maturity`
- `status`
- `attention`
- `activeSessionTitle`
- `links`

Always update `updated_at` and append `task.updated` to both the task event log
and the global event log.

If `patch.maturity` is present, validate it before writing:

- It must be exactly `idea`, `planned`, `research`, `needs-decision`,
  `blocked`, `deferred`, `in-progress`, `validating`, `complete`, or
  `rejected`.
- It must match the task's current `column`.
- It must not be copied from `status`, tracker states, or freeform process
  labels.

If the caller asks for `maturity: "Validated"`, `maturity: "spec"`, or any
other non-enum value, stop and map it to the coherent MPI value or ask for
direction before writing.

Do not embed long plans, handoffs, validation notes, research, or file lists in
`task.json`; use linked workspace files.

---

## `ensureLinkedFiles(id, links)`

Create linked files only when the workflow needs them.

Default empty content:

- `brief.md`: `# <id> Brief`
- `plan.md`: `# <id> Plan`
- `checklist.md`: `# <id> Checklist`
- `validation.md`: `# <id> Validation`
- `files.json`: `{"schema":"mpi-kanban/task-files/v1","files":[]}`
- `events.jsonl`: empty file

Always create `handoffs/` and `research/` as directories when their links are
used. Never delete unknown files from a task folder.

`files.json` exists in two shapes in the wild: the object form above, and a
bare `[]` array, which is what the VS Code extension writes when it migrates a
legacy Markdown board. Readers must accept both - a list is the file list, an
object carries it under `files`. Write the object form. Entries are repo-
relative paths or globs, for example `["src/api/**", "docs/install.md"]`.

---

## `beginImplementation(id, actor, planPath, sessionTitle)`

Use this recipe when a workflow starts implementation for a JSON task card. It
prevents partial state such as a card in `doing` with `maturity: "planned"` or
missing checklist items.

Lifecycle contract: every card with real implementation work must pass through
`doing`. The canonical lifecycle is `To do -> Doing -> Done`, never
`To do -> Done`. Any workflow that is about to edit files for a `todo` card must
call `beginImplementation` first so the card enters `doing` with a derived
checklist. `mpi-end-session` enforces this on close-out: a `todo` card carrying
implementation work is auto-corrected through `doing` (with a warning) rather
than moved straight to `done`.

1. Read `read.md`, `_schema.md`, and `plan-ops/derive.md`.
2. Load the task with `loadTask(id)` and read `board.json`.
3. If the task is in `todo`, call `moveTask(id, "doing", actor,
   "Implementation started.")`.
4. If the task is already in `doing`, leave board order alone.
5. Stop and report drift if the task is in `done`; do not silently reopen a
   completed card.
6. Call `ensureLinkedFiles(id, { "plan": "plan.md", "checklist":
   "checklist.md", "validation": "validation.md", "files": "files.json",
   "events": "events.jsonl", "handoffs": "handoffs/" })`.
7. If `planPath` points at the task workspace plan, derive checklist items from
   the plan:
   - phased plan: phase titles, stripped of `Phase N:` prefix;
   - compact plan: one `Implementation` item;
   - large adaptive plan without phases: lifecycle items from
     `plan-ops/derive.md`.
8. Preserve checked checklist items that still match derived item text. Rewrite
   stale derived items only when the plan changed or the checklist was missing.
9. Write ownership into `files.json`. This is the transition where ownership
   becomes knowable: at creation it is a guess, and a card that never records
   it can never be dispatched.
   - Derive the list from the first source that yields paths: `Ownership:`
     lines in the plan; the files, directories and globs the plan names; the
     file whose edit triggered this transition.
   - Write the derived list to `.agents/mpi-kanban/tasks/<id>/files.json` in
     the object form, and keep `"files": "files.json"` in `links`.
   - Say it in one line - `files.json: <n> paths from <source>` - not as a
     file list. Never write ownership silently.
   - When the plan names nothing and no triggering file is known, leave the
     list empty and say so. An empty list means "not dispatchable", which is
     honest; an invented one sends a worker at files nobody chose.
   - Merge with an existing non-empty list rather than replacing it, and do not
     drop a path the card already owned.
10. Call `writeTask(id, { "maturity": "in-progress", "status": "active",
   "activeSessionTitle": sessionTitle, "links": { ...existingLinks,
   "plan": "plan.md", "checklist": "checklist.md", "validation":
   "validation.md", "files": "files.json", "events": "events.jsonl",
   "handoffs": "handoffs/" } }, actor)`.
11. Append `checklist.updated` when checklist items are created or changed.

Do not set `maturity: "implementing"`; the MPI value is `in-progress`.

---

## `appendEvent(scope, event)`

Scopes:

- global: `.agents/mpi-kanban/events.jsonl`
- task: `.agents/mpi-kanban/tasks/<id>/events.jsonl`

Event rules:

1. One compact JSON object per line.
2. Include `schema: "mpi-kanban/event/v1"`, `type`, `at`, and `actor`.
3. Include `id` for task-scoped events.
4. For normal task-card changes, append matching records to both the task log
   and global log so local card history and board history stay coherent.
5. Append only. Do not rewrite event history except during an explicit repair
   approved by the user.
