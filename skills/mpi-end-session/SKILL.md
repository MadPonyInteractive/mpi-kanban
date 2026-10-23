---
name: mpi-end-session
description: MPI workflow pack - Close out finished MPI work. Syncs rules and docs, heals project knowledge, writes memory, resolves every validating card, commits and pushes, and closes the JSON task card. Use when the user says "end session", "wrap up", "commit and close", "we're done", "close this out", "MPI end session", "$mpi-end-session", or "/mpi-end-session". This is the expensive, once-per-finished-job skill - when the work merely continues in a fresh session, use mpi-handoff instead.
---

# mpi-end-session Skill

The work is finished. This preserves what the session learned into rules,
docs, and memory, commits it, and closes the task card. It is the LAST step of
brainstorm -> plan -> continue -> end-session, and deliberately thorough: a
knowledge pass run once per finished job is cheap; run at every session switch
it is not.

Sub-files live in `${CLAUDE_PLUGIN_ROOT}/skills/mpi-end-session/`; read one
only when its step says so: `peers.md` (step 0 gate did not clear),
`growth-loop.md` (step 2, a convention was proved), `repairs.md` (step 10, a
skipped Doing phase or an invalid maturity).

Work along silently. Each pass's outcome goes on the report's `Passes:` line,
not in a message of its own.

## Wrong skill?

Work not finished - the user said "handoff", "new session", "start fresh",
"context is big", or a plan phase ended with more pending -> stop and run
`mpi-handoff`; it commits, pushes, and writes the handoff in about a minute and
skips every pass below, none of which can be concluded mid-job. Genuinely
unclear -> default to `mpi-handoff` and say so in one line: it is cheap, loses
nothing, and close-out can still run later. Never write a handoff here.

## 0. Scope gate

Read `.agents/mpi-kanban/state/index.json` FIRST (under 3 KB). **Parse it as
`utf-8-sig`** - PowerShell `>`, `Out-File`, and `Set-Content -Encoding utf8`
all add a BOM, and plain `utf-8` `json.load` dies on it with
`Unexpected UTF-8 BOM`. A counter is CLEAR when it is `[]`, `0`, **or absent**;
the shape varies by repo, so measure it, never assume.

`active_sessions`, `active_tasks`, `active_file_claims`, `pending_file_states`
and `open_messages` ALL clear -> solo: skip the coordination references
(~28 KB of multi-agent rules a solo, file-mode close-out - most close-outs -
cannot use) and the open-messages check. Otherwise -> read `peers.md` and
follow it before committing. `active_handoffs` is deliberately NOT in the
condition: an open handoff says the last session ended mid-thread, not that a
peer is active. Still reread the handoff records.

**Never skippable:** `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md`,
`read.md`, and `mutate.md` before any card write; the write recipes are in
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/implement.md`.

## 1. Survey what changed

`git status` and `git diff --stat HEAD` only - never `git diff HEAD`; the file
list is enough to decide, and the full diff can be huge. Do not print the list
back to the user.

## 2. Rule/doc impact

Per changed file: a new or changed workspace, component, event, state key, or
other architectural concept -> the relevant `.agents/rules/*.md` may need an
edit; a shift large enough to affect onboarding -> the `docs/PROJECT.md`
pointer. This session proved an uncovered convention -> `growth-loop.md`.

Cardinal rule: an architectural rule-file change is a `Your call:` line, never
a write before a yes.

## 2b. Project knowledge

`.agents/mpi-kanban/project-profile.md` or `project-knowledge-index.md` exists
-> did this session change architecture, conventions, important commands, or
agent guidance? Update shape:
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/updates.md`. Drifted ->
a `Your call:` line per file, current vs. proposed, with the agent's pick;
apply on a yes in a follow-up commit. Broader drift -> recommend
`mpi-project-refresh`.

## 3. Knowledge healing (do NOT skip)

The routing system (CLAUDE.md -> folder README -> subsystem doc) only stays
trustworthy if every agent that hits a gap repairs it. Replay THIS session -
did any of these happen?

- **Dead or wrong pointer** - a doc/rule/memory/skill named a file, section,
  function, or flag that no longer exists, or lives elsewhere.
- **Routing gap** - the task matched no router row, or the routed doc lacked
  the fact, forcing a codebase search or a wrong first attempt.
- **Rule gap** - a mistake or user correction an existing rule should have
  prevented but does not cover; or a rule that actively misled.
- **Skill friction** - a skill or playbook step failed, was ambiguous, or
  needed improvisation.
- **Memory drift** - an entry contradicted reality or duplicated the docs.

Heal at the source: the ONE doc the project's map routes to, never a catch-all
dump file. Mechanical heals (dead pointers, broken links, stale references,
memory corrections, MEMORY.md index drift) -> fix directly. Substantive ones
(new rule text, doc additions, router rows, skill edits) -> one `Your call:`
line per file, current vs. proposed. **Never edit the pack itself**: files
under the installed plugin root are not project files; record the change as a
memory note or a card. Never invent a gap to have something to heal.

## 4. Memory

Per `~/.claude/CLAUDE.md`: write anything worth keeping to the project memory
directory or `~/.claude/memory/`, with one dated line in the `MEMORY.md` index.
Changing an existing entry is a `Your call:` line, current vs. proposed, with
the agent's pick; nothing edited before a yes.

## 5. Board check

`python ${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/validate_board.py <project-root>`

- Exit 0: continue.
- Non-zero: report every violation line verbatim and fix the board through the
  task-board recipes before committing (inconsistent board state:
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/validate.md`). Never commit a board the validator
  rejects, and never hand-edit `task.json` to silence it.
- Python or script missing, or any launch failure: skip, put it on the
  report's `Passes:` line, continue. This check never blocks close-out by being
  unavailable.

**Consolidation sweep:** 8 or more `todo` cards -> follow
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/close-out/consolidation.md`, or offer
`mpi-umbrella` as its own pass. Umbrellas are a `Your call:` line; nothing is
created, closed, merged, or deleted before a yes. Fewer -> skip silently.

## 6. `validating` is not a parking space

Every card this session touched lands in exactly one of two states. There is no
third, and silence is not one of them.

**1. Evidence exists -> move it to `done`. Do not ask.** Agent verification is
sufficient: passing tests, a live probe, a real log line, a harness run, a diff
showing the change. Do not hold a proven card for a rubber stamp.

**2. A human's eyes or ears are genuinely required -> ASK, in this session.**
Only a judgement no test can make qualifies: does this LOOK right, SOUND right,
is this copy good, is this the product call. Name the card and the ONE thing
needed, in one line. Unanswered when the session ends -> say so in the report;
an unanswered ask is visible, a silent park is not.

Every `validating` card gets one report line - its evidence and its outcome
(moved, or the one question). A real board once reached 19 cards in `doing`,
16 of them `validating`; twelve closed in one pass the moment the user was
asked, every one with its evidence already recorded.

## 7. Project extension point, then the claim auditor

`.agents/mpi-kanban/close-out.md` exists -> run its project steps HERE, after
the shared passes and **before** the commit, so anything approved lands in the
same commit. Each (release awareness, changelog, version drift, dependencies)
is a `Your call:` line unless the file says otherwise.

Then dispatch `agents/claim-auditor.md` when it ships with the installed
plugin: read-only, output capped at 40 lines, verdicts sorted FALSE first.
**Running this skill IS the user's request for that dispatch**, as it is for
the commit. A standing "do not call agents unless the user asked" instruction
is a default against *unprompted* dispatch; it does not veto this step. Say so
rather than quietly deferring - that reflex is why the auditor once never ran,
and unaudited claims reach public changelogs.

Skip it only when the session produced no factual claim to audit (a card move,
a scratch script, a gitignored config edit), and **state the skip and its
reason** - a silent skip is indistinguishable from a clean audit. Its findings
are evidence, not verdicts: re-verify each `file:line` against the file before
editing any copy; it has produced a confidently wrong finding whose "fix" would
have put a false claim into a public changelog.

## 8. Commit

Running this skill IS the user's explicit request to commit this session's
touched files, even when a general "commit only when asked" instruction is in
effect. Do not ask again; do not report "did not commit".

- `git add` new files by name - never `-A` or `.` - then
  `git commit --only <path> ... -m "<subject>"`. A bare commit commits the
  whole INDEX, so a peer's staged files ride along. Read `git status --short`
  AFTER the commit: `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/git-ops/commit.md`.
- Message in this repo's recent conventional style; a clear "why" subject, a
  body when several changes are bundled. Never commit over another fresh
  writer's claim.

## 9. Push

`push_policy` from `.agents/mpi-kanban/project-profile.md` frontmatter; absent
-> `auto`. `auto` pushes, `ask` asks in one line then pushes on approval,
`never` leaves the branch unpushed and says so. Rejected push: `git fetch`,
`git merge --ff-only`, retry ONCE; still failing -> report and stop. Never
force-push, and **never auto-rebase a shared tree**. Worker sub-agents never
commit or push, whatever the policy says.

## 10. Close the task card

`validation.md` is the gate between implementation and completion; checklists,
validation notes, and handoffs live in workspace files, not `task.json`. Card
badges and attention are never coordination authority; `state/` is.

1. `findBoard()`; the active plan is the plan file most recently touched this
   session (`git diff --stat HEAD` or context).
2. Locate the task by explicit ID, active plan link, required attention in
   `doing`, or active coordination task `task_card`. None -> the report says no
   card close-out was performed.
3. In `todo` or `doing`: read `checklist.md` and `validation.md`. Implementation
   incomplete -> leave the card; note `Note: session ended mid-implementation;
   task "<id>" still has open implementation work.` in the commit body when
   appropriate. In `todo` with implementation work, or an invalid or incoherent
   maturity -> `repairs.md` before any move.
4. **Close on evidence.** Validation represented and work verified ->
   `moveTask(id, "done", actor, reason)` (agent evidence counts, step 6). Close
   resolved coordination task records tied to that `task_card` and drop them
   from `active_tasks`; leave `needs_review`, `needs_verification`, or
   `needs_integration` records active.
5. A human judgement genuinely needed -> ask the ONE question (step 6).
   Unanswered at the end -> keep it in `doing`,
   `setAttention(id, "required", reason, actor)`, and say so.
6. Already `done` -> do not move it again; update only concise summary fields
   or attention.

Then close or complete the coordination session and task per
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md`, removing
closed records from active index arrays and keeping pending ones that still
need cleanup, review, verification, or integration. Release this session's file
claims: `python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/task_ops.py" release`.

## 11. Final report - close-out order

Paste this block; do not redecide the wording. Everything else goes in the
card or the plan.

```text
<BREAKS USERS: what + "fixed, test added" or "card MPI-n made"> | Nothing breaking | Not checked: <why>
Changed from the brief: <what and why>          (only when something did)
Left before close: <what, or "nothing">
Your call: <question> My pick: <answer>         (one line each, only when needed)
Done: <what landed> - <the check that proved it>
Validating: <MPI-n> - <evidence> - <moved | the one question>   (one line per validating card)
Passes: knowledge <healed n | no gaps hit>, memory <n | none>, board <ok | skipped: why>, audit <n FALSE | skipped: why>, coordination <read | skipped: solo>
Spent: <amount> of <approved amount>            (only when money was spent)
<n> unrelated notes saved to the card           (only when any)
```

Line 1 is word for word, never a paraphrase. `Nothing breaking` is earned:
verification ran, passed, found nothing breaking; else `Not checked: <why>`.
A skipped step goes on `Passes:` with its reason. Unrelated finds ->
`brief.md` `## Noticed`; print only the count. Old plans, handoffs, closed
coordination state, or archived workspaces likely stale -> add a `Your call:`
for `mpi-cleanup`; never run it automatically.

Then one `git status` confirming a clean tree, or naming what was deferred.
