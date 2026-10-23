# mpi-continue - direct card update

Read from `mpi-continue` only when the user asks to move or set one card's
board state without asking to implement ("move MPI-42 to doing", "set MPI-42 to
validating", "mark the current card done"). Values come from the skill's
`## Card contract`, recipes from
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/implement.md`; never infer
legal values by grepping existing cards.

1. Locate exactly one JSON task by `MPI-*` id or unambiguous title
   (`findBoard`/`findTask` in
   `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md`). If
   `board.json` is absent, stop and report that direct card-state updates
   require the JSON task board.
2. Map the requested state:
   - `todo`, `to do`, `backlog`, `planned`, `reopen` -> `moveTask(id, "todo",
     actor, reason)` with coherent `maturity: "planned"` unless it is a raw
     idea.
   - `doing`, `in progress`, `implementing`, `implementation started` ->
     `beginImplementation(id, actor, planPath, sessionTitle)` when work is
     starting or the card is in `todo`; otherwise `moveTask(id, "doing", actor,
     reason)`, and `writeTask` only if a concise badge/status change is needed.
   - `validating`, `needs validation`, `ready for validation`, yellow card ->
     ensure `validation.md` and `events.jsonl` exist, write or update
     `validation.md` with a short validation-state note if none exists, append
     `validation.updated`, keep/move the card in `doing`, then call
     `writeTask(id, { "maturity": "validating", "status": "active" }, actor)`.
   - `done`, `complete`, `completed` -> move to `done` when `validation.md`
     records the evidence that closes it: the command that ran and passed, or
     the user's own confirmation. Evidence closes a card. Keep it in `doing`
     with `maturity: "validating"` and validation attention only when the
     evidence is missing, the check failed, or the card's verification
     genuinely needs human eyes that have not seen it yet - and say which of
     those it is.
3. Meaningful card updates append to both
   `.agents/mpi-kanban/tasks/<id>/events.jsonl` and
   `.agents/mpi-kanban/events.jsonl`.
4. Report one line - `MPI-42 -> doing / in-progress / active (validation.md)`:
   column, maturity, status, and the task file touched - and stop. Do not inspect
   unrelated tasks or sibling repositories.
