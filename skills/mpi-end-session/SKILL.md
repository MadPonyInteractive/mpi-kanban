---
name: mpi-end-session
description: Close session — sync rules/docs, commit touched files, move kanban entry to COMPLETED if all steps done. Use when user says "end session", "wrap up", "commit and close", "/mpi-end-session".
---

# mpi-end-session Skill

Wrap up the current session cleanly: sync docs/rules with code changes, commit
touched files, persist any new memory, and close out the active kanban entry.

This skill is the LAST step in the brainstorm → write-plan → execute-next →
end-session loop. Run it when the user signals the session is done.

## Process

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
- Commit message follows this repo's recent conventional style (read
  `git log --oneline -10` if uncertain). Write a clear "why" subject + a body
  if multiple distinct changes are bundled.

### 5. Close out the kanban entry

Read `lib/kanban-ops.md` once. Then:

1. `findKanban()`. If the file does not exist, skip kanban close-out — there is
   nothing to update. Tell the user: "No kanban file found — skipping board
   close-out."
2. Identify the active plan: the plan file most recently touched in this
   session (from `git diff --stat HEAD` or conversation context).
3. `findEntry(e => e.body matches "Plan file: <activePlan>")` — locate the
   IMPLEMENTING entry tied to that plan.
4. If no matching entry → tell the user, do nothing further.
5. If found → call `allStepsDone(entry.title)`:
   - **True** → `moveEntry(entry.title, "IMPLEMENTING", "COMPLETED")`. Report
     the move in chat with a clickable [kanban.md](.claude/mpi-kanban/kanban.md)
     link.
   - **False** → leave the entry in IMPLEMENTING. Append a single line to the
     commit message body: `Note: session ended mid-implementation; kanban entry
     "<title>" still has open steps.` (Edit the commit if already made, or
     include in the original commit message.)

### 6. Final report

Output to the user:

- Files committed (one line each).
- Rules/docs updated (one line each, or "none").
- Memory entries written/updated (one line each, or "none").
- Kanban result — one of:
  - `Kanban: "<title>" → COMPLETED. [kanban.md](.claude/mpi-kanban/kanban.md)`
  - `Kanban: "<title>" still in IMPLEMENTING — open steps remain. [kanban.md](.claude/mpi-kanban/kanban.md)`
  - `Kanban: no matching entry / no kanban file.`

Then a final `git status` — confirm working tree clean (or list deferred items
explicitly).

## Hard rules

- No `mcp__nimbalyst-*` calls anywhere in this skill.
- Never use `git add -A` / `git add .`.
- Never modify a rule file in `.claude/rules/` without explicit user approval.
- Never auto-overwrite or delete a memory entry — `AskUserQuestion` first.
- Never push (`git push`) — committing is enough; the user pushes when ready.

## Success criteria

- All session-touched files committed (or explicitly deferred with reason).
- Rules/docs reflect any architectural change with the user's per-file approval.
- Memory entries written for non-obvious learnings; `MEMORY.md` index current.
- Kanban entry moved to COMPLETED if all steps done; otherwise left in
  IMPLEMENTING with a note in the commit.
- `git status` clean (or remaining items explained).
