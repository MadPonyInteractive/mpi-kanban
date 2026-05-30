# Existing Knowledge Adoption

`mpi-project-setup` and `mpi-project-refresh` must adopt or improve existing
project knowledge before creating new MPI-managed artifacts. This file
defines the adoption process and the classification each existing source
falls into.

## Sources to inspect

Look at the project root and the conventional locations, in this order:

- `AGENTS.md`
- `CLAUDE.md`
- `.agents/rules/*.md`
- `README.md`
- `docs/` (especially `docs/architecture/`, `docs/PROJECT.md`,
  `docs/conventions.md`, `docs/contributing.md`)
- legacy MPI board/workflow files under `.claude/mpi-kanban/`
- `CONTRIBUTING.md`, `CONTRIBUTING.rst`
- existing memory: project memory directory and any `MEMORY.md`
- backlog/process files (`backlog.md`, `TODO.md`, `ROADMAP.md`,
  `CHANGELOG.md`)
- user-specified custom docs

Do not scan the entire repo for prose. The list above is the budget. If the
user points at a custom doc, treat that as the highest-priority source.

## Classification

Tag each inspected source with one of:

- **usable as-is:** matches MPI knowledge needs, current, no edits required.
  Profile/index will point at it.
- **small update:** mostly current but needs one or two precise edits to
  match repo reality.
- **index pointer:** the source is fine as-is and just needs an entry in the
  knowledge index so future agents find it.
- **convert to MPI-managed:** content fits the profile, knowledge index, or
  a rule file and should move there. Conversion proposes a new MPI file and
  either deprecates the source or leaves it as a pointer.
- **superseded historical reference:** records prior architecture/decisions
  that should be preserved but not loaded as current state. Move out of the
  active read path or annotate as historical.
- **conflict / uncertain:** contradicts another source or repo reality, or
  intent is unclear. Surface to the user; do not silently choose.

## Adoption map

Setup and refresh produce a single adoption map BEFORE writing any files.
The map is shown to the user for approval. Shape:

```markdown
## Adoption Map

- `AGENTS.md` -> **usable as-is**. Profile will point here for invocation
  surface.
- `docs/architecture/overview.md` -> **small update**. Diagram references
  `src/v1/` which moved to `src/api/`. Propose one-line fix.
- `.agents/rules/components.md` -> **usable as-is**. Knowledge index topic
  "Components" will point here.
- `docs/old-arch.md` -> **superseded historical reference**. Move into
  `docs/archive/` or leave with a top-of-file note.
- `TODO.md` -> **index pointer**. Stays where it is; index lists it under
  backlog.
- `.claude/mpi-kanban/kanban.md` -> **small update**. Propose migrating or
  snapshotting it into the JSON task board at `.agents/mpi-kanban/board.json`
  and `.agents/mpi-kanban/tasks/<id>/`.
- `CONTRIBUTING.md` and `README.md` disagree on the dev server command ->
  **conflict / uncertain**. Ask the user.
```

## Conflict handling

When two sources disagree, the skill does not pick. It surfaces the
conflict, names the candidate truths, and asks the user. Examples of
genuine conflict:

- Two rule files claim ownership of the same convention with different
  rules.
- A doc says one thing about architecture; the code clearly does another.
- Two backlog/process files name the same item with different status.

The skill asks one focused question per conflict (or batches them via the
question tool when available) and records the resolution as a one-line
note in the profile `## Open Gaps` or the index `## Topic Gaps` if the
answer cannot be applied yet.

## Improvement before creation

Setup and refresh must prefer:

1. Pointing at an existing source (index pointer or usable as-is).
2. A small update to an existing source.
3. Creating a new MPI-managed artifact only when none of the above fits.

The reason: parallel MPI files that duplicate existing project docs cause
drift. The project profile and knowledge index are pointers first,
canonical content last.

