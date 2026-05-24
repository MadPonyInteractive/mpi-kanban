# Project Profile Schema

Canonical path: `.agents/mpi-kanban/project-profile.md`

The project profile is a compact, pointer-driven Markdown file. It is the
first knowledge file an agent reads when joining the project. It is NOT an
encyclopedia. It points at where the real information lives.

Hard size budget: aim for under 200 lines. If a section is growing, split it
into a referenced doc/rule and replace the body with a one-line pointer.

## Frontmatter

```yaml
---
schema: mpi-kanban/project-profile/v1
mode: prototype | mvp | scalable-foundation
mode_rationale: one short line, e.g. "user chose scalable-foundation at setup, 2026-05-23"
mode_source: user | repo-evidence | default
setup_date: YYYY-MM-DD
last_refresh: YYYY-MM-DD
knowledge_index: .agents/mpi-kanban/project-knowledge-index.md
---
```

## Body sections

### `## Project Summary`

Two to four sentences. What the project is, who it serves, and the
non-obvious purpose. No marketing tone.

### `## Architecture Summary`

Five to fifteen lines. Top-level components, how they connect, and where
boundaries are. Prefer a short bullet list and a pointer at the end:

```markdown
- Backend: Python service at `src/api/`
- Frontend: React app at `web/`
- Background workers: `src/workers/`

Detail: see `docs/architecture/overview.md`.
```

If the project already has an architecture doc, this section is mostly a
pointer. Do not duplicate the doc here.

### `## Conventions`

One bullet per convention. Each bullet is one line, points at where the
convention is enforced or documented if applicable.

```markdown
- New API routes go under `src/api/routes/` and register in `routes/index.py`.
- Tests live next to source as `*_test.py`. See `.agents/rules/testing.md`.
```

If there are no project-specific conventions yet, write a single line:
`No project-specific conventions recorded yet.`

### `## Important Commands`

Commands future agents will want. Keep to the small set that actually
matters. One line each, with what they do.

```markdown
- `npm run dev` - start dev server
- `pytest -k "<expr>"` - run a focused test
- `python scripts/seed.py` - reset local DB
```

### `## Read First`

Files a fresh agent should read before touching code. Pointer-only.

```markdown
- `README.md`
- `docs/architecture/overview.md`
- `.agents/rules/components.md`
```

### `## Open Gaps`

Known knowledge gaps, prototype shortcuts, mode-migration debt, or
under-documented areas. Each entry is one or two lines.

```markdown
- Auth flow predates mvp -> scalable-foundation transition; conventions for
  session handling not yet documented.
- No architecture doc for the worker queue; recorded on backlog.
```

### `## Mode Notes`

Optional. Short notes about behavior expectations tied to the current mode
and any active migration. When mode changes, append a dated bullet here
rather than rewriting prior notes.

```markdown
- 2026-05-23: scalable-foundation. New work follows full guardrails; legacy
  `src/legacy/` predates conventions and is touched only when needed.
```

## Update rules

- `mpi-project-setup` writes the initial profile only after the user approves
  the proposed content.
- `mpi-project-refresh` proposes edits when repo reality has drifted. It
  never overwrites user-owned content without approval.
- `mpi-end-session` proposes a lightweight refresh when implementation
  changed architecture, conventions, commands, or agent guidance. The user
  must approve before the profile is updated.
- `mpi-project-mode` updates `mode`, `mode_rationale`, `mode_source`, and
  appends a `## Mode Notes` bullet.
- Profile edits prefer pointers to existing docs/rules over copying content.
- Profile edits preserve sections the user has clearly customized.

