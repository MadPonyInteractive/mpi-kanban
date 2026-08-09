---
name: mpi-lib
description: MPI workflow pack - shared reference library for the mpi-kanban skills. Agents may read its reference files directly for card/task-board rules; do not run it as a user workflow.
metadata:
  author: Mad Pony Interactive
---

# mpi-lib Support Skill

This is a support skill for the all-or-nothing MPI workflow pack, not a user
workflow. Agents may read its reference files directly when they need MPI
task-board, coordination, or workflow rules; do not run `mpi-lib` itself as the
workflow.

Other `mpi-*` skills read this library's reference files directly at
`${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/<sub/path>.md`, only when needed.

## Pack Version

The installed pack version is the `version` field in
`${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`. It is the only version stamp
the pack ships, and `/release` bumps it.

A project records the version it was last refreshed with as `pack_version` in
`.agents/mpi-kanban/project-profile.md` frontmatter. `mpi-project-refresh`
compares the two. Compare the numbers component by component, never as
strings: `0.9.0` is older than `0.10.0`, but sorts after it.

Nothing here reaches the network, so the pack cannot tell that a newer release
exists upstream - only that this install is older than one this project has
already seen. To update, the user runs:

`/plugin update mpi-kanban@mad-pony-interactive`

The plugin never reinstalls itself.

## Reference Index

- `config-ops.md` - project config discovery and rule bundle parsing.
- `coordination-ops/` - shared `.agents/mpi-kanban/state/` lifecycle and
  status vocabulary.
- `docs/coordination/` - coordination state layout, schemas, roles, UUID
  helper, and handoff migration references.
- `interop-ops/` - source-of-truth mode and Nimbalyst interop state guidance.
- `task-board-ops/` - JSON task board schema, read/mutation, migration, and
  validation/repair contracts.
- `kanban-ops/` - legacy Markdown board schema, lookup, mutation, archive, and
  errors for compatibility and migration.
- `plan-ops/` - plan shape, reading, derivation, and mutation guidance.
- `project-intent/` - project mode contracts.
- `project-knowledge/` - project profile and knowledge-index contracts.
- `scripts/validate_board.py` - runnable live-board check:
  `python ${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/validate_board.py <project-root>`. Exits 0 when
  the board is consistent, 1 with one line per violation.
- `templates/board.json` - JSON board bootstrap template.
- `templates/interop.json` - default source-of-truth mode template.
- `templates/task.json` - task-card bootstrap template.
- `templates/project-profile.md` - project profile bootstrap template.
- `templates/project-knowledge-index.md` - project knowledge index template.
- `templates/kanban.md` - legacy Markdown board template.

