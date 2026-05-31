# Install Mpi-Kanban

Mpi-Kanban is distributed as an all-or-nothing Agent Skills pack through
skills.sh / `npx skills`.

## Install

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

The `--all` flag is required. The workflow skills depend on the `mpi-lib`
support skill; partial installs are unsupported.

## Update

Run the same command again:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

Restart or reload the agent if it caches skill metadata for the current
session.

## Agent Notes

Different agents expose installed skills differently. Use the native Agent
Skills invocation for your tool, or ask naturally:

```text
what is MPI-5?
continue this MPI plan
create an MPI handoff
run MPI cleanup
```

The skill folders install under Agent Skills directories such as
`~/.agents/skills/`, `.agents/skills/`, `~/.claude/skills/`, or
`.claude/skills/` depending on agent and install scope.

## Board Files

New projects use a JSON task board:

```text
.agents/mpi-kanban/board.json
.agents/mpi-kanban/events.jsonl
.agents/mpi-kanban/tasks/<id>/task.json
```

The fixed human columns are `To do`, `Doing`, and `Done`, stored in JSON as
`todo`, `doing`, and `done`. Task IDs are system-assigned visible IDs such as
`MPI-42`; use those IDs when asking an agent to show, continue, or inspect
work.

Legacy projects may still contain `.agents/mpi-kanban/kanban.md` or
`.claude/mpi-kanban/kanban.md`. Treat those files as migration inputs or
snapshots after `board.json` exists, not as a second live board. Prefer moving
the old Markdown file under `.agents/mpi-kanban/legacy/`; if it must remain at
the old path, keep a strong tombstone/header and never route active boot docs
through it.

## Migration From Old Installs

Older releases used Claude Code and Codex plugin packaging. Those install
surfaces are removed in the universal skills release.

For old Claude plugin installs, uninstall the plugin package, then install the
skills pack:

```text
/plugin uninstall mpi-kanban@mad-pony-interactive --scope user
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

For old Codex plugin installs, remove the old Codex plugin registration/cache
through Codex's normal plugin removal flow, then install the skills pack:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

If a workflow skill reports that it cannot find `mpi-lib`, reinstall with the
full command above.

After installing in a project, run `mpi-init`. It is the single onboarding
entrypoint: it creates or migrates the JSON board, writes the project profile
and knowledge index, records project mode, and can import a freeform backlog.
Use `mpi-project-refresh` later for maintenance, drift updates, and project
mode changes.

## Nimbalyst Interop

Nimbalyst interop uses `.agents/mpi-kanban/state/interop.json` to decide which
system is canonical:

- `file` mode: MPI updates `.agents/mpi-kanban/board.json`, task folders, and
  passive event logs.
- `nimbalyst` mode: Nimbalyst trackers/sessions are canonical and MPI board
  updates happen only through explicit `mpi-nimbalyst-sync` import/export
  snapshots.

Use `mpi-nimbalyst-sync detect` before switching modes. The skill prompts before
changing source of truth.
