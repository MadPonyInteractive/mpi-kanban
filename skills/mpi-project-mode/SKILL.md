---
name: mpi-project-mode
description: Review, reaffirm, or change the MPI project mode (prototype, mvp, scalable-foundation) without rerunning setup. Records mode rationale and notes prior-mode shortcuts. Use when the user says "MPI project mode", "change project mode", "switch to scalable-foundation", "we are now MVP", "show me the project mode", "$mpi-project-mode", or "/mpi-kanban:mpi-project-mode".
---

# mpi-project-mode Skill

## Purpose

Review, reaffirm, or change the project mode recorded in
`.agents/mpi-kanban/project-profile.md`. Mode controls planning depth,
acceptable shortcuts, reuse expectations, and clarification behavior. Mode
changes do NOT force a rewrite; they shape future work and record
migration notes.

Invocation: Claude Code users may run `/mpi-kanban:mpi-project-mode`; Codex
users may run `$mpi-project-mode` or ask naturally. References using
`${CLAUDE_PLUGIN_ROOT}` mean the installed plugin root.

## Required reading

- `${CLAUDE_PLUGIN_ROOT}/lib/project-intent/modes.md` - mode contracts and
  defaults.
- `${CLAUDE_PLUGIN_ROOT}/lib/project-knowledge/profile-schema.md` - profile
  fields the skill edits (`mode`, `mode_rationale`, `mode_source`,
  `## Mode Notes`).
- `${CLAUDE_PLUGIN_ROOT}/lib/project-knowledge/updates.md` - approval rules.

## Pre-condition

The project profile must exist at
`.agents/mpi-kanban/project-profile.md`. If it does not, tell the user:

```text
No project profile found at .agents/mpi-kanban/project-profile.md.
Run $mpi-project-setup in Codex or /mpi-kanban:mpi-project-setup in
Claude Code first.
```

Stop. Do not create the profile from this skill.

## Process

### 1. Read current mode

Read the profile frontmatter. Report:

```text
Current mode: <mode>
Rationale: <mode_rationale>
Source: <mode_source>
Last refresh: <last_refresh>
```

If `## Mode Notes` exists, list the most recent two entries.

### 2. Ask intent

```text
Do you want to:
1. reaffirm the current mode (no changes)
2. change to a different mode
3. just review (no changes)
```

For option 1 or 3, no write happens. For option 1, update `mode_rationale`
to a fresh dated note if the user provides one. Otherwise skip.

### 3. Mode change flow (option 2)

Ask which mode and why:

```text
Switch to which mode? (prototype, mvp, scalable-foundation)
Reason in one line:
```

Summarize behavior changes from `lib/project-intent/modes.md` for the new
mode in 3-6 bullets so the user sees what shifts. Confirm:

```text
Switch mode to <new mode>? This updates future work behavior; it does not
rewrite existing code. Reply "yes" to apply.
```

### 4. Record migration notes

When changing modes (especially `prototype` -> `mvp` or
`mvp` -> `scalable-foundation`), prompt:

```text
Are there shortcuts or technical debt from the prior mode you want recorded
in the project profile `## Open Gaps`? (list them or "none")
```

For downgrades (`scalable-foundation` -> `mvp`, etc.), prompt for the
reason and record it in `## Mode Notes` along with the dated transition.

### 5. Apply approved writes

After approval:

1. Edit profile frontmatter: `mode`, `mode_rationale`, `mode_source` =
   `user`, and bump `last_refresh` to today.
2. Append a dated bullet to `## Mode Notes`:
   ```markdown
   - <YYYY-MM-DD>: <new mode>. <one-line note: behavior change and any
     migration context>.
   ```
3. Append any shortcuts/debt to `## Open Gaps` if the user listed them.

### 6. Final report

Output:

```text
Mode: <old mode> -> <new mode> (or reaffirmed).
Profile updated: .agents/mpi-kanban/project-profile.md
Migration notes: <count> entries added to ## Open Gaps (or "none").
```

Suggest `mpi-project-refresh` if the mode change implies wider profile/index
drift the user wants to review now. Do not run refresh automatically.

## Hard rules

- Mode change requires explicit approval before any write.
- Mode change never rewrites code or files outside the profile.
- Do not edit profile sections outside the mode-related fields and the two
  appended bullets.
- Do not create the profile from this skill. Use `mpi-project-setup` first.

## Related invocations

- `mpi-project-setup` to establish the profile.
- `mpi-project-refresh` to audit profile/index drift.
