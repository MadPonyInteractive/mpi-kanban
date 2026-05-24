---
name: mpi-project-refresh
description: MPI workflow pack - Audit and propose updates when repository reality drifts from the MPI project profile, knowledge index, rules, memory pointers, important commands, architecture summary, or conventions. Also performs a lightweight mode reassessment. Use when the user says "MPI project refresh", "refresh project knowledge", "audit project profile", "re-evaluate project knowledge", "the profile is stale", "$mpi-project-refresh", or "/mpi-project-refresh".
---

# mpi-project-refresh Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Detect drift between project knowledge artifacts and current repository
reality. Propose updates and apply them only after user approval. Includes
a lightweight mode reassessment.

Refresh is on-demand. `mpi-end-session` runs the lightweight version for
session-touched files only; this skill runs the full audit.

Invocation: Use the installed Agent Skills invocation for this agent, or ask naturally.

## Required reading

- `<mpi-lib-root>/project-knowledge/updates.md` - approval,
  preservation, drift detection rules.
- `<mpi-lib-root>/project-knowledge/adoption.md` - classification
  vocabulary for any newly discovered sources.
- `<mpi-lib-root>/project-knowledge/indexing.md` - context-budget
  rules.
- `<mpi-lib-root>/project-intent/modes.md` - mode contracts for
  the reassessment step.

<HARD-GATE>
Refresh inspects and proposes. It does NOT write to any project file,
rule, or memory entry before the user approves the refresh proposal.
</HARD-GATE>

## Pre-condition

`.agents/mpi-kanban/project-profile.md` should exist. If it does not, tell
the user:

```text
No project profile found. Run `mpi-project-setup` first.
```

Stop. Do not bootstrap the profile here.

## Process

### 1. Load current artifacts

Read:

- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`

Skim, do not deep-load every linked file. The audit checks whether linked
files still exist and whether their topics still match the project.

### 2. Drift detection

Per `<mpi-lib-root>/project-knowledge/updates.md`:

- **Profile claims vs repo:**
  - Listed components: do the named directories/files still exist?
  - Architecture summary: still consistent with the codebase shape?
  - Important commands: still valid (script names, package scripts, CLI
    invocations)?
  - `Read First` files: still present?
  - `Open Gaps`: still relevant, or resolved?
- **Index pointers vs repo:**
  - Per topic: do all `Read first`, `Rules`, `Memory` pointers resolve?
  - Renamed/moved files: flag for repointing.
  - New subsystems with no topic block: flag as new topic candidates.
- **Conventions vs repo:**
  - Sample a few changed areas (recent commits or session context). Are
    the documented conventions still followed?
  - If code disagrees with the convention, flag for the user to decide
    which is canonical.
- **Cross-checks:**
  - `AGENTS.md` and/or `CLAUDE.md` still point at the profile/index when
    they did before.
  - Rule files referenced by the index still exist.
  - Memory pointers still resolve.

Cap inspection to a sane budget. Sample, do not enumerate every file. If
the repo is too large for a full audit, say so and narrow scope with the
user.

### 3. Mode reassessment

Announce the current mode and any evidence for or against it. Be brief:

```text
Current mode: <mode>. Evidence:
- For: <one-line bullets>
- Against: <one-line bullets, or "none">
```

If the evidence suggests a different mode, recommend
`mpi-project-mode`. Do NOT change mode from this skill.

### 4. Build the proposal

Single message containing:

1. Drift summary (counts by category: profile, index, conventions, rules,
   memory, agent entrypoints).
2. Per-finding details, one line each, with proposed action:
   - "Profile architecture summary: `src/v1/` renamed to `src/api/` -
     propose one-line fix."
   - "Index topic 'Auth' points at moved file `docs/auth.md` -
     propose repoint to `docs/architecture/auth.md`."
   - "New subsystem at `src/workers/` has no topic block - propose new
     topic 'Workers'."
   - "Convention drift: `tests/` location not consistent with rule
     `.claude/rules/testing.md` - ask user which is canonical."
3. Mode reassessment line (current mode + evidence + recommendation or
   "no change recommended").
4. Newly inspected sources (from `<mpi-lib-root>/project-knowledge/adoption.md`) with
   classification, if any.

End with:

```text
Approve this refresh? Reply "yes" to apply all, "yes except <list>" to
skip some, "change <item>" to adjust, or "no" to discard.
```

### 5. Clarification loop

Same shape as setup: user can ask why a change is proposed, opt out of any
single edit, redirect a finding (e.g., "treat that as historical reference,
not drift"), or defer all writes.

### 6. Apply approved writes

After approval, in order:

1. Update `.agents/mpi-kanban/project-profile.md` per approved findings.
   Bump `last_refresh` to today.
2. Update `.agents/mpi-kanban/project-knowledge-index.md` per approved
   findings. Bump `last_refresh` to today.
3. Apply approved rule file creations or edits per file. ASK before touching
   any `.claude/rules/*.md` per `<mpi-lib-root>/project-knowledge/updates.md`. New rule
   files are appropriate when refresh finds reusable project-specific
   conventions that should be briefable to future agents or workers.
4. Apply approved memory pointer edits. Use `AskUserQuestion` before
   removing or modifying existing memory entries.
5. Apply approved `AGENTS.md` or `CLAUDE.md` pointer edits. Preserve
   existing content; pointer-first additions only.

### 7. Final report

```text
Refresh applied.
- Profile: <change count or "no changes">.
- Index: <change count or "no changes">.
- Rules: <files updated or "none">.
- Memory: <entries updated or "none">.
- Agent entrypoints: <files updated or "none">.
- Mode reassessment: <"no change recommended" or "consider $mpi-project-mode">.
```

## Hard rules

- Inspect first, propose second, write third. No write without approval.
- Never create or edit a rule file without explicit per-file approval.
- Never auto-delete or auto-overwrite a memory entry.
- Never overwrite user-customized sections of the profile/index without
  showing the diff and getting approval.
- Do not change project mode from this skill. Recommend `mpi-project-mode`.
- Refresh does not bootstrap missing artifacts. Recommend
  `mpi-project-setup` if the profile is absent.

## Related invocations

- `mpi-project-setup` to establish missing artifacts.
- `mpi-project-mode` to change mode.
- `mpi-end-session` runs the lightweight refresh for session-touched files.



