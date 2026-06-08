---
name: mpi-lib
description: MPI workflow pack - shared reference library for the mpi-kanban skills. Install with the full MPI workflow pack; do not invoke directly.
metadata:
  author: Mad Pony Interactive
  version: "0.8.3"
---

# mpi-lib Support Skill

This is a support skill for the all-or-nothing MPI workflow pack, not a user
workflow. Do not invoke it directly.

Other `mpi-*` skills locate this sibling skill at first use, cache its root
path as `<mpi-lib-root>`, and read individual reference files only when needed.

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
- `templates/board.json` - JSON board bootstrap template.
- `templates/interop.json` - default source-of-truth mode template.
- `templates/task.json` - task-card bootstrap template.
- `templates/project-profile.md` - project profile bootstrap template.
- `templates/project-knowledge-index.md` - project knowledge index template.
- `templates/kanban.md` - legacy Markdown board template.

