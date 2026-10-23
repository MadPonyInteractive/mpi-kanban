# task-board-ops/mutate - create, move, and update task cards

Read this when a workflow needs to create a task, move it between columns,
write `task.json`, ensure linked files, append events, or update attention
state. For schema details, read `_schema.md`.

Recipes live in two files. This one: the preflight, `createTask`,
`attachPlan`, `setAttention`. `implement.md` in this directory: `moveTask`,
`writeTask`, `ensureLinkedFiles`, `beginImplementation`, `appendEvent`.

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

## `setAttention(id, state, reason, actor)`

1. Load the task.
2. For `required`, set `attention.state`, `reason`, and `updated_at`.
3. For `cleared`, either set `attention.state` to `cleared` with a reason or
   remove the `attention` object when no history is needed on the visible card.
4. Write the task and append `attention.required` or `attention.cleared` to
   both event logs.
