# mpi-continue - dispatch

Read from `mpi-continue` only when one of these fires:

- the active card's next eligible unit is a `## Parallel Batch`;
- the user asks for the whole board ("run the ready cards", "dispatch ready
  cards", "work the board", "run everything that's ready").

`mpi-continue` never spawns implementation workers itself;
`mpi-execute-parallel` does, and it is the only worker-spawning implementation
path.

## Parallel batch routing

A card whose `plan.md` carries phases and `## Parallel Batch` sections is an
**umbrella card**: one card holding work that splits. There is no `parent`
field and no umbrella flag - the plan's shape makes it one, deliberately,
because the board contract forbids new card fields.

When the active card's next eligible unit is a valid `## Parallel Batch` -
disjoint `Ownership:`, a per-task `**Verify:**` and `Model:`, no intra-batch
dependency, no fresh write claim on the owned files - route it to
`mpi-execute-parallel` and
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

## Other ready cards: report, never spawn

Ready cards the user did not name are never dispatched unasked. `continue
MPI-45` with two other planned cards on the board once started up to four
workers on cards nobody named, before the brief - a plan written weeks ago is
not today's go-ahead (MPI-49). They get one line on the brief's Heads-up, from
the board and the cards' own folders - no plan reads, no footprint grep:

```text
Ready cards: MPI-31, MPI-34 (2). Say "run the ready cards" to check which can run in parallel.
```

Spawning needs the user's words (`## Board dispatch routing`) or a batch in
the named card's own plan (`## Parallel batch routing`). The footprint check,
the conflict graph and the `dispatcher` agent live in `mpi-execute-parallel`'s
`## Board batch source`, and run only from there.

### `isolation: "worktree"` is not the isolation mechanism here

Do not run these workers in git worktrees, and do not "fix" this in a later
session. A worktree branches from the **default branch, not the parent
session's HEAD**, and MPI commits only at close-out - so a worktree worker
cannot see the session's uncommitted work, and will re-implement or contradict
it. Isolation here is the disjoint ownership you declare: workers share one
session id, so `guard-claim` cannot catch two of them writing one file.
