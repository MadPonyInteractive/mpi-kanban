---
name: mpi-end-session
description: MPI workflow pack - Close out finished MPI work. Syncs rules and docs, heals project knowledge, writes memory, resolves every validating card, commits and pushes, and closes the JSON task card. Use when the user says "end session", "wrap up", "commit and close", "we're done", "close this out", "MPI end session", "$mpi-end-session", or "/mpi-end-session". This is the expensive, once-per-finished-job skill - when the work merely continues in a fresh session, use mpi-handoff instead.
---

# mpi-end-session Skill

The work is finished. This preserves what the session learned into rules,
docs, and memory, commits it, and closes the task card.

It is the LAST step in the brainstorm -> create-plan/create-large-plan ->
continue -> end-session loop, and it is deliberately thorough - a knowledge
pass that runs once per finished job is cheap, and the same pass run at every
session switch is not.

Invocation: Use the installed Agent Skills invocation for this agent, or ask
naturally.

## Wrong skill?

If the work is not finished - the user said "handoff", "new session", "start
fresh", "context is big", or a plan phase just ended with more phases pending -
stop and run `mpi-handoff` instead. It commits, pushes, and writes the handoff
in about a minute, and skips every knowledge pass below because none of it can
be concluded mid-job.

Genuinely unclear? Ask in one line: `Finished, or continuing in a new session?`
Do not guess. The two differ by roughly ten minutes and everything that
survives the session.

## Process

### 0. Scope gate, then coordination state

Read `.agents/mpi-kanban/state/index.json` FIRST (under 3 KB). **Parse it as
`utf-8-sig`** - PowerShell `>`, `Out-File`, and `Set-Content -Encoding utf8`
all add a BOM, and plain `utf-8` `json.load` dies on it with
`Unexpected UTF-8 BOM`.

A counter is CLEAR when it is `[]`, `0`, **or absent**. The shape varies by
repo; measure it, never assume.

`active_sessions`, `active_tasks`, `active_file_claims`, `pending_file_states`
and `open_messages` ALL clear -> nothing to coordinate. **Skip** the four
coordination references (`docs/coordination/README.md`,
`coordination-ops/lifecycle.md`, `statuses.md`, `messages.md`) and the
open-messages check below. They are ~28 KB of multi-agent rules that a solo,
file-mode close-out - which is most close-outs - cannot use. Report the skip in
ONE line: `Coordination reads skipped: solo session, file mode.`

`active_handoffs` is deliberately NOT in the condition: an open handoff means
the last session ended mid-thread, which says nothing about whether a PEER is
active. Still reread the handoff records.

**Never skippable, whatever the gate says:**
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md`,
`read.md`, and `mutate.md` before any card write.

When the gate did NOT clear:

- Reread the active session, task, file claim, and handoff records before
  committing. A released file claim means no active writer owns the file; it
  does not mean the pending changes are independently safe to commit.
- Read any `open_messages` records that target the current session, task,
  changed files, workspace, agent, role, or user. Treat `open`, `acknowledged`,
  and `replied` as unresolved. They can block commit, require a
  reply/acknowledgement, require an integrator, or require a handoff first.
  This is an async boundary check only; do not promise live interruption,
  remote delivery, global broadcast, or a background broker.
- If this session owns active `claimed` files, complete, release, or hand them
  off before committing. If another fresh active session owns claimed files
  that are part of the current task, do not commit those changes; ask the user
  or assign an integrator.

### 1. Survey what changed

Small commands only, to protect context on big sessions:

- `git status` - working tree state.
- `git diff --stat HEAD` - file list with line counts. Do not run
  `git diff HEAD`; the file list is enough to decide, and the full diff can be
  huge.

List the changed files back to the user before doing anything else.

### 2. Rule/doc impact, and the growth loop

For each changed file, decide whether a rule or doc needs to update:

- New workspace, component, event, state key, or other architectural concept
  introduced or changed -> relevant `.agents/rules/*.md` file may need an edit.
- Architectural shift large enough to affect onboarding -> `docs/PROJECT.md`
  pointer may need an edit.

**Growth loop.** When this session PROVED an uncovered convention, propose the
artifact that would have prevented the friction. Four kinds, one loop:

| What repeated | Propose |
|---|---|
| A convention no rule file covers | a `.agents/rules/*.md` file, drafted from `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/rule.md`, with a `## Sub-Agent Briefing` section, added to the `rules` list in `.agents/mpi-kanban.local.md` so `mpi-brief-rule` can dispatch it |
| The same worker briefing assembled by hand more than once | a `.claude/agents/<name>.md` definition |
| The same multi-step procedure typed out again | a project skill under `.claude/skills/` |
| A prose rule that fired and was ignored, or a mistake a check could have caught | a hook under `.claude/hooks/` plus its `settings.json` registration |

Rules for the loop, all four kinds:

- **Cap 1-2 proposals per session.** More is noise and gets ignored.
- **Only from repetition that already happened** here or in a recorded earlier
  session. **Never propose from directory structure** - an empty
  `.claude/agents/` directory is not evidence anyone needs an agent.
- Propose; do not create. One line each, wait for approval.

Cardinal rule: creating or modifying any architectural rule file needs explicit
per-file approval. Keep the edits concise - short bullets, no prose bloat, no
new headings unless strictly required.

### 2b. Lightweight project knowledge refresh

When `.agents/mpi-kanban/project-profile.md` or
`project-knowledge-index.md` exists, check whether this session's changes
affected architecture, conventions, important commands, or agent guidance;
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/updates.md` has the
update shape.

Drifted -> propose one concise edit per affected file, current vs. proposed,
and wait for per-file approval. Nothing drifted -> say so in one line. Broader
drift -> recommend `mpi-project-refresh`.

### 3. Knowledge-healing pass (do NOT skip)

The routing system (CLAUDE.md -> folder README -> subsystem doc) only stays
trustworthy if every agent that hits a gap repairs it. Replay THIS session and
answer honestly - did any of these happen?

- **Dead or wrong pointer** - a doc/rule/memory/skill named a file, section,
  function, or flag that no longer exists, or lives elsewhere.
- **Routing gap** - the task matched no router row, or the routed doc lacked
  the fact, forcing a codebase search or a wrong first attempt.
- **Rule gap** - a mistake, or a user correction, that an existing rule should
  have prevented but does not cover; or a rule that actively misled.
- **Skill friction** - a skill or playbook step failed, was ambiguous, or
  needed improvisation.
- **Memory drift** - an entry contradicted reality or duplicated the docs.

Heal at the source: the ONE doc the project's map routes to, never a catch-all
dump file. Fix mechanical heals directly (dead pointers, broken links, stale
references, memory corrections, MEMORY.md index drift). Substantive changes -
new rule text, doc additions, router-row changes, skill edits - get a one-line
proposal per file and wait for approval.

**Never edit the pack itself.** Files under the installed plugin root are not
project files; record the change as a memory note or a card instead.

No friction this session -> say "no knowledge gaps hit" and move on. Never
invent a gap to have something to heal.

### 4. Memory pass

Per `~/.claude/CLAUDE.md`:

- Anything learned worth keeping? Write to the right file under the project's
  memory directory or `~/.claude/memory/`.
- Update the `MEMORY.md` index entry with one dated line.
- Ask before removing or modifying an existing memory entry; show current
  content plus the proposed change.

### 5. Board check

```text
python ${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/validate_board.py <project-root>
```

- Exit 0: continue.
- Exit non-zero: report every violation line verbatim and fix the board through
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` recipes before
  committing. Do not commit a board the validator rejects, and do not hand-edit
  `task.json` to silence it.
- Python missing, script missing, or any other launch failure: skip the check,
  say so in the final report, and continue. This check never blocks close-out by
  being unavailable.

#### Consolidation sweep

Count the `todo` cards. **8 or more** - follow
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/close-out/consolidation.md`, or offer
`mpi-umbrella` as its own pass. Fewer - skip silently, that is not sprawl.

### 6. `validating` is not a parking space

Every card this session touched lands in exactly one of two states. There is no
third, and silence is not one of them.

**1. Evidence exists -> move it to `done`. Do not ask.** Agent verification is
sufficient: passing tests, a live probe, a real log line, a harness run, a diff
showing the change. Do not hold a proven card for a rubber stamp.

**2. A human's eyes or ears are genuinely required -> ASK, in this session.**
Only a judgement no test can make qualifies: does this LOOK right, SOUND right,
is this copy good, is this the product call. Name the card and the ONE thing
needed, in one line. Session ends unanswered -> say so plainly in the report;
an unanswered ask is visible, a silent park is not.

**List every `validating` card before finishing**, with its evidence and its
outcome: moved, or the one question. A session ending with cards parked and no
question asked has not finished.

This exists because a real board reached 19 cards in `doing`, 16 of them
`validating`; twelve closed in one pass the moment the user was actually asked.
Every one had its evidence recorded already.

### 7. Project extension point, then the claim auditor

If `.agents/mpi-kanban/close-out.md` exists, run its steps HERE - after the
shared passes, **before** the commit, so anything it proposes lands in the same
commit. That file holds project-specific close-out steps: release awareness,
changelog checks, version-registry drift, dependency-set checks. Treat them as
pointers producing one-line proposals, same approval discipline as the rest of
close-out, unless the file says otherwise.

Then dispatch `agents/claim-auditor.md` when it ships with the installed
plugin: read-only, output capped at 40 lines, verdicts sorted FALSE first.

**Running this skill IS the user's request for that dispatch**, exactly as it
is for the commit in section 8. A standing "do not call agents unless the user
asked" instruction is a default against *unprompted* dispatch; naming this
skill is the ask, so that default does not veto this step. Say so out loud
rather than quietly deferring - faced with a standing rule and a soft "run it
here", the reflex is to obey the standing rule, and the auditor then never runs
at all. It exists because unaudited claims reach public changelogs.

Skip it only when the session produced no factual claim to audit - a card move,
a scratch script, a gitignored config edit. **A skip must be stated in the
report with its reason.** A silent skip is indistinguishable from a clean
audit, which is how this went unnoticed for weeks.

Its findings are evidence, not verdicts. It reports `file:line` for each one;
re-verify against the file before editing any copy. It has produced a
confidently wrong finding whose "fix" would have put a false claim into a
public changelog.

If neither exists, say nothing and continue.

### 8. Commit

Running this skill IS the user's explicit request to commit this session's
touched files. Commit without asking again, even if a general "commit only when
the user asks" instruction is otherwise in effect - invoking this skill is that
ask. Do not report "did not commit".

- Stage files by name; never use `git add -A` or `git add .`.
- The session running close-out, or an explicit integrator, owns the final
  commit summary. Base the message on current coordination and Git state, not
  stale assumptions from a previous file claim.
- Commit message follows this repo's recent conventional style. Read
  `git log --oneline -10` if uncertain. Write a clear "why" subject and a body
  if multiple distinct changes are bundled.

### 9. Push

Read `push_policy` from `.agents/mpi-kanban/project-profile.md` frontmatter;
absent -> `auto`. `auto` pushes, `ask` asks in one line then pushes on
approval, `never` leaves the branch unpushed and says so.

Rejected push: `git fetch`, `git merge --ff-only`, retry ONCE. Still failing -
report the rejection and stop. Do not force, and **never auto-rebase a shared
tree**. Worker sub-agents never commit and never push, whatever the policy
says.

### 10. Close out the task card

Lib pointers under `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/`, read
each only when its recipe is needed: `read.md` (`findBoard`, `findTask`,
`loadTask`), `mutate.md` (`moveTask`, `writeTask`, `ensureLinkedFiles`,
`appendEvent`, `setAttention`), `validate.md` (inconsistent board state).

`validation.md` is the gate between implementation and completion. Keep
checklists, validation notes, and handoffs in linked task workspace files, not
in `task.json`.

1. Call `findBoard()`.
2. Identify the active plan: the plan file most recently touched this session,
   from `git diff --stat HEAD` or conversation context.
3. Locate the task by explicit task ID, active plan link, required attention in
   `doing`, or active coordination task `task_card`. If none matches, report
   that no JSON task-card close-out was performed.
4. If the task is in `todo` or `doing`, inspect `checklist.md` for
   implementation progress and `validation.md` for validation state. If
   implementation remains incomplete, leave the card in place and note
   `Note: session ended mid-implementation; task "<id>" still has open
   implementation work.` in the commit body when appropriate.

   Skipped-Doing auto-correct: if the card is in `todo` but real implementation
   work exists for it - checked items in `checklist.md`, OR changed files this
   session that belong to this task's plan - the Doing phase was skipped.
   Before any `done` move, call
   `beginImplementation(id, actor, planPath, sessionTitle)` to backfill
   `todo -> doing`, set `maturity: "in-progress"`, and derive the checklist,
   then continue. Print:
   `Note: card "<id>" skipped the Doing phase; auto-corrected through doing before done.`
   A card with no implementation work keeps moving `todo -> done` with no
   warning. The lifecycle is always `To do -> Doing -> Done` for implemented
   work.

   Maturity auto-correct: before any move, check `maturity` against the enum
   (`idea`, `planned`, `research`, `needs-decision`, `blocked`, `deferred`,
   `in-progress`, `validating`, `complete`, `rejected`) and its column. If the
   value is invalid (e.g. `active`, `accepted`, `done`, `Validated`,
   `validated`, `validation`, `spec`, `implementing`, `implementation`) or
   incoherent with the column, call
   `writeTask(id, { "maturity": "<corrected>" }, actor)` (`todo` -> keep any
   valid todo value, otherwise `planned`; `doing` -> `in-progress`, or
   `validating` when validation is represented; `done` -> keep `rejected` when
   the work was closed without being built, otherwise `complete`). Print:
   `Note: card "<id>" had invalid maturity "<old>"; corrected to "<new>".`

5. **Close on evidence.** If validation state is represented in the task
   workspace and the work is verified, call
   `moveTask(id, "done", actor, reason)`. Agent verification is sufficient -
   see section 6. Then close resolved coordination task records tied to that
   `task_card` and remove them from `state/index.json` `active_tasks`. Leave
   unresolved `needs_review`, `needs_verification`, or `needs_integration`
   records active.
6. If the card genuinely needs a human judgement, ask the ONE question in this
   session per section 6. Unanswered at the end -> keep it in `doing`, call
   `setAttention(id, "required", reason, actor)`, and say so in the report.
7. If the task is already in `done`, do not move it again. Update only concise
   summary fields or attention state when needed.
Then close or complete the active coordination session and task per
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md`. Remove
closed records from active index arrays; preserve pending records that still
need cleanup, review, verification, or integration.

### 11. Final report - four bullets, no more

Everything else goes in the card or the plan. This is what the user reads.

```markdown
**CHANGED:** <what landed, one line; commit subject + file count; pushed or not>
**VERIFIED:** <the command or check that proved it, and its result>
**STILL OPEN:** <cards left in doing, unanswered validation questions, deferred items, or "nothing">
**NEXT AGENT NEEDS:** <the one thing a fresh session must know, or "nothing">
```

Two additions are allowed below the four bullets, and only these:

- `Did not run:` - any close-out step skipped, with its reason. The claim
  auditor and the coordination reads are the usual two. Omit when nothing was
  skipped. A four-bullet report with no slot for this is why a skipped step
  reads as a passed one.
- `Noticed, not actioned:` - separate work found this session that was
  deliberately not turned into cards, one line each. Omit when empty. Do not
  create cards for these; the user decides.

Then one `git status` confirming a clean tree, or naming what was deferred.

## Hard rules

- Never use `git add -A` or `git add .`.
- Never modify a rule file in `.agents/rules/` without explicit user approval.
- Never auto-overwrite or delete a memory entry; ask first.
- The commit and the claim auditor's dispatch are both authorized by invoking
  this skill; neither needs a second ask.
- Pushing follows `push_policy`, default `auto`. Never force-push, never
  auto-rebase a shared tree, never commit over another fresh writer's claim.
- Card-write preflight is mandatory before any `column`, `maturity`, or
  `status` write: read
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` and
  `mutate.md`. Do not derive legal values from existing cards.
- Never treat task-card badges or attention as coordination authority; reread
  `.agents/mpi-kanban/state/`.
- A card moves to `done` on represented validation state plus verification.
  Agent evidence counts. When only a human judgement will do, ASK in this
  session - never park it silently in `validating`.
- Never write a handoff here. If the work turns out to be unfinished, stop and
  route to `mpi-handoff` - a close-out that also hands off is the expensive
  path this split exists to remove.
- The consolidation sweep proposes umbrellas; it never creates one without
  approval and never closes, merges, or deletes the clustered cards.
- Never edit files under the installed plugin root. Record pack changes as a
  memory note or a card instead.

## Success criteria

- All session-touched files committed, or explicitly deferred with a reason;
  pushed per `push_policy`.
- Rules/docs reflect any architectural change, with per-file approval.
- Knowledge gaps healed at the source, or "no knowledge gaps hit" stated.
- Memory entries written for non-obvious learnings; `MEMORY.md` index current.
- Every touched card is `done` on evidence, or has an asked question on record.
  No card parked in `validating` in silence.
- The claim auditor ran, or the report says why it did not.
- The report is four bullets; `git status` clean, or remaining items explained.
- Suggest `mpi-cleanup` when old plans, handoffs, closed coordination state, or
  archived task workspaces are likely stale. Do not run cleanup automatically.
