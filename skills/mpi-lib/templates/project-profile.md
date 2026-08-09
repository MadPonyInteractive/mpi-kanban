---
schema: mpi-kanban/project-profile/v1
mode: scalable-foundation
mode_rationale: default at init
mode_source: default
setup_date: YYYY-MM-DD
last_refresh: YYYY-MM-DD
pack_version: <plugin.json version at setup/refresh time>
push_policy: auto
knowledge_index: .agents/mpi-kanban/project-knowledge-index.md
---

<!--
push_policy controls what `mpi-end-session` does after it commits:
  auto   push (default)
  ask    ask in one line, push on approval
  never  do not push; report the branch as unpushed
A rejected push retries once after `git fetch` + `git merge --ff-only`, then
reports. It never force-pushes and never rebases a shared tree.
-->


# Project Profile

## Project Summary

<2-4 sentences. What this project is, who it serves, the non-obvious purpose.>

## Architecture Summary

- <top-level component> at `<path>`
- <top-level component> at `<path>`

Detail: <pointer to an architecture doc, or remove this line>.

## Conventions

- No project-specific conventions recorded yet.

## Important Commands

- `<command>` - <what it does>

## Read First

- `README.md`

## Task Board Card Contract

`maturity` is a fixed enum. Never invent values and never copy a `status` or
intent word into it. Allowed values, by column:

| Column  | Allowed `maturity` |
| ------- | ------------------ |
| `todo`  | `idea`, `planned`, `research`, `needs-decision`, `blocked`, `deferred` |
| `doing` | `in-progress`, `validating` |
| `done`  | `complete`, `rejected` |

When to use `todo` values: `research` — needs investigation before planning;
`needs-decision` — understood but a user/product decision is outstanding;
`blocked` — ready but waiting on another card or an external dependency;
`deferred` — deliberately postponed, not being picked up in the current
stretch. For `done`: `rejected` — closed without being built, kept as a
record of the decision.

`status` is a separate field (e.g. `active`, `accepted`). Words like `active`,
`done`, `implementing`, and `implementation` are NOT maturity values. Words
like `Validated`, `validated`, `validation`, `spec`, `scoped`, `designed`, and
`review` are also NOT maturity values. A `doing` card under active work is
`in-progress` (renders yellow), not `implementation`, `spec`, or `idea`. Any
other `maturity` renders as a red invalid card.

## Open Gaps

- None recorded yet.

## Mode Notes

- <YYYY-MM-DD>: <mode>. <one-line note on what new work should follow>.
