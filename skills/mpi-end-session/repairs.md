# mpi-end-session - card repairs

Read from `mpi-end-session` step 10 only when the card to close is in `todo`
while implementation work exists for it, or its `maturity` is not one of the
ten legal values for its column. Recipes: `beginImplementation` and `writeTask`
in `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/implement.md`.

## Skipped-Doing auto-correct

If the card is in `todo` but real implementation work exists for it - checked
items in `checklist.md`, OR changed files this session that belong to this
task's plan - the Doing phase was skipped. Before any `done` move, call
`beginImplementation(id, actor, planPath, sessionTitle)` to backfill
`todo -> doing`, set `maturity: "in-progress"`, and derive the checklist, then
continue. Print:
`Note: card "<id>" skipped the Doing phase; auto-corrected through doing before done.`

A card with no implementation work keeps moving `todo -> done` with no warning.
The lifecycle is always `To do -> Doing -> Done` for implemented work.

## Maturity auto-correct

Before any move, check `maturity` against the enum (`idea`, `planned`,
`research`, `needs-decision`, `blocked`, `deferred`, `in-progress`,
`validating`, `complete`, `rejected`) and its column. If the value is invalid
(e.g. `active`, `accepted`, `done`, `Validated`, `validated`, `validation`,
`spec`, `implementing`, `implementation`) or incoherent with the column, call
`writeTask(id, { "maturity": "<corrected>" }, actor)`:

- `todo` -> keep any valid todo value, otherwise `planned`;
- `doing` -> `in-progress`, or `validating` when validation is represented;
- `done` -> keep `rejected` when the work was closed without being built,
  otherwise `complete`.

Print: `Note: card "<id>" had invalid maturity "<old>"; corrected to "<new>".`
