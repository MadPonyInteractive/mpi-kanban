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
- Done card: move to `done` only after validation state exists and final
  completion is explicitly approved; set `maturity: "complete"`.
- Event logs: append meaningful `task.moved`, `task.updated`,
  `checklist.updated`, or `validation.updated` records to both the card's
  `tasks/<id>/events.jsonl` and the global `.agents/mpi-kanban/events.jsonl`.

Reject these common mistakes. They are NOT maturity values:

- `active`, `accepted`, `done` -> these are `status` values, not maturity.
- `implementing`, `implementation` -> Nimbalyst phrasing; the MPI value is
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

Required input:

```json
{
  "title": "Short task title",
  "description": "Optional card summary.",
  "column": "todo",
  "maturity": "idea",
  "status": "active",
  "position": "top",
  "actor": "codex"
}
```

`status` defaults to `active` when omitted. `position` is optional and may be
`top` or `bottom`; use `bottom` when importing an ordered source list.

Recipe:

1. Read `read.md` and call `ensureBoard()`.
2. Allocate an ID with `allocateTaskId(board)`.
3. Create `.agents/mpi-kanban/tasks/<id>/`.
4. Write `task.json` using `templates/task.json` as the field baseline.
5. Set `id`, `title`, `description`, `column`, `maturity`, `status`,
   timestamps, and links. Use relative links only.
   Reject the input if `maturity` is not one of the fixed enum values above or
   does not match `column`; normalize before writing rather than writing a red
   invalid card.
6. Add the ID to the target column array in `board.json`: prepend for
   `position: "top"` and append for `position: "bottom"`.
7. Append `task.created` to the global event log and task event log.

New ideas default to `todo`.

---

## `moveTask(id, toColumn, actor, reason)`

1. Read `board.json`.
2. Find the task ID in exactly one current column. If not found or duplicated,
   stop and report validation failure.
3. Remove the ID from the old column and insert it at the top of `toColumn`
   unless the caller provides a specific insertion index.
4. Read `tasks/<id>/task.json`.
5. Update `column`, `maturity`, and `updated_at` together. Column movement is
   also maturity reconciliation:
   - `toColumn: "todo"` -> keep the existing value when it is one of `idea`,
     `planned`, `research`, `needs-decision`, `blocked`, or `deferred`;
     otherwise set `planned`.
   - `toColumn: "doing"` -> keep existing `validating` only when validation
     state is already represented; otherwise set `in-progress`.
   - `toColumn: "done"` -> keep existing `rejected` when the card was
     explicitly closed without being built; otherwise set `complete`.
6. If the move implies agent reconciliation, set:

   ```json
   "attention": {
     "state": "required",
     "reason": "<reason>",
     "updated_at": "<timestamp>"
   }
   ```

7. Write `board.json` and `task.json`.
8. Append `task.moved` to both event logs.

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
- It must not be copied from `status`, legacy Markdown columns, Nimbalyst
  phases, tracker states, or freeform process labels.

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
   "checklist.md", "validation": "validation.md", "events": "events.jsonl",
   "handoffs": "handoffs/" })`.
7. If `planPath` points at the task workspace plan, derive checklist items from
   the plan:
   - phased plan: phase titles, stripped of `Phase N:` prefix;
   - compact plan: one `Implementation` item;
   - large adaptive plan without phases: lifecycle items from
     `plan-ops/derive.md`.
8. Preserve checked checklist items that still match derived item text. Rewrite
   stale derived items only when the plan changed or the checklist was missing.
9. Call `writeTask(id, { "maturity": "in-progress", "status": "active",
   "activeSessionTitle": sessionTitle, "links": { ...existingLinks,
   "plan": "plan.md", "checklist": "checklist.md", "validation":
   "validation.md", "events": "events.jsonl", "handoffs": "handoffs/" } },
   actor)`.
10. Append `checklist.updated` when checklist items are created or changed.

Do not set `maturity: "implementing"`; that is a Nimbalyst phase and maps to
MPI `in-progress`.

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
