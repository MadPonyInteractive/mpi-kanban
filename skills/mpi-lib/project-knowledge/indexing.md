# Context-Budget Indexing

Agents must read narrowly. The knowledge index exists so a session can load
only the files that match the task topic, not the whole project.

## Reading order

1. `.agents/mpi-kanban/project-profile.md` if present. Frontmatter, summary,
   architecture summary, conventions, important commands, `Read First`,
   `Open Gaps`.
2. `.agents/mpi-kanban/project-knowledge-index.md` if present. Find the topic
   block closest to the current task.
3. Only the files listed under the matching topic block (`Read first`,
   `Rules`, `Memory`).
4. Cross-cutting entries from the index when relevant.
5. If no topic matches, ask the user for a pointer instead of scanning the
   repo.

This order replaces "read everything." Skills that previously prompted the
agent to scan all of `CLAUDE.md`, all rules, or all docs upfront should
delegate to the profile + index when both exist.

## When profile/index do not exist

Fall back to existing behavior: `AGENTS.md`/`CLAUDE.md` entrypoints,
`README.md`, and the smallest set of files the task obviously touches.
Recommend `mpi-init` to the user when the lack of profile/index is
costing time.

## When profile/index exist but seem stale

If the index points at a file that has moved or been renamed, do not silently
re-scan. Report the staleness to the user and recommend `mpi-project-refresh`.
The user decides whether to refresh now or proceed with current task and
fix later.

## Cost discipline

- Read pointer files first; their job is to tell you which one to read next.
- Avoid reading entire rule trees. Read the specific rule file the topic
  points at.
- Avoid reading memory files unless the index lists a memory pointer for the
  topic.
- When a sub-agent investigation is needed, brief the sub-agent with the
  profile mode and the relevant topic block, not the whole project.

