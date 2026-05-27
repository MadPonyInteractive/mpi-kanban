---
name: mpi-end-session
description: MPI workflow pack - MPI end session workflow. Close session, sync rules/docs, commit touched files, move implemented work to VALIDATING, and close explicitly validated work. Use when user says "MPI end session", "end session", "wrap up", "commit and close", "$mpi-end-session", or "/mpi-end-session".
---

# mpi-end-session Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`
Wrap up the current session cleanly: sync docs/rules with code changes, commit
touched files, persist any new memory, and close out the active kanban entry.

This skill is the LAST step in the brainstorm Ã¢â€ â€™ create-plan/create-large-plan
Ã¢â€ â€™ continue Ã¢â€ â€™ handoff/continue Ã¢â€ â€™ end-session loop. Run it when the user signals
the session is done.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Process

### 0. Read coordination state

Read these references when `.agents/mpi-kanban/state/index.json` exists:

- `<mpi-lib-root>/docs/coordination/README.md`
- `<mpi-lib-root>/coordination-ops/lifecycle.md`
- `<mpi-lib-root>/coordination-ops/statuses.md`
- `<mpi-lib-root>/interop-ops/modes.md`

Reread the active session, task, file claim, and handoff records before
committing. A released file claim means no active writer owns the file; it does
not mean the pending changes are independently safe to commit.

Read `.agents/mpi-kanban/state/interop.json` when present. If it is missing,
assume `file` mode. In `nimbalyst` mode, Nimbalyst trackers/sessions are
canonical: do not move the MPI board entry during close-out. Commit/session
cleanup may proceed, but board snapshots require an explicit
`mpi-nimbalyst-sync` boundary.

If this session owns active `claimed` files, complete, release, or hand them off
before committing. If another fresh active session owns claimed files that are
part of the current task, do not commit those changes; ask the user or assign an
integrator.

### 1. Survey what changed

Run, in this order (small commands only Ã¢â‚¬â€ protect context on big sessions):

- `git status` Ã¢â‚¬â€ working tree state.
- `git diff --stat HEAD` Ã¢â‚¬â€ file list with line counts. **Do NOT run `git diff HEAD`**
  (full diff) here; the file list is enough to make decisions, and the full diff
  can be huge.

List the changed files back to the user before doing anything else.

### 2. Identify rule/doc impact

For each changed file, decide whether a rule or doc needs to update:

- New workspace, component, event, state key, or other architectural concept
  introduced or changed Ã¢â€ â€™ relevant `.agents/rules/*.md` file may need an edit.
- Architectural shift large enough to affect onboarding Ã¢â€ â€™ `docs/PROJECT.md`
  pointer may need an edit.

**Cardinal rule (per project CLAUDE.md): ASK the user before modifying any
architectural rule file.** Surface a one-line proposal per file ("Should I
update `.agents/rules/components.md` to mention the new mount adapter?") and
wait for explicit approval per file.

Edits MUST be concise Ã¢â‚¬â€ short bullets, no prose bloat, no new headings unless
strictly required.

### 2b. Lightweight project knowledge refresh

When `.agents/mpi-kanban/project-profile.md` or
`.agents/mpi-kanban/project-knowledge-index.md` exists, check whether this
session's changes affected architecture, conventions, important commands,
or agent guidance. Refer to
`<mpi-lib-root>/project-knowledge/updates.md` for the update
shape.

If any of the following changed in this session, propose a single,
concise edit:

- Top-level component moved/renamed/added Ã¢â€ â€™ profile architecture summary
  or knowledge index topic pointer.
- New command worth recording Ã¢â€ â€™ profile `Important Commands`.
- New convention or convention change Ã¢â€ â€™ profile `Conventions` or the
  referenced rule file.
- New subsystem with no topic block Ã¢â€ â€™ knowledge index `Topics`.
- `AGENTS.md`/`CLAUDE.md` no longer accurately points at the profile/index
  Ã¢â€ â€™ propose a pointer update.

Surface ONE proposal per file with current vs proposed content. Wait for
per-file approval. If nothing has drifted, say so in one line and move on.
For broader drift, recommend `mpi-project-refresh` instead of expanding
this pass.

### 3. Memory pass

Per `~/.claude/CLAUDE.md`:

- Anything learned worth keeping? Write to the right file under the project's
  memory directory or `~/.claude/memory/`.
- Update `MEMORY.md` index entry (one line, dated).
- Use `AskUserQuestion` BEFORE removing or modifying an existing memory entry
  Ã¢â‚¬â€ show current content + proposed change.

### 4. Commit

- Stage files BY NAME Ã¢â‚¬â€ never use `git add -A` or `git add .`. Mass-staging
  picks up unrelated work and secrets.
- The session running `mpi-end-session`, or an explicit integrator, owns the
  final commit summary. Base the message on current coordination state and the
  current Git state, not stale assumptions from a previous file claim.
- Commit message follows this repo's recent conventional style (read
  `git log --oneline -10` if uncertain). Write a clear "why" subject + a body
  if multiple distinct changes are bundled.

### 5. Close out the kanban entry

Lib pointers (read each only when its recipe is needed):

- `<mpi-lib-root>/kanban-ops/find.md` Ã¢â‚¬â€ `findKanban`, `findEntry`
- `<mpi-lib-root>/kanban-ops/steps.md` Ã¢â‚¬â€ `allStepsDone`
- `<mpi-lib-root>/kanban-ops/mutate.md` Ã¢â‚¬â€ `moveEntry`

Steps:

`VALIDATING` is the gate between implementation and final completion. All done
IMPLEMENTING steps move to VALIDATING. A VALIDATING entry moves to COMPLETED
only when the user explicitly approves final completion for that entry in the
current request.

If interop mode is `nimbalyst`, skip all MPI board movement in this section and
report: "Interop mode is nimbalyst - Nimbalyst trackers/sessions are canonical.
Skipping kanban close-out; use mpi-nimbalyst-sync for a board snapshot."

1. Read `<mpi-lib-root>/kanban-ops/find.md` for `findKanban`. Call `findKanban()`. If
   the file does not exist, skip kanban close-out Ã¢â‚¬â€ there is nothing to
   update. Tell the user: "No kanban file found Ã¢â‚¬â€ skipping board close-out."
2. Identify the active plan: the plan file most recently touched in this
   session (from `git diff --stat HEAD` or conversation context).
3. Call `findEntry(e => e.body matches "Plan file: <activePlan>")` Ã¢â‚¬â€ locate
   the PLANNING, IMPLEMENTING, VALIDATING, or COMPLETED entry tied to that
   plan. If the board has the legacy four-column shape, ask before inserting
   `## VALIDATING` between `## IMPLEMENTING` and `## COMPLETED`.
4. If no matching entry Ã¢â€ â€™ tell the user, do nothing further.
5. If found Ã¢â€ â€™ read `<mpi-lib-root>/kanban-ops/steps.md` for `allStepsDone`. Call
   `allStepsDone(entry.title)`:
   - **True** Ã¢â€ â€™ read `<mpi-lib-root>/kanban-ops/mutate.md` for `moveEntry`. Call
     `moveEntry(entry.title, "IMPLEMENTING", "VALIDATING")`. Report that the
     work is ready for validation with a clickable
     [kanban.md](.agents/mpi-kanban/kanban.md) link.
   - **False** Ã¢â€ â€™ leave the entry in IMPLEMENTING. Append a single line to the
     commit message body: `Note: session ended mid-implementation; kanban
     entry "<title>" still has open steps.` (Edit the commit if already made,
     or include in the original commit message.)
   - If the matching entry is already in VALIDATING, promote it to COMPLETED
     only when the user explicitly approved final completion in the current
     request. Otherwise ask before moving it.

After commit/kanban close-out, close or complete the active coordination session
and task according to `<mpi-lib-root>/coordination-ops/lifecycle.md`. Remove closed records
from active index arrays, but preserve pending records that still need cleanup,
review, verification, or integration.

### 6. Final report

Output to the user:

- Files committed (one line each).
- Rules/docs updated (one line each, or "none").
- Project profile/index updates (one line each, or "none").
- Memory entries written/updated (one line each, or "none").
- Kanban result should distinguish `IMPLEMENTING -> VALIDATING`, explicitly
  approved `VALIDATING -> COMPLETED`, entries still in IMPLEMENTING, and no
  matching board entry.
- Kanban result Ã¢â‚¬â€ one of:
  - `Kanban: "<title>" Ã¢â€ â€™ COMPLETED. [kanban.md](.agents/mpi-kanban/kanban.md)`
  - `Kanban: "<title>" still in IMPLEMENTING Ã¢â‚¬â€ open steps remain. [kanban.md](.agents/mpi-kanban/kanban.md)`
  - `Kanban: "<title>" -> VALIDATING. [kanban.md](.agents/mpi-kanban/kanban.md)`
  - `Kanban: no matching entry / no kanban file.`

Then a final `git status` Ã¢â‚¬â€ confirm working tree clean (or list deferred items
explicitly).

## Hard rules

- Never use `git add -A` / `git add .`.
- Never modify a rule file in `.agents/rules/` without explicit user approval.
- Never auto-overwrite or delete a memory entry Ã¢â‚¬â€ `AskUserQuestion` first.
- Never push (`git push`) Ã¢â‚¬â€ committing is enough; the user pushes when ready.
- Never commit over another fresh active writer's claim.
- Never treat kanban tags as coordination authority; reread `.agents` state.

## Success criteria

- All session-touched files committed (or explicitly deferred with reason).
- Rules/docs reflect any architectural change with the user's per-file approval.
- Memory entries written for non-obvious learnings; `MEMORY.md` index current.
- Kanban entry moved to VALIDATING if implementation steps are done, or moved
  from VALIDATING to COMPLETED only after explicit user approval.
- `git status` clean (or remaining items explained).
- Suggest `mpi-cleanup`
  after a completed entry if old plans or handoffs are likely stale. Do not run
  cleanup automatically.





