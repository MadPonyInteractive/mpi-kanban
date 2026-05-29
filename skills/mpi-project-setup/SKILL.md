---
name: mpi-project-setup
description: MPI workflow pack - Establish durable MPI project knowledge. Ask for project mode, inspect existing docs/rules/memory, propose an adoption map, and create or update the project profile, knowledge index, agent entrypoint pointers, rule files, and memory pointers after explicit user approval. Use when the user says "MPI project setup", "set up project knowledge", "adopt this project", "create a project profile", "$mpi-project-setup", or "/mpi-project-setup", or right after `mpi-brainstorm` for a brand-new project.
---

# mpi-project-setup Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Establish project knowledge an agent can rely on across sessions. Sets the
project mode, adopts existing docs/rules/memory, and writes a compact
pointer-driven profile and knowledge index.

This skill does NOT bootstrap the kanban board. The board is `mpi-init`'s
job. Setup may suggest running `mpi-init` afterward if no board exists, but
the two skills stay separate.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Required reading

Read each only when its section is needed:

- `<mpi-lib-root>/project-intent/modes.md` - mode contracts and
  default-mode rule.
- `<mpi-lib-root>/project-knowledge/profile-schema.md` - profile
  shape.
- `<mpi-lib-root>/project-knowledge/index-schema.md` - index
  shape.
- `<mpi-lib-root>/project-knowledge/adoption.md` - source list,
  classification, conflict handling.
- `<mpi-lib-root>/project-knowledge/indexing.md` - context-budget
  rules.
- `<mpi-lib-root>/project-knowledge/updates.md` - approval and
  preservation rules.

<HARD-GATE>
Do NOT write or modify any project file (profile, index, AGENTS.md, rules,
memory) before the user approves the setup proposal. Inspection and
proposal are safe; writes require explicit approval.
</HARD-GATE>

## Process

### 1. Detect new vs existing project

A project is "existing" if at least one of these is present: `README.md`
with content, `src/`, `AGENTS.md`, `CLAUDE.md`, `.agents/rules/`, `docs/`,
`.claude/mpi-kanban/`, or any source-code directory the user names.
Otherwise treat as new.

State which mode the skill is in: `new project setup` or
`existing project setup`. Ask the user to confirm if uncertain.

### 2. Ask for project mode

Per `<mpi-lib-root>/project-intent/modes.md`:

```text
What project mode should this be?
- prototype (throwaway, exploratory)
- mvp (first real version, correctness over polish)
- scalable-foundation (intended to grow; default)
```

Default to `scalable-foundation` if the user declines to answer. Record the
chosen mode and the source (`user` or `default` or `repo-evidence`).

For existing projects, also note any repo signals: prior CHANGELOG, presence
of CI, presence of architecture docs. Surface signals to the user only if
they meaningfully argue for a different default; do not turn this into a
forensic exercise.

### 3. Setup questions

Ask a small set of questions one at a time (or batched via the question
tool when available). Pick from this set; skip any the user already
answered:

- What is this project, in one or two sentences?
- What are the top-level components or directories?
- Are there project-specific conventions agents must follow?
- What commands matter for future agents (dev server, tests, scripts)?
- Where should agents read first when joining the project?
- Any known knowledge gaps or shortcuts to record up front?

For an existing project, prefer inferring answers from the repo and asking
the user to confirm, rather than asking from scratch.

### 4. Inspect existing knowledge (existing project only)

Per `<mpi-lib-root>/project-knowledge/adoption.md`, inspect:

- `AGENTS.md`, `CLAUDE.md`
- `.agents/rules/*.md`
- `README.md`
- `docs/` (architecture, project, conventions, contributing)
- `CONTRIBUTING.md`
- existing memory pointers (project memory directory, `MEMORY.md`)
- backlog/process files (`backlog.md`, `TODO.md`, `ROADMAP.md`,
  `CHANGELOG.md`)
- any user-named custom doc

Stay within the source budget. Do not read every file in the repo. Read
each candidate enough to classify it; do not load full content unless the
classification is uncertain.

Also check for legacy board/workflow state:

- `.claude/mpi-kanban/kanban.md`
- `.claude/mpi-kanban/archived*.md`
- `.claude/mpi-kanban/` files created by earlier MPI releases

If legacy files exist, propose migrating them to `.agents/mpi-kanban/`.
Never delete the legacy directory without explicit user approval. If the
target file already exists, classify the conflict and ask which copy is
canonical.

If a board file is found at either path, also audit its shape per
`<mpi-lib-root>/kanban-ops/_schema.md` "Board-shape drift":

- list missing locked columns (e.g. `## IMPLEMENTING`, `## VALIDATING`);
- list locked columns out of canonical order;
- list unknown H2 columns;
- list freehand entries that do not match the `### Title` + metadata
  bullets + fenced body schema.

Each finding becomes a per-finding proposal: insert missing column at the
canonical position; ask about unknown columns; list freehand entries for
the user to convert. Never reorder or rewrite user entries silently.

### 5. Build the adoption map

Classify each inspected source per `<mpi-lib-root>/project-knowledge/adoption.md`:
`usable as-is`, `small update`, `index pointer`, `convert to MPI-managed`,
`superseded historical reference`, `conflict / uncertain`.

When no `.agents/rules/*.md` files exist, do not treat that as "rules out of
scope." Decide whether any discovered project-specific conventions are better
stored as:

- short bullets in `.agents/mpi-kanban/project-profile.md`;
- pointers to existing docs; or
- a proposed new `.agents/rules/<topic>.md` file when the convention is
  reusable, important for sub-agents, or too detailed for the profile.

If no rule file is warranted, state why ("no reusable project-specific
conventions found yet" or "profile bullets are enough for now").

For new projects, the adoption map is short or empty. State that explicitly.

### 6. Draft the proposal

The proposal is a single message containing:

1. Project mode + rationale + source.
2. Draft project profile content
   (`.agents/mpi-kanban/project-profile.md`).
3. Draft knowledge index content
   (`.agents/mpi-kanban/project-knowledge-index.md`).
4. Adoption map (existing project) or "new project - no adoption needed".
5. Any agent entrypoint changes: create/update `AGENTS.md` with pointers to
   the profile and index. Default to creating `AGENTS.md` only if it does
   not exist OR if existing entrypoints are silent about MPI. Keep
   entrypoint edits to short pointer additions.
6. Any legacy board migration proposed from `.claude/mpi-kanban/` to
   `.agents/mpi-kanban/`, listing each file and whether it is a move, skip,
   or conflict requiring a decision. Include any board-shape migrations
   (missing locked columns to insert, unknown columns to resolve, freehand
   entries to convert).
7. Any rule file changes proposed, including new `.agents/rules/*.md` files or
   edits to existing rules (per file, one-line summary and purpose).
8. Any memory pointers proposed (existing project/user memory preferred; new
   memory entries called out explicitly).
9. Any deferred items the user should know about.

End with:

```text
Approve this setup? Reply "yes" to write all approved items, "yes except <list>"
to skip some, "change <item>" to adjust, or "no" to discard.
```

### 7. Clarification loop

If the user asks why a file should be created/updated, answer concisely.
The user may:

- skip an artifact ("skip the knowledge index for now");
- change project mode ("make it mvp instead");
- redirect adoption ("treat docs/old-arch.md as historical not pointer");
- defer rule/memory writes ("skip rule files", "skip memory writes");
- request edits before approval.

Loop until the user approves, declines, or specifies a partial approval.
Do not write any file before that point.

### 8. Apply approved writes

After approval, perform writes in this order. Skip steps the user opted
out of.

1. Create `.agents/mpi-kanban/` if missing.
2. Write `.agents/mpi-kanban/project-profile.md` using the
   `templates/project-profile.md` template as the
   base, filled in from the approved draft. Set `setup_date` and
   `last_refresh` to today.
3. Write `.agents/mpi-kanban/project-knowledge-index.md` from the
   `templates/project-knowledge-index.md` template.
4. Create or update `AGENTS.md` if approved. Pointer-first: add a short
   `## Project Knowledge` section that links to the profile and index.
   Preserve existing content; do not rewrite the file.
5. Apply approved legacy board migration:
   - Create `.agents/mpi-kanban/` if missing.
   - Move `.claude/mpi-kanban/kanban.md` to
     `.agents/mpi-kanban/kanban.md` only when the target does not exist or
     the user chose the legacy copy as canonical.
   - Move `.claude/mpi-kanban/archived*.md` and other legacy MPI board files
     to the same relative names under `.agents/mpi-kanban/` when targets do
     not conflict.
   - Preserve `.claude/mpi-kanban/` if any file remains, if the user did not
     approve deletion, or if the directory contains unknown files.
   - Apply approved board-shape migrations on the resulting
     `.agents/mpi-kanban/kanban.md`: insert each approved missing locked
     column at its canonical position, apply approved unknown-column
     resolutions, and rewrite each approved freehand entry to the
     `### Title` schema using `<mpi-lib-root>/kanban-ops/mutate.md`
     recipes. Preserve original body text inside the new ```` ```md ````
     body fence. Do not reorder entries across columns.
6. Apply approved rule file creations or edits per file. Each file should be
   concise and include a `## Sub-Agent Briefing` section when it is intended
   for `mpi-brief-rule` or parallel worker briefings.
7. Apply approved memory pointer entries.
8. Confirm: state which files were written, link them, and suggest the next
   useful step. If no kanban exists, suggest `mpi-init`. If brainstorm just
   ran, suggest `mpi-create-plan` or `mpi-create-large-plan`.

### 9. Final report

Output to the user:

- Mode set: `<mode>` (`<source>`).
- Files written (one line each).
- Files updated (one line each).
- Files skipped or deferred (with reason).
- Next suggested step.

## Hard rules

- Inspect first, propose second, write third. No write without approval.
- Default mode is `scalable-foundation` when unclear.
- Pointer-first: prefer pointing at existing docs/rules over copying
  content into profile/index.
- Creating `.agents/rules/*.md` is allowed during setup when the approved
  proposal identifies reusable project-specific conventions that do not already
  have a good home.
- Never create or edit `.agents/rules/*.md` without explicit per-file approval.
- Never overwrite `.agents/mpi-kanban/kanban.md` with a legacy
  `.claude/mpi-kanban/kanban.md` file without explicit conflict approval.
- Never delete `.claude/mpi-kanban/` automatically after migration.
- Board-shape migrations only insert missing locked columns and convert
  freehand entries the user has explicitly approved. Never reorder entries
  across columns. Never silently delete an unknown column.
- Never overwrite an existing profile or index without showing diff and
  getting approval.
- Memory writes use `AskUserQuestion` before removing or modifying existing
  entries.
- This skill does NOT bootstrap the kanban. Suggest `mpi-init` separately.
- This skill does NOT change project mode after setup. Use
  `mpi-project-mode` for that.

## Related invocations

- `mpi-init` to bootstrap the kanban board.
- `mpi-project-mode` to change mode later.
- `mpi-project-refresh` when the profile or index drifts.




