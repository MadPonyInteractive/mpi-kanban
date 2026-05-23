---
name: mpi-project-setup
description: Establish durable MPI project knowledge. Ask for project mode, inspect existing docs/rules/memory, propose an adoption map, and create or update the project profile, knowledge index, agent entrypoint pointers, rule files, and memory pointers after explicit user approval. Use when the user says "MPI project setup", "set up project knowledge", "adopt this project", "create a project profile", "$mpi-project-setup", or "/mpi-kanban:mpi-project-setup", or right after `mpi-brainstorm` for a brand-new project.
---

# mpi-project-setup Skill

## Purpose

Establish project knowledge an agent can rely on across sessions. Sets the
project mode, adopts existing docs/rules/memory, and writes a compact
pointer-driven profile and knowledge index.

This skill does NOT bootstrap the kanban board. The board is `mpi-init`'s
job. Setup may suggest running `mpi-init` afterward if no board exists, but
the two skills stay separate.

Invocation: Claude Code users may run `/mpi-kanban:mpi-project-setup`; Codex
users may run `$mpi-project-setup` or ask naturally. References using
`${CLAUDE_PLUGIN_ROOT}` mean the installed plugin root.

## Required reading

Read each only when its section is needed:

- `${CLAUDE_PLUGIN_ROOT}/lib/project-intent/modes.md` - mode contracts and
  default-mode rule.
- `${CLAUDE_PLUGIN_ROOT}/lib/project-knowledge/profile-schema.md` - profile
  shape.
- `${CLAUDE_PLUGIN_ROOT}/lib/project-knowledge/index-schema.md` - index
  shape.
- `${CLAUDE_PLUGIN_ROOT}/lib/project-knowledge/adoption.md` - source list,
  classification, conflict handling.
- `${CLAUDE_PLUGIN_ROOT}/lib/project-knowledge/indexing.md` - context-budget
  rules.
- `${CLAUDE_PLUGIN_ROOT}/lib/project-knowledge/updates.md` - approval and
  preservation rules.

<HARD-GATE>
Do NOT write or modify any project file (profile, index, AGENTS.md, rules,
memory) before the user approves the setup proposal. Inspection and
proposal are safe; writes require explicit approval.
</HARD-GATE>

## Process

### 1. Detect new vs existing project

A project is "existing" if at least one of these is present: `README.md`
with content, `src/`, `AGENTS.md`, `CLAUDE.md`, `.claude/rules/`, `docs/`,
or any source-code directory the user names. Otherwise treat as new.

State which mode the skill is in: `new project setup` or
`existing project setup`. Ask the user to confirm if uncertain.

### 2. Ask for project mode

Per `lib/project-intent/modes.md`:

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

Per `lib/project-knowledge/adoption.md`, inspect:

- `AGENTS.md`, `CLAUDE.md`
- `.claude/rules/*.md`
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

### 5. Build the adoption map

Classify each inspected source per `lib/project-knowledge/adoption.md`:
`usable as-is`, `small update`, `index pointer`, `convert to MPI-managed`,
`superseded historical reference`, `conflict / uncertain`.

When no `.claude/rules/*.md` files exist, do not treat that as "rules out of
scope." Decide whether any discovered project-specific conventions are better
stored as:

- short bullets in `.agents/mpi-kanban/project-profile.md`;
- pointers to existing docs; or
- a proposed new `.claude/rules/<topic>.md` file when the convention is
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
6. Any rule file changes proposed, including new `.claude/rules/*.md` files or
   edits to existing rules (per file, one-line summary and purpose).
7. Any memory pointers proposed (existing Claude memory preferred; new
   memory entries called out explicitly).
8. Any deferred items the user should know about.

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
   `${CLAUDE_PLUGIN_ROOT}/templates/project-profile.md` template as the
   base, filled in from the approved draft. Set `setup_date` and
   `last_refresh` to today.
3. Write `.agents/mpi-kanban/project-knowledge-index.md` from the
   `${CLAUDE_PLUGIN_ROOT}/templates/project-knowledge-index.md` template.
4. Create or update `AGENTS.md` if approved. Pointer-first: add a short
   `## Project Knowledge` section that links to the profile and index.
   Preserve existing content; do not rewrite the file.
5. Apply approved rule file creations or edits per file. Each file should be
   concise and include a `## Sub-Agent Briefing` section when it is intended
   for `mpi-brief-rule` or parallel worker briefings.
6. Apply approved memory pointer entries.
7. Confirm: state which files were written, link them, and suggest the next
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
- Creating `.claude/rules/*.md` is allowed during setup when the approved
  proposal identifies reusable project-specific conventions that do not already
  have a good home.
- Never create or edit `.claude/rules/*.md` without explicit per-file approval.
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
