# Project Knowledge Index Schema

Canonical path: `.agents/mpi-kanban/project-knowledge-index.md`

The knowledge index maps task topics to the specific docs, rules, and memory
files an agent should load. It exists so a fresh session can load only
task-relevant context instead of scanning the entire project.

Hard size budget: aim for under 200 lines. If a topic block needs more, that
content belongs in a doc/rule, not the index.

## Frontmatter

```yaml
---
schema: mpi-kanban/project-knowledge-index/v1
profile: .agents/mpi-kanban/project-profile.md
last_refresh: YYYY-MM-DD
---
```

## Body sections

### `## How To Use`

Three to six lines. Tell the reader the index is a topic-to-files map, not a
substitute for the profile. Example:

```markdown
Match the topic closest to the current task. Read the listed files first.
If no topic matches, read the project profile and ask the user for a
pointer rather than scanning the repo end-to-end.
```

### `## Topics`

One subsection per topic. Topics are stable concepts (subsystems, layers,
flows), not task instances.

Each topic block uses this shape:

```markdown
### <topic name>

- **Read first:** `<pointer>`, `<pointer>`
- **Rules:** `.claude/rules/<file>.md` (optional)
- **Memory:** `<memory pointer or "none">`
- **Notes:** one short line of context (optional)
```

Example:

```markdown
### Auth and sessions

- **Read first:** `docs/architecture/auth.md`, `src/auth/README.md`
- **Rules:** `.claude/rules/auth.md`
- **Memory:** `~/.claude/memory/domain/auth-providers.md`
- **Notes:** session storage is mid-migration; see profile `## Open Gaps`.
```

### `## Cross-cutting`

Files that always belong in context, regardless of topic. Usually short.

```markdown
- `CLAUDE.md`, `AGENTS.md`
- `.claude/rules/*.md` when listed by topic
```

### `## Topic Gaps`

Topics the index knows are missing or incomplete. Pairs with the profile's
`## Open Gaps`. Each line is one or two lines.

```markdown
- No topic block yet for the worker queue subsystem.
```

## Update rules

- Index entries point at existing files. Do not invent docs that are not on
  disk.
- Prefer existing rule files in `.claude/rules/` and existing docs over
  proposing new MPI-specific files.
- Memory pointers reference Claude memory files (`~/.claude/memory/...`) or
  project memory under the project's memory directory. Never duplicate
  memory content into the index.
- `mpi-project-refresh` rewrites topics when files move or get renamed and
  proposes new topics when work introduces a new subsystem.
- `mpi-end-session` proposes index edits when implementation introduced or
  renamed a topic-worthy file.
