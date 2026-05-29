---
name: mpi-create-plan
description: MPI workflow pack - Create a compact/default MPI plan for normal work. Use when the user says "MPI create plan", "create an MPI plan", "create a plan", "make a plan", "plan this", "$mpi-create-plan", or after brainstorming when the task can be implemented as one coherent flow with final verification.
---

# mpi-create-plan Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Create a compact plan at `docs/plans/YYYY-MM-DD-<slug>.md` and reflect it on
the kanban board. This is the default planning path for normal work.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

Use `mpi-create-large-plan` instead when the work needs investigation,
multiple phases, explicit parallel batches, or complex risk management. In
particular, if the work can be split into independent implementation tasks with
disjoint ownership, it belongs in a large plan: compact plans stay one coherent
flow and never carry `## Parallel Batch` sections.

## Plan shape

```markdown
# <Goal>

## Current State

Brief facts known at planning time.

## Implementation

- [ ] Implement the planned change end to end. **Verify:** <final verification>

## Completed

- [ ] Nothing yet.

## Remaining Work

- Implement the planned change end to end.

## Plan Drift

- None yet.

## Verification

Final verification instructions.

## Preservation Notes

Docs, rules, memory, or cleanup notes to consider before handoff/end-session.
```

Keep the plan compact. Do not split related work into many checklist items just
because several files may change.

## Workflow

1. Understand the goal or BACKLOG entry from `mpi-brainstorm`.
2. **Load project knowledge if present.** Read
   `.agents/mpi-kanban/project-profile.md` and
   `.agents/mpi-kanban/project-knowledge-index.md` when they exist. Follow
   the context-budget rules in
   `<mpi-lib-root>/project-knowledge/indexing.md`: read pointer
   files first, then only the topic-matching docs/rules. Do not scan all
   rules and docs.
3. If the goal is clearly large or uncertain, or if independent parallel
   implementation looks likely (work splits into disjoint-ownership tasks),
   recommend `mpi-create-large-plan` instead and wait for
   confirmation.
4. Write the compact plan file. Include project mode in `## Current State`
   when the profile exists ("Project mode: scalable-foundation"). Pull
   relevant conventions or commands from the matched topic block only.
5. Update the kanban board.

## Kanban update

Lib pointers, read only when needed:

- `<mpi-lib-root>/kanban-ops/_schema.md` - locked entry shape and forbidden
  freehand entry format
- `<mpi-lib-root>/kanban-ops/find.md` - `findEntry`, `ensureKanban`
- `<mpi-lib-root>/kanban-ops/mutate.md` - `moveEntry`, `updateEntry`, `createEntry`
- `<mpi-lib-root>/interop-ops/modes.md` - source-of-truth mode gate

Before mutating the board, inspect its column shape. If a locked column is
missing (legacy four-column boards, or older boards missing
`## IMPLEMENTING`), pause and ask before inserting the missing column. Do not
silently repair broader shape drift here — recommend `mpi-project-refresh` for
multi-column or unknown-column drift. A single missing `## VALIDATING` between
`## IMPLEMENTING` and `## COMPLETED` may be inserted after explicit approval.

Before mutating `kanban.md`, read `.agents/mpi-kanban/state/interop.json` when
it exists. If `source_of_truth` is `nimbalyst`, do not move or create MPI board
entries. Report:

```text
Interop mode is nimbalyst, so Nimbalyst trackers/sessions are canonical. I created the plan file, but I will not update .agents/mpi-kanban/kanban.md. Update the Nimbalyst tracker/session, or run mpi-nimbalyst-sync for an explicit snapshot boundary.
```

If the file is missing or `source_of_truth` is `file`, continue with the normal
kanban update below.

If `mpi-brainstorm` passed a BACKLOG title, match that entry. Otherwise ask:

```text
Does this work already have a BACKLOG entry? If yes, what's the title? (or "no" for a fresh PLANNING entry)
```

If a BACKLOG entry matches:

1. `moveEntry(title, "BACKLOG", "PLANNING")`.
2. Replace its tag with `[PLAN]`.
3. Replace its body fence with `Plan file: docs/plans/YYYY-MM-DD-<slug>.md`.

If no entry matches:

1. `ensureKanban()`.
2. Create a PLANNING entry with title, `[PLAN]`, priority (ask, default
   `medium`), `defaultExpanded: true`, and body
   `Plan file: docs/plans/YYYY-MM-DD-<slug>.md`.

Confirm:

```text
Kanban: "<title>" -> PLANNING. [kanban.md](.agents/mpi-kanban/kanban.md)
Next: say "continue this plan" to start implementation.
```

## Hard rules

- Do not implement.
- Do not create a large multi-step checklist in this skill.
- Do not add `## Parallel Batch` syntax to a compact plan.
- If the work obviously needs phased investigation, or splits into independent
  parallel implementation tasks, redirect to `mpi-create-large-plan`.
- Entries written to `kanban.md` MUST use the `### Title` + 2-space-indented
  metadata bullets + 4-space-indented ```` ```md ```` body fence schema from
  `<mpi-lib-root>/kanban-ops/_schema.md`. Never write a top-level
  `- **Title**` bullet, a free-form `Steps:` block, or a bare `Plan file:`
  line outside the body fence, even if surrounding entries on the board
  already use those malformed shapes. If existing entries are malformed,
  surface them and recommend `mpi-project-refresh`; do not adopt the
  malformed style.
- Plan steps belong in the plan file under `## Implementation`. Steps on the
  kanban entry are added by `mpi-continue` on the PLANNING → IMPLEMENTING
  transition via `<mpi-lib-root>/kanban-ops/steps.md`. Do not add a `steps`
  block to a PLANNING entry here.




