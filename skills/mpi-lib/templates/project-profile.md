---
schema: mpi-kanban/project-profile/v1
mode: scalable-foundation
mode_rationale: default at init
mode_source: default
setup_date: YYYY-MM-DD
last_refresh: YYYY-MM-DD
knowledge_index: .agents/mpi-kanban/project-knowledge-index.md
---

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

| Column  | Allowed `maturity`        |
| ------- | ------------------------- |
| `todo`  | `idea`, `planned`         |
| `doing` | `in-progress`, `validating` |
| `done`  | `complete`                |

`status` is a separate field (e.g. `active`, `accepted`). Words like `active`,
`deferred`, `done`, `implementing`, and `implementation` are NOT maturity
values. Words like `Validated`, `validated`, `validation`, `spec`, `scoped`,
`designed`, and `review` are also NOT maturity values. A `doing` card under
active work is `in-progress` (renders yellow), not `implementation`, `spec`, or
`idea`. Any other `maturity` renders as a red invalid card.

## Open Gaps

- None recorded yet.

## Mode Notes

- <YYYY-MM-DD>: <mode>. <one-line note on what new work should follow>.
