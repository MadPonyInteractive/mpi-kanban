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
continue this MPI plan
create an MPI handoff
run MPI cleanup
```

The skill folders install under Agent Skills directories such as
`~/.agents/skills/`, `.agents/skills/`, `~/.claude/skills/`, or
`.claude/skills/` depending on agent and install scope.

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
