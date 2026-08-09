---
name: mpi-end-session
description: MPI workflow pack - Close out an MPI session through one of two exits, resume or done. Syncs rules/docs, heals project knowledge, commits and pushes touched files, resolves every validating card, and then either writes a handoff JSON for a fresh session or closes the task card. Use when the user says "end session", "wrap up", "commit and close", "we're done", "MPI end session", "$mpi-end-session", "/mpi-end-session", or asks for a handoff - "handoff", "create a handoff", "new session", "start fresh", "context is big", "$mpi-handoff" - and when a plan phase just completed and a new one starts.
---

# mpi-end-session Skill

One close-out, two exits:

- **resume** - the work continues in a fresh session. Writes a handoff JSON at
  `.agents/mpi-kanban/state/handoffs/<uuid>.json` that `mpi-continue` loads.
- **done** - the work is finished. Closes the JSON task card.

Everything before the exit is shared: scope gate, rule/doc pass, knowledge
healing, memory, board check, the `validating` sweep, the project extension
point, commit, and push. The two exits used to be two skills the user ran back
to back by hand; this runs what they ran.

This skill is the LAST step in the brainstorm -> create-plan/create-large-plan
-> continue -> end-session loop.

Legacy Markdown kanban close-out is compatibility behavior only when no JSON
board exists.

Invocation: Use the installed Agent Skills invocation for this agent, or ask
naturally.

## Pick the exit first

Decide before running the process, and say which one in the first line of
output:

- The user said "handoff", "new session", "start fresh", "context is big", or a
  plan phase just ended with more phases pending -> **resume**.
- The user said "done", "wrap up", "we're done", "end session", or the plan is
  complete -> **done**.
- Unclear -> ask in one line: `Resume later, or done?` Do not guess. The exits
  differ in what survives the session.

## Process

### 0. Scope gate, then coordination state

Read these two small files FIRST (both under 3 KB):

- `.agents/mpi-kanban/state/index.json`
- `.agents/mpi-kanban/state/interop.json`

**Parse both as `utf-8-sig`.** A UTF-8 BOM is present in the wild - PowerShell
`>`, `Out-File`, and `Set-Content -Encoding utf8` all add one - and a plain
`utf-8` `json.load` dies on it with `Unexpected UTF-8 BOM`.

Treat a counter as CLEAR when it is `[]`, `0`, **or absent**. The shape varies
by repo: some write empty lists, some omit the field entirely. Measure it,
never assume.

If `active_sessions`, `active_tasks`, `active_file_claims`,
`pending_file_states` and `open_messages` are ALL clear, there is nothing to
coordinate. **Skip** these reads:

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/docs/coordination/README.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/statuses.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/messages.md`

and skip the open-messages boundary check below. If `interop.json` says
`source_of_truth: "file"`, or the file is absent, also skip
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/interop-ops/modes.md` and treat the mode
as `file`.

`active_handoffs` is deliberately NOT part of the condition. It is a *resume*
signal, not a coordination-reference signal: a handoff left open means the last
session ended mid-thread, which says nothing about whether a PEER is active.
The five counters above already answer that. Still reread the handoff records.

**Never skippable, whatever the gate says:**
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md`,
`read.md`, and `mutate.md` before any card write.

Report the skip in ONE line, e.g.
`Coordination reads skipped: solo session, file mode.`
If ANY counter is non-clear, read all of the references above as written.

Why: those references are ~28 KB of multi-agent coordination rules that are
inapplicable to a solo, file-mode close-out - which is most close-outs.

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

In `nimbalyst` mode, Nimbalyst trackers/sessions are canonical: do not move
JSON task cards or legacy MPI board entries during close-out. Commit/session
cleanup may proceed, but board snapshots require an explicit
`mpi-nimbalyst-sync` boundary.

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

- **Cap 1-2 proposals per session.** More than that is noise and gets ignored.
- **Only from repetition that already happened** in this session or a recorded
  earlier one. **Never propose from directory structure** - an empty
  `.claude/agents/` directory is not evidence anyone needs an agent.
- Propose; do not create. One line per proposal, wait for approval.

Cardinal rule: ask the user before modifying any architectural rule file.
Creating one needs the same explicit approval. Surface a one-line proposal per
file and wait for explicit approval per file.

Edits must be concise: short bullets, no prose bloat, no new headings unless
strictly required.

### 2b. Lightweight project knowledge refresh

When `.agents/mpi-kanban/project-profile.md` or
`.agents/mpi-kanban/project-knowledge-index.md` exists, check whether this
session's changes affected architecture, conventions, important commands, or
agent guidance. Refer to
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/updates.md` for the
update shape.

If architecture, commands, conventions, topic coverage, or AGENTS/CLAUDE
pointers drifted, propose one concise edit per affected file with current vs.
proposed content. Wait for per-file approval. If nothing has drifted, say so in
one line. For broader drift, recommend `mpi-project-refresh`.

### 3. Knowledge-healing pass (do NOT skip)

The routing system (CLAUDE.md -> folder README -> subsystem doc) only stays
trustworthy if every agent that hits a gap repairs it. Replay THIS session and
answer honestly:

- **Dead or wrong pointer?** A doc/rule/memory/skill pointed at a file,
  section, function, or flag that no longer exists - or at the wrong home.
- **Routing gap?** The task matched no router row, or the routed doc lacked the
  fact needed, forcing a codebase search or a wrong first attempt.
- **Rule gap?** A mistake happened, or the user corrected the agent, that an
  existing rule SHOULD have prevented but does not cover - or a rule misled.
- **Skill/command friction?** A skill or playbook step failed, was ambiguous,
  or needed improvisation to complete.
- **Memory drift?** A memory entry contradicted reality or duplicated what docs
  now hold.

Heal at the source. Facts go to the ONE doc the project's map routes to, never
a catch-all dump file:

- **Mechanical heals - fix directly, no approval needed:** dead pointers,
  broken links, stale file/function references, memory-entry corrections,
  MEMORY.md index drift.
- **Substantive changes - one-line proposal per file, wait for approval:**
  new or changed rule text, doc content additions, router-row changes, project
  skill step edits.
- **Never edit the pack itself.** Files under the installed plugin root are not
  project files. Record the needed change as a memory note or a task card so an
  issue can be filed on the pack.

No friction this session -> say "no knowledge gaps hit" in one line and move
on. Never invent a gap to have something to heal.

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

### 6. `validating` is not a parking space

Every card this session touched must land in exactly one of two states. There
is no third option, and silence is not one of them.

**1. Evidence exists -> move it to `done`. Do not ask.**
Agent verification counts and is sufficient: passing tests, a live probe, a
real log line, an offline harness run, a diff that shows the change. Do not
hold a proven card for a rubber stamp.

**2. A human's eyes or ears are genuinely required -> ASK, in this session,
before it ends.**
Only a judgement no test can make qualifies: does this LOOK right, does it
SOUND right, is this copy good, is this the product call. Name the card and the
ONE thing needed, in one line. If the user answers, act on it. If the session
ends without an answer, say so plainly in the report - an unanswered ask is
still visible, a silent park is not.

**List every `validating` card before finishing**, with its evidence and its
outcome: moved, or the one question. A session that ends with cards still
parked and no question asked has not finished.

This exists because a real board reached 19 cards in `doing`, 16 of them
`validating`; twelve closed in one pass the moment the user was actually asked.
Every one had its evidence recorded already.

### 7. Project extension point

If `.agents/mpi-kanban/close-out.md` exists, run its steps HERE - after the
shared passes, **before** the commit, so anything it proposes lands in the same
commit.

That file holds project-specific close-out steps: release awareness, changelog
checks, version-registry drift, dependency-set checks. They belong to the
project, not to the pack. Treat its steps as pointers producing one-line
proposals, same approval discipline as the rest of close-out, unless the file
says otherwise.

If `agents/claim-auditor.md` ships with the installed plugin, run it here too:
read-only, output capped at 40 lines, verdicts sorted FALSE first.

If neither exists, say nothing and continue.

### 8. Commit

Running this skill IS the user's explicit request to commit this session's
touched files. Commit without asking again, even if a general "commit only when
the user asks" instruction is otherwise in effect - invoking this skill is that
ask. Both exits commit. Do not report "did not commit".

- Stage files by name; never use `git add -A` or `git add .`.
- The session running close-out, or an explicit integrator, owns the final
  commit summary. Base the message on current coordination and Git state, not
  stale assumptions from a previous file claim.
- Commit message follows this repo's recent conventional style. Read
  `git log --oneline -10` if uncertain. Write a clear "why" subject and a body
  if multiple distinct changes are bundled.

### 9. Push

Read `push_policy` from `.agents/mpi-kanban/project-profile.md` frontmatter.
Absent -> `auto`.

| `push_policy` | Behavior |
|---|---|
| `auto` | Push. This is the default. |
| `ask` | Ask in one line, then push on approval. |
| `never` | Do not push. Say the branch is unpushed. |

On a rejected push: `git fetch`, then `git merge --ff-only`, then retry ONCE.
If that fails, report the rejection and stop - do not force, and **never
auto-rebase a shared tree**.

Worker sub-agents never commit and never push, whatever the policy says.

### 10A. Exit `done` - close out the task card

Lib pointers, read each only when its recipe is needed:

- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md` - `findBoard`,
  `findTask`, `loadTask`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/mutate.md` - `moveTask`,
  `writeTask`, `ensureLinkedFiles`, `appendEvent`, `setAttention`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/validate.md` - checks
  when board state is inconsistent
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/kanban-ops/find.md` - legacy
  `findKanban`, `findEntry`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/kanban-ops/steps.md` - legacy
  `allStepsDone`
- `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/kanban-ops/mutate.md` - legacy
  `moveEntry`

`validation.md` is the gate between implementation and completion. Keep
implementation checklists, validation notes, and handoffs in linked task
workspace files, not in `task.json`.

If interop mode is `nimbalyst`, skip this whole section and report:
`Interop mode is nimbalyst - skipping task-board close-out; use
mpi-nimbalyst-sync for a board snapshot.`

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
8. If `board.json` is missing, fall back to legacy kanban compatibility: locate
   the PLANNING, IMPLEMENTING, VALIDATING, or COMPLETED entry tied to the
   active plan. All done IMPLEMENTING steps move to VALIDATING. A VALIDATING
   entry moves to COMPLETED on the same evidence rule.

Then close or complete the active coordination session and task per
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/coordination-ops/lifecycle.md`. Remove
closed records from active index arrays; preserve pending records that still
need cleanup, review, verification, or integration.

### 10B. Exit `resume` - write the handoff

The card stays where it is. Do not close it, and do not move it out of `doing`.

**1. Gather state from the conversation.** Not from git - the commit in step 8
already recorded what changed on disk; the handoff records what is in your
head and nowhere else:

- What was the user originally trying to accomplish?
- What is complete vs. pending?
- The very next action the fresh session should take.
- Key decisions, constraints, and gotchas discovered this session.
- Which plan file is active.

**2. Preservation pass.** Capture knowledge while this session still has
context:

- Update the active plan's `## Current State`, `## Plan Drift`, and
  `## Preservation Notes` if stale.
- Mark the outgoing session `handoff_ready`; mark unfinished file claims
  `complete`, `needs_integration`, or `needs_review`; keep pending-change
  provenance visible in `pending_file_states`.
- Preserve unresolved message context: acknowledge, reply, resolve, or
  supersede only when this session can do so accurately; otherwise list the
  message paths and needed follow-up under `knowledge_preservation.pending`,
  `context.constraints`, or `files_to_read_first`.
- Long-form context belongs in the task workspace under
  `.agents/mpi-kanban/tasks/<id>/`, not in `task.json`.

**3. Look up the active task card** with
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/read.md`: call
`findBoard()`, then locate the task by ID, linked plan path, or required
attention in `doing`. Set `task_card` to its ID, title, column, and workspace
path with links. If no JSON board exists, use legacy `findKanban()` and set
`kanban_entry` to the matching IMPLEMENTING/VALIDATING title. When a JSON card
exists, `kanban_entry` is `null`.

**4. Write the handoff** at `.agents/mpi-kanban/state/handoffs/<uuid>.json`,
creating the directory if missing. Generate `<uuid>` with
`python ${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/new_uuid.py`, or
`python -c "import uuid; print(uuid.uuid4())"` if that script is missing. Use
the same value for the filename and the JSON `id`.

```json
{
  "schema": "mpi-kanban/handoff/v1",
  "id": "<uuid>",
  "generated_at": "<ISO-8601 timestamp>",
  "from_session": "<state/sessions path, or null>",
  "to_role": "orchestrator | planner | implementer | reviewer | verifier | integrator | docs",
  "status": "open",
  "session": {
    "name": "<best description of the session>",
    "branch": "<current branch>"
  },
  "goal": {
    "original": "<what the user set out to do, verbatim or close paraphrase>",
    "status": "in_progress | blocked | complete",
    "summary": "<1-3 sentence summary of where things stand>"
  },
  "plan": {
    "file": "<path to active plan file, or null>",
    "completed": ["<done item 1>", "<done item 2>"],
    "pending": ["<next item 1>", "<next item 2>"]
  },
  "task_card": {
    "id": "<MPI-* id, or null>",
    "title": "<task title, or null>",
    "column": "<todo | doing | done, or null>",
    "workspace": "<.agents/mpi-kanban/tasks/<id>/, or null>",
    "links": {
      "plan": "<relative or project path, or null>",
      "checklist": "<relative or project path, or null>",
      "validation": "<relative or project path, or null>",
      "handoffs": "<relative or project path, or null>"
    }
  },
  "kanban_entry": "<legacy active IMPLEMENTING or VALIDATING title, or null>",
  "allowed_actions": ["<actions the next agent may take, e.g. read, continue, verify>"],
  "knowledge_preservation": {
    "completed": ["<docs/rules/memory/plan preservation done before handoff>"],
    "pending": ["<preservation item the next session must handle>"]
  },
  "next_action": {
    "description": "<exact instruction for the fresh session>",
    "command": "<optional skill or command to run first, e.g. mpi-continue>"
  },
  "context": {
    "key_decisions": ["<decision 1 and why>", "<decision 2 and why>"],
    "constraints": ["<constraint or gotcha 1>", "<constraint or gotcha 2>"],
    "files_modified": ["<path1>", "<path2>"],
    "files_to_read_first": ["<path1>", "<path2>"]
  },
  "project_knowledge": {
    "profile": "<.agents/mpi-kanban/project-profile.md if present, else null>",
    "knowledge_index": "<.agents/mpi-kanban/project-knowledge-index.md if present, else null>",
    "mode": "<profile mode if present, else null>",
    "relevant_topics": ["<topic block names the fresh session should load first>"]
  },
  "rules_active": ["<rule file that must be read>", "<rule file 2>"],
  "recent_events": [{ "at": "<ISO-8601 timestamp>", "event": "handoff_created" }],
  "resume_prompt": "<single paragraph the user can paste into a new session. Second person, present tense. Names the handoff file path and task ID, or the legacy kanban entry title when no task ID exists.>"
}
```

When `task_card.id` is present, also write a pointer at
`.agents/mpi-kanban/tasks/<id>/handoffs/<uuid>.json`:

```json
{
  "schema": "mpi-kanban/task-handoff-pointer/v1",
  "canonical_handoff": ".agents/mpi-kanban/state/handoffs/<uuid>.json"
}
```

Do not duplicate the handoff body into the task workspace. Add the handoff to
`state/index.json` `active_handoffs` and update `index.updated_at`. Mark any
handoff this one supersedes as resolved.

**5. Print the resume block.** Mandatory, every time, and never dump the full
JSON:

```text
Handoff saved: .agents/mpi-kanban/state/handoffs/<uuid>.json
Active task: "<MPI-* title>"   (or "none")

To resume in a new session, paste this:
---
Read .agents/mpi-kanban/state/handoffs/<uuid>.json and use mpi-continue to continue from where we left off.
The next action is: <next_action.description>
---
```

### 11. Final report - four bullets, no more

Everything else goes in the card, the plan, or the handoff. This is what the
user reads.

```markdown
**CHANGED:** <what landed, one line; commit subject + file count; pushed or not>
**VERIFIED:** <the command or check that proved it, and its result>
**STILL OPEN:** <cards left in doing, unanswered validation questions, deferred items, or "nothing">
**NEXT AGENT NEEDS:** <the one thing a fresh session must know, or the handoff path>
```

Two additions are allowed below the four bullets, and only these:

- `Noticed, not actioned:` - separate work found this session that was
  deliberately not turned into cards, one line each. Omit the heading when
  empty. Do not create cards for these; the user decides.
- The resume block from 10B, when the exit was `resume`.

Then one `git status` confirming a clean tree, or naming what was deferred.

## Hard rules

- Never use `git add -A` or `git add .`.
- Never modify a rule file in `.agents/rules/` without explicit user approval.
- Never auto-overwrite or delete a memory entry; ask first.
- Committing is in scope and authorized by invoking this skill, on BOTH exits.
- Pushing follows `push_policy`, default `auto`. Never force-push, and never
  auto-rebase a shared tree.
- Never commit over another fresh active writer's claim.
- Card-write preflight is mandatory before any `column`, `maturity`, or
  `status` write: read
  `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/task-board-ops/_schema.md` and
  `mutate.md`. Do not derive legal values from existing cards.
- Never treat task-card badges, attention, or legacy kanban tags as
  coordination authority; reread `.agents/mpi-kanban/state/`.
- A card moves to `done` on represented validation state plus verification.
  Agent evidence counts. When only a human judgement will do, ASK in this
  session - never park it silently in `validating`.
- On the `resume` exit, `resume_prompt` MUST be self-contained; the fresh
  session has zero memory. The copy/paste block is mandatory.
- New canonical handoffs MUST be written under
  `.agents/mpi-kanban/state/handoffs/`. `docs/handoffs/` is legacy
  compatibility, not canonical state.
- Never edit files under the installed plugin root. Record pack changes as a
  memory note or a card instead.

## Success criteria

- The exit was named in the first line of output.
- All session-touched files committed, or explicitly deferred with a reason;
  pushed per `push_policy`.
- Rules/docs reflect any architectural change, with per-file approval.
- Knowledge gaps healed at the source, or "no knowledge gaps hit" stated.
- Memory entries written for non-obvious learnings; `MEMORY.md` index current.
- Every touched card is `done` on evidence, or has an asked question on record.
  No card parked in `validating` in silence.
- On `resume`: a handoff JSON exists, is indexed, and its resume block was
  printed.
- The report is four bullets.
- `git status` clean, or remaining items explained.
- Suggest `mpi-cleanup` when old plans, handoffs, closed coordination state, or
  archived task workspaces are likely stale. Do not run cleanup automatically.
