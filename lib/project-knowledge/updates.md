# Profile and Index Maintenance Rules

`mpi-project-setup`, `mpi-project-refresh`, `mpi-project-mode`, and
`mpi-end-session` may propose updates to the project profile, knowledge
index, rules, and memory pointers. This file is the single source for how
those updates behave.

## Approval

All writes require explicit user approval, except where called out below.

- **First-time creation:** the proposal is the full draft of the profile or
  index. The skill writes only after the user approves.
- **Edits to an existing profile or index:** the proposal shows current
  content vs proposed content per section. The skill writes only after the
  user approves each section change.
- **Edits to rule files (`.claude/rules/*.md`):** ASK per file. Cardinal
  rule, same as `mpi-end-session`. Never edit a rule without explicit
  approval.
- **Edits to memory:** prefer pointing at existing Claude memory. Only
  propose new or changed memory entries when the user agrees the knowledge
  belongs in memory and not in the profile/index/rules. Use
  `AskUserQuestion` before removing or modifying existing memory entries.
- **Edits to `AGENTS.md`:** project setup may create or update `AGENTS.md`
  directly after the user approves the setup proposal. Prefer the
  pointer-first strategy: keep existing agent entrypoints concise and point
  at MPI profile/index files instead of duplicating project knowledge.

## Pointer-first preference

When in doubt, the profile and index point at existing files. Do not copy
content from a rule or doc into the profile/index.

If the same convention appears in three places, propose consolidating into
one canonical file and pointing the others at it. Surface the proposal; do
not auto-merge.

## Preservation of user-owned content

- Sections the user has clearly customized (non-template wording, project-
  specific phrasing, hand-written examples) must be preserved verbatim
  unless the user approves a rewrite.
- When the schema changes, propose a migration patch rather than overwriting
  the file.
- Historical content (superseded architecture, prior conventions) is moved
  or annotated, not deleted, unless the user asks for deletion.

## Drift detection

`mpi-project-refresh` runs the full drift pass. `mpi-end-session` runs a
lightweight pass on the files touched in the current session. Both follow
the same comparison shape:

- Profile claim vs repo reality: do the listed files exist? Do the named
  components match the directories? Are the important commands still valid?
- Index pointers vs repo reality: do the linked files exist? Have they been
  renamed?
- Conventions vs repo reality: does the changed code follow the documented
  convention? If not, is the convention wrong or the code wrong? Ask.

Report drift findings in a single proposal. Do not auto-fix.

## Frequency

- `mpi-project-setup` runs once when the project adopts MPI.
- `mpi-project-mode` runs on demand when mode changes.
- `mpi-project-refresh` runs on demand or when the user signals the profile
  is stale.
- `mpi-end-session` always runs the lightweight pass for the current
  session's touched files. It surfaces nothing when nothing has drifted.
