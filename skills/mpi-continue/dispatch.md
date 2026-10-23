# mpi-continue - dispatch

Read from `mpi-continue` only when one of these fires:

- the active card's next eligible unit is a `## Parallel Batch`;
- the user asks for the whole board ("run the ready cards", "dispatch ready
  cards", "work the board", "run everything that's ready");
- two or more board cards are ready (`## Autonomous dispatch` step 1).

`mpi-continue` never spawns implementation workers itself;
`mpi-execute-parallel` does, and it is the only worker-spawning implementation
path.

## Parallel batch routing

A card whose `plan.md` carries phases and `## Parallel Batch` sections is an
**umbrella card**: one card holding work that splits. There is no `parent`
field and no umbrella flag - the plan's shape makes it one, deliberately,
because the board contract forbids new card fields.

When the active card's next eligible unit is a valid `## Parallel Batch` -
disjoint `Ownership:`, a per-task `**Verify:**`, no intra-batch dependency, no
fresh write claim on the owned files - route it to `mpi-execute-parallel` and
announce the split. Do not ask first. The batch was written into the plan
deliberately, and the plan was already approved; asking again is the round trip
this pack exists to remove.

```text
Next unit is a parallel batch: "<batch title>". Running its N tasks in parallel.
<one line per task: id or title - owned paths>
```

Fall back to a sequential continue brief only when the batch fails an
eligibility gate - and then say which gate - or when the user asks for
sequential.

## Board dispatch routing

When the user asks for the whole board rather than one card, that is a board
batch, not a continue. Route it to `mpi-execute-parallel` and use its
`## Board batch source` section; do not implement the cards here one after
another, and do not spawn workers here.

Requests naming one card ("continue MPI-42", "what is MPI-42") stay in
`mpi-continue` (or `mpi-show` for the lookup).

Being asked is not the only trigger. `## Autonomous dispatch` below runs the
same routing on every start, without being asked; this section only covers the
case where the user says it out loud.

## Autonomous dispatch

Evaluated on every start, before the Continue Brief. Do not wait to be asked -
the user never types "dispatch", and the work still splits. It is read-only,
costs a few reads, and needs no permission. Skip it entirely when `board.json`
is absent or fewer than two cards are ready.

1. **Collect the ready cards.** A card is ready when it is in `todo` with
   `maturity: "planned"`, has a `plan.md`, and carries no
   `attention.state: "required"`. The active card belongs to
   `## Parallel batch routing`, not here, unless its own next unit is not a
   batch and it is otherwise ready.
2. **Grep each card's footprint.** Do not trust `files.json` - most cards
   predate ownership being written at `todo -> doing`, so it is empty or stale.
   Read each card's `plan.md` and resolve every path, glob and module it names
   against the repo with a bounded search. `files.json` is a hint the grep
   confirms, never a substitute for it.
3. **Build the conflict graph.** Two cards conflict when their footprints share
   a file, when one footprint sits inside a directory the other owns, or when
   either intersects a fresh active write claim in `state/index.json`. A card
   whose footprint came back empty conflicts with everything: it cannot be
   proven disjoint, so it cannot be dispatched.
4. **Select the largest mutually non-conflicting set, capped at 4 workers.** On
   a tie, prefer the smaller footprints - those are the ones the grep pinned
   down most precisely.
5. **Report the whole evaluation before anything runs**, never dropping a card
   silently: every card the board offered appears, every exclusion with its
   reason, one line each.

```text
Dispatch: 3 of 7 ready cards are disjoint. Running them in parallel.

Selected:
- MPI-31 - src/api/** (grep: 12 files)
- MPI-34 - docs/install.md (grep: 1 file)
- MPI-37 - tests/e2e/** (grep: 4 files)
Excluded:
- MPI-30 - maturity is `research`, not `planned`
- MPI-33 - no plan.md; needs planning first
- MPI-35 - footprint overlaps MPI-31 on src/api/routes.ts
- MPI-38 - plan names no files; footprint not derivable
```

6. **Hand the selected set to `mpi-execute-parallel`** through its
   `## Board batch source`, which re-runs the board validator and owns worker
   spawning. Announce the split; do not ask permission - each selected card
   carries a `plan.md`, and that plan is the approval that already happened.
7. Fewer than two cards survive -> say nothing, continue with the normal
   single-card brief. "Nothing splits" is the common case; reporting it every
   session is noise.

This evaluation is **read-only**: cards, plans and claims in, nothing written -
not the board, not `files.json`, not a claim. A dispatcher that cannot write
cannot clobber a worker.

When `agents/dispatcher.md` ships with the installed plugin, delegate steps 1-4
to it with `subagent_type: "dispatcher"` - same method, in a subagent that
cannot write, keeping the card and plan reads out of this session's context.
**Running `mpi-continue` authorizes that dispatch**, exactly as invoking
`mpi-end-session` authorizes its commit; a standing "do not call agents unless
the user asked" instruction is a default against *unprompted* dispatch, not a
veto here. Say so rather than quietly deferring - that reflex is why this agent
went months without running. Absent, or deliberately skipped: do the evaluation
inline and say which.

### `isolation: "worktree"` is not the isolation mechanism here

Do not run these workers in git worktrees, and do not "fix" this in a later
session. A worktree branches from the **default branch, not the parent
session's HEAD**, and MPI commits only at close-out - so a worktree worker
cannot see the session's uncommitted work, and will re-implement or contradict
it. Isolation here is the disjoint ownership you declare: workers share one
session id, so `guard-claim` cannot catch two of them writing one file.
