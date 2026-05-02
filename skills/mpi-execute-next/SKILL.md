---
name: mpi-execute-next
description: Execute the next incomplete to-do from an mpi plan file with a brief gate before code and a verified gate after. Use when the user says "next", "do the next task", "continue the plan", "execute next", or drops/pastes a plan file path and wants to run a to-do.
---

# mpi-execute-next Skill

## Purpose

Execute one to-do at a time from the plan in context, with two mandatory
gates: brief approval before code, and user choice after code.

The brief gate exists so the user can catch wrong assumptions before any code
is written. The post-implementation gate exists so the user can verify
behavior before deciding what to do next. **These gates are the entire point
of the human-in-the-loop pattern — never skip them.**

## Pre-conditions

The plan file path is available if any of these are true:

- The user passed it as an argument when invoking the command.
- The user pasted or mentioned a path in the current conversation.
- A `.md` plan file is visible in the current context.

Read the plan file immediately — do not ask if you can see the path.

If no plan path is visible anywhere → ask:
**"Which plan should I use? Please drop or paste the plan file path."** Stop.

If all to-dos are `[x]` → report plan complete (see "Last to-do" below). Do
NOT re-execute.

---

## Session setup (once per session, before first to-do — first invocation
against this plan)

Read `lib/kanban-ops.md` and `lib/plan-ops.md` once. Then:

1. **Locate the kanban entry** for this plan:
   - Call `findEntry(e => e.body matches "Plan file: <planPath>")`.
   - If `null` → tell the user no kanban entry references this plan; ask
     whether to create a fresh PLANNING entry first (`/mpi-write-plan`).
     Stop.

2. **If the entry is in PLANNING → transition it to IMPLEMENTING:**
   - Call `moveEntry(title, "PLANNING", "IMPLEMENTING")`.
   - Determine plan shape via `lib/plan-ops.md` ("is this plan phased?"):
     - **Phased** → steps = phase titles, stripped of `Phase N:` prefix and
       shortened to 3-6 words.
     - **Flat** → steps = each plan to-do, summarized to 3-6 words.
   - Build the `steps` array. Mark each step `[x]` if its source is already
     done in the plan (a fully-done phase, or a `[x]` to-do).
   - Call `addSteps(title, steps)`.
   - Confirm in chat: `Kanban: "<title>" → IMPLEMENTING. [kanban.md](.claude/mpi-kanban/kanban.md)`.

3. **If the entry is already in IMPLEMENTING → no transition needed.** Continue.

---

## Gate 1 — Brief (before code)

1. Read the plan file. Find the first `[ ]` incomplete to-do.
2. Read `brief-template.md` (in this skill folder) to get the exact brief
   format.
3. Output the brief to the user — to-do text, files touched, approach, risk,
   verify after.
4. End your message with: *"Reply 'go' (or 'ok', 'yes', 'proceed') to start
   implementation."*

**STOP HERE.** Do not write any code. Do not edit any files. Do not continue.
Wait for the user to reply before doing anything else.

"go" (or any affirmative) only approves starting implementation. It does NOT
approve moving to the next to-do.

---

## Phase 2 — Implementation (only after user replies "go")

Implement the to-do exactly as described. While implementing, **add
`console.log(...)` calls** where helpful to make the verification testable
without UI.

After implementation, report:

- Files changed.
- Key changes made.
- What console log to look for (if applicable).

---

## Gate 3 — Post-implementation (AFTER implementation, before any next step)

After implementation is complete, output this completion message verbatim
(filling in the bracketed parts):

---
To-do implementation complete.

**Files changed:** [list files]
**Key changes:** [what was done]

**Verify:**
[Copy the full Verify instruction verbatim from the current to-do in the plan.
Do not paraphrase. If you added console.log calls, append: "Also look in
browser dev tools console for: [exact log message]"]

**Option 1 — Verified** — say "1" or "verified"
**Option 2 — Keep talking** — say "2" or "keep talking"
---

**STOP HERE.** Do not write any more text. Do not show the next to-do. Do
not show the next brief. Do not mark the plan. The only valid next action is
waiting for the user to reply with Option 1 or Option 2.

---

## If user chooses Option 1 (verified)

Do these steps in order — all of them, no skipping:

1. Remove all `console.log` calls added during verification (edit the files).
2. **Mark the plan to-do `[x]`.** Use `markTodoDone(planPath, todoText)` per
   `lib/plan-ops.md`.
3. **Flip the matching kanban step.** Read `lib/kanban-ops.md` for `markStep`.
   - **Phased plan:** identify the phase containing this to-do. Call
     `phaseAllDone(phase)`. If true → `markStep(title, "<phase summary>", true)`.
     If false → leave the kanban step as is (other to-dos in the phase remain).
   - **Flat plan:** the kanban step at the same zero-based index as the
     completed plan to-do. Call `markStep(title, "<step text>", true)` (use
     the step text, since indices may shift visually).

**Check if more to-dos remain (`[ ]` in the plan):**

### If more to-dos remain:

Output:

```
To-do [N] done.

What next?
  → "next" — brief for to-do [N+1]
  → "end"  — close this session (run /mpi-end-session)
```

Wait for user reply. If "next" → go to Gate 1 for next to-do. If "end" → tell
the user to invoke `/mpi-end-session`.

### If this was the last to-do (all `[x]`):

Output:

```
Plan complete. All to-dos done.

Suggested next step: run /mpi-end-session to commit, sync rules/docs, and
close out the kanban entry (it will move to COMPLETED automatically once all
steps are flipped).
```

Note: the kanban entry stays in IMPLEMENTING until `/mpi-end-session` runs
and confirms all steps are `[x]`. This skill does NOT move the entry to
COMPLETED — that is `mpi-end-session`'s responsibility.

---

## If user chooses Option 2 (keep talking)

- Do nothing. Stay in the conversation.
- Wait for the user to tell you what to do next.
- Append once: *"Context getting large? Run `/mpi-handoff` before starting a
  new session."*

---

## Critical rules

These rules protect the human-in-the-loop contract. Breaking either gate
defeats the purpose of the system.

1. **Brief gate is mandatory.** Never implement without presenting the brief
   and waiting for "go".
2. **Post-implementation gate is mandatory.** Never skip the Option 1 /
   Option 2 choice. Never show the next to-do's brief before the user replies
   to Gate 3.
3. **Gate 3 Verify must come from the plan.** Copy the `**Verify:**` line
   verbatim. Do not substitute, omit, or paraphrase.
4. **One to-do at a time.**
5. **Execution is always sequential.**
6. **Do not modify the plan except to mark `[x]` after Option 1 is chosen.**
7. **No git commits.** Committing is `mpi-end-session`'s responsibility.
8. **No git push.**

## Related commands

- `/mpi-write-plan` — create a plan from a complex goal.
- `/mpi-handoff` — generate handoff doc when context is large.
- `/mpi-end-session` — wrap up: commit, sync docs, close kanban entry.
