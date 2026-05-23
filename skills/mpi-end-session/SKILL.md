---
name: mpi-end-session
description: MPI end session workflow. Close session, sync rules/docs, commit touched files, and move the kanban entry to COMPLETED if all steps are done. Use when user says "MPI end session", "end session", "wrap up", "commit and close", "$mpi-end-session", or "/mpi-kanban:mpi-end-session".
---

# mpi-end-session Skill

Wrap up the current session cleanly: sync docs/rules with code changes, commit
touched files, persist any new memory, and close out the active kanban entry.

This skill is the LAST step in the brainstorm → create-plan/create-large-plan
→ continue → handoff/continue → end-session loop. Run it when the user signals
the session is done.

Invocation: Claude Code users may run `/mpi-kanban:mpi-end-session`; Codex
users may run `$mpi-end-session` or ask naturally to end the MPI session.
References using `${CLAUDE_PLUGIN_ROOT}` mean the installed plugin root; Codex
resolves the same files relative to this plugin root.

## Process

### 0. Read coordination state

Read these references when `.agents/mpi-kanban/state/index.json` exists:

- `${CLAUDE_PLUGIN_ROOT}/docs/coordination/README.md`
- `${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/lifecycle.md`
- `${CLAUDE_PLUGIN_ROOT}/lib/coordination-ops/statuses.md`

Reread the active session, task, file claim, and handoff records before
committing. A released file claim means no active writer owns the file; it does
not mean the pending changes are independently safe to commit.

If this session owns active `claimed` files, complete, release, or hand them off
before committing. If another fresh active session owns claimed files that are
part of the current task, do not commit those changes; ask the user or assign an
integrator.

### 1. Survey what changed

Run, in this order (small commands only — protect context on big sessions):

- `git status` — working tree state.
- `git diff --stat HEAD` — file list with line counts. **Do NOT run `git diff HEAD`**
  (full diff) here; the file list is enough to make decisions, and the full diff
  can be huge.

List the changed files back to the user before doing anything else.

### 2. Identify rule/doc impact

For each changed file, decide whether a rule or doc needs to update:

- New workspace, component, event, state key, or other architectural concept
  introduced or changed → relevant `.claude/rules/*.md` file may need an edit.
- Architectural shift large enough to affect onboarding → `docs/PROJECT.md`
  pointer may need an edit.

**Cardinal rule (per project CLAUDE.md): ASK the user before modifying any
architectural rule file.** Surface a one-line proposal per file ("Should I
update `.claude/rules/components.md` to mention the new mount adapter?") and
wait for explicit approval per file.

Edits MUST be concise — short bullets, no prose bloat, no new headings unless
strictly required.

### 2b. Lightweight project knowledge refresh

When `.agents/mpi-kanban/project-profile.md` or
`.agents/mpi-kanban/project-knowledge-index.md` exists, check whether this
session's changes affected architecture, conventions, important commands,
or agent guidance. Refer to
`${CLAUDE_PLUGIN_ROOT}/lib/project-knowledge/updates.md` for the update
shape.

If any of the following changed in this session, propose a single,
concise edit:

- Top-level component moved/renamed/added → profile architecture summary
  or knowledge index topic pointer.
- New command worth recording → profile `Important Commands`.
- New convention or convention change → profile `Conventions` or the
  referenced rule file.
- New subsystem with no topic block → knowledge index `Topics`.
- `AGENTS.md`/`CLAUDE.md` no longer accurately points at the profile/index
  → propose a pointer update.

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
  — show current content + proposed change.

### 4. Commit

- Stage files BY NAME — never use `git add -A` or `git add .`. Mass-staging
  picks up unrelated work and secrets.
- The session running `mpi-end-session`, or an explicit integrator, owns the
  final commit summary. Base the message on current coordination state and the
  current Git state, not stale assumptions from a previous file claim.
- Commit message follows this repo's recent conventional style (read
  `git log --oneline -10` if uncertain). Write a clear "why" subject + a body
  if multiple distinct changes are bundled.

### 5. Close out the kanban entry

Lib pointers (read each only when its recipe is needed):

- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/find.md` — `findKanban`, `findEntry`
- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/steps.md` — `allStepsDone`
- `${CLAUDE_PLUGIN_ROOT}/lib/kanban-ops/mutate.md` — `moveEntry`

Steps:

1. Read `lib/kanban-ops/find.md` for `findKanban`. Call `findKanban()`. If
   the file does not exist, skip kanban close-out — there is nothing to
   update. Tell the user: "No kanban file found — skipping board close-out."
2. Identify the active plan: the plan file most recently touched in this
   session (from `git diff --stat HEAD` or conversation context).
3. Call `findEntry(e => e.body matches "Plan file: <activePlan>")` — locate
   the IMPLEMENTING entry tied to that plan.
4. If no matching entry → tell the user, do nothing further.
5. If found → read `lib/kanban-ops/steps.md` for `allStepsDone`. Call
   `allStepsDone(entry.title)`:
   - **True** → read `lib/kanban-ops/mutate.md` for `moveEntry`. Call
     `moveEntry(entry.title, "IMPLEMENTING", "COMPLETED")`. Report the move
     in chat with a clickable [kanban.md](.claude/mpi-kanban/kanban.md) link.
   - **False** → leave the entry in IMPLEMENTING. Append a single line to the
     commit message body: `Note: session ended mid-implementation; kanban
     entry "<title>" still has open steps.` (Edit the commit if already made,
     or include in the original commit message.)

After commit/kanban close-out, close or complete the active coordination session
and task according to `lib/coordination-ops/lifecycle.md`. Remove closed records
from active index arrays, but preserve pending records that still need cleanup,
review, verification, or integration.

### 6. Final report

Output to the user:

- Files committed (one line each).
- Rules/docs updated (one line each, or "none").
- Project profile/index updates (one line each, or "none").
- Memory entries written/updated (one line each, or "none").
- Kanban result — one of:
  - `Kanban: "<title>" → COMPLETED. [kanban.md](.claude/mpi-kanban/kanban.md)`
  - `Kanban: "<title>" still in IMPLEMENTING — open steps remain. [kanban.md](.claude/mpi-kanban/kanban.md)`
  - `Kanban: no matching entry / no kanban file.`

Then a final `git status` — confirm working tree clean (or list deferred items
explicitly).

## Hard rules

- Never use `git add -A` / `git add .`.
- Never modify a rule file in `.claude/rules/` without explicit user approval.
- Never auto-overwrite or delete a memory entry — `AskUserQuestion` first.
- Never push (`git push`) — committing is enough; the user pushes when ready.
- Never commit over another fresh active writer's claim.
- Never treat kanban tags as coordination authority; reread `.agents` state.

## Success criteria

- All session-touched files committed (or explicitly deferred with reason).
- Rules/docs reflect any architectural change with the user's per-file approval.
- Memory entries written for non-obvious learnings; `MEMORY.md` index current.
- Kanban entry moved to COMPLETED if all steps done; otherwise left in
  IMPLEMENTING with a note in the commit.
- `git status` clean (or remaining items explained).
- Suggest `$mpi-cleanup` in Codex or `/mpi-kanban:mpi-cleanup` in Claude Code
  after a completed entry if old plans or handoffs are likely stale. Do not run
  cleanup automatically.
