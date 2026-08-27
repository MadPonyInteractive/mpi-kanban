# task-board-ops/mutate - create, move, and update task cards

Read this when a workflow needs to create a task, move it between columns,
write `task.json`, ensure linked files, append events, or update attention
state. For schema details, read `_schema.md`.

---

## Card-write preflight (read before any write)

Before writing `column`, `maturity`, `status`, `attention`, or any linked
task-board state, read `_schema.md` in this directory. Do not infer legal
values from existing cards, old Markdown boards, tracker phases, or nearby
examples. Existing cards can be stale or invalid.

Use this contract for every card write:

`maturity` accepts ONLY: `idea`, `planned`, `research`, `needs-decision`,
`blocked`, `deferred`, `in-progress`, `validating`, `complete`, `rejected`.
Do not guess, invent, or copy another field's value into it.

Column coherence is mandatory:

- `todo` -> `idea`, `planned`, `research`, `needs-decision`, `blocked`, or `deferred`
- `doing` -> `in-progress` or `validating`
- `done` -> `complete` or `rejected`

Lifecycle ordering is mandatory:

- Pickup/start implementation: move `todo -> doing`, set
  `maturity: "in-progress"`, set `status: "active"`, and create/derive linked
  checklist state before editing implementation files. Never implement a
  `todo` card in place.
- Needs validation/yellow card: keep the card in `doing`, write or update
  `validation.md` first, then set `maturity: "validating"`. Do not move to
  `done` just because validation is needed.
- Done card: move to `done` once `validation.md` records evidence that the work
  holds - the command that ran and passed, or the user's own confirmation - and
  set `maturity: "complete"`. Evidence closes a card; a passing check is not
  worth a round trip. Ask first only when the card's verification genuinely
  needs human eyes (a UI/UX surface, a judgement call) and that has not
  happened yet. Never close a card on an unrun or failed check.
- Event logs: append meaningful `task.moved`, `task.updated`,
  `checklist.updated`, or `validation.updated` records to both the card's
  `tasks/<id>/events.jsonl` and the global `.agents/mpi-kanban/events.jsonl`.

Reject these common mistakes. They are NOT maturity values:

- `active`, `accepted`, `done` -> these are `status` values, not maturity.
- `implementing`, `implementation` -> tracker phrasing; the MPI value is
  `in-progress`.
- `validated`, `Validated`, `validation` -> validation state is represented by
  `maturity: "validating"` while the card is in `doing`, then
  `maturity: "complete"` when it moves to `done`.
- `spec`, `scoped`, `designed`, `review`, or other process labels -> keep that
  detail in `brief.md`, `plan.md`, `validation.md`, or `description`; do not
  put it in `maturity`.

Any other `maturity` value renders as a red invalid card in the VS Code board.
A `doing` card that should show needs-validation/yellow state uses
`maturity: "validating"` after validation state exists, never
`implementation`, `idea`, or `Validated`.

Before every write, derive the maturity from the destination column unless the
workflow has an explicitly allowed value:

| Column | Allowed `maturity` | Default when unsure |
|---|---|---|
| `todo` | `idea`, `planned`, `research`, `needs-decision`, `blocked`, `deferred` | `planned` for planned/reopened work; `idea` for raw backlog ideas; pick the more specific value when the state is known |
| `doing` | `in-progress`, `validating` | `in-progress`; use `validating` only after validation state exists |
| `done` | `complete`, `rejected` | `complete`; use `rejected` only for explicitly closed/abandoned work |

If an existing card already has an invalid or incoherent maturity, correct it
with the same task-board write that changes or confirms its column. Do not
preserve invalid maturity for history; preserve the old label in an event,
brief, plan note, or validation note if it matters.

---

## `createTask(input)`

One command. Never assemble a card out of separate writes:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/task_ops.py" create --title "Short task title" --description "Optional card summary." --column todo --maturity idea --root <project-root>
```

It claims the id with an atomic `mkdir`, writes `task.json` with mode `'x'` from
`templates/task.json`, inserts the id into the `board.json` column, bumps
`next_id`, appends `task.created` to both event logs, takes its timestamps from
the clock, and runs `validate_board()` before it exits. If any step fails the
task folder is removed, so a create lands whole or leaves nothing.

Options: `--maturity` defaults to the column's default (`todo` -> `planned`,
`doing` -> `in-progress`, `done` -> `complete`) and is rejected when it does not
match the column. `--status` defaults to `active`. `--position` defaults to
`top`; use `bottom` when importing an ordered source list. A card created
straight into `doing` or `done` gets that column's required linked file seeded.

Why this is a command and not a recipe: writing `task.json` without inserting
the id into `board.json` leaves a card that owns an id and is invisible to the
VS Code extension, to `board_server.py`, and to everything else that reads the
board - and nothing errors, because `next_id` has already moved. That happened
twice in one hour on 2026-08-27, in two different repos, to two different
agents working from the step list this section used to carry.

Repair an existing orphan with:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/validate_board.py" <project-root> --fix
```

New ideas default to `todo`.

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

## `attachPlan(id, planMarkdown, actor)`

Use this recipe from planning workflows.

1. Load the task with `loadTask(id)`.
2. Call `ensureLinkedFiles(id, { "plan": "plan.md", "events": "events.jsonl" })`.
3. Write the plan body to `.agents/mpi-kanban/tasks/<id>/plan.md`.
4. Call `writeTask(id, { "maturity": "planned", "status": "active", "links": { ...existingLinks, "plan": "plan.md" } }, actor)`.
5. The `writeTask` call updates `updated_at` and appends the `task.updated`
   event.

Do not store plan bodies or long plan summaries in `task.json`.

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
   - Report what was written and which source it came from. Never write
     ownership silently.
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

---

## `setAttention(id, state, reason, actor)`

1. Load the task.
2. For `required`, set `attention.state`, `reason`, and `updated_at`.
3. For `cleared`, either set `attention.state` to `cleared` with a reason or
   remove the `attention` object when no history is needed on the visible card.
4. Write the task and append `attention.required` or `attention.cleared` to
   both event logs.
