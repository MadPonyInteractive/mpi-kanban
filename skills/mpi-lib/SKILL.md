---
name: mpi-lib
description: MPI workflow pack - shared reference library for the mpi-kanban skills. Install with the full MPI workflow pack; do not invoke directly.
metadata:
  author: Mad Pony Interactive
  version: "0.6.0"
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
- `kanban-ops/` - board schema, entry lookup, mutation, archive, and errors.
- `plan-ops/` - plan shape, reading, derivation, and mutation guidance.
- `project-intent/` - project mode contracts.
- `project-knowledge/` - project profile and knowledge-index contracts.
- `templates/kanban.md` - board bootstrap template used by `kanban-ops/find.md`.

