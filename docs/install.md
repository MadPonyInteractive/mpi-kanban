# Install Mpi-Kanban

Mpi-Kanban is distributed as an all-or-nothing Agent Skills pack through
skills.sh / `npx skills`.

## Install

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

The `--all` flag is required. The workflow skills depend on the `mpi-lib`
support skill; partial installs are unsupported.

> **Expected output:** `--all` targets every agent the `skills` CLI knows
> about. Some agents (for example `PromptScript`) reject the `-g` global flag
> and show a red `Failed to install` line for each skill. This is normal — the
> pack still installs correctly for every compatible agent. Confirm success by
> checking that the skill folders exist under `~/.agents/skills/` (or, when an
> agent symlinks, `~/.claude/skills/`).

## Update

Run the same command again:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

Restart or reload the agent if it caches skill metadata for the current
session.

## Board Validator

To confirm a project's board is consistent after installing or after a session
ends unexpectedly, run:

```text
python <mpi-lib-root>/scripts/validate_board.py <project-root>
```

Replace `<mpi-lib-root>` with the installed path of the `mpi-lib` skill (for
example `~/.agents/skills/mpi-lib`). `<project-root>` defaults to the current
directory. A project with no `board.json` is not an error. Exit 0 means the
board is consistent; exit 1 prints one line per violation.

## Agent Notes

Different agents expose installed skills differently. Use the native Agent
Skills invocation for your tool, or ask naturally:

```text
what is MPI-5?
set MPI-5 to validating
continue this MPI plan
read inbox
tell another agent
create an MPI handoff
run MPI cleanup
```

The skill folders install under Agent Skills directories such as
`~/.agents/skills/`, `.agents/skills/`, `~/.claude/skills/`, or
`.claude/skills/` depending on agent and install scope.

## Board Files

Mpi-Kanban uses one Kanban root per work context, not one board per folder. A
work context can be a single project folder or a VS Code `.code-workspace`.
When a `.code-workspace` is active, its `folders` entries define the member
folders that share the same board, coordination state, and message inbox.

New projects use a JSON task board:

```text
.agents/mpi-kanban/board.json
.agents/mpi-kanban/events.jsonl
.agents/mpi-kanban/tasks/<id>/task.json
```

The fixed human columns are `To do`, `Doing`, and `Done`, stored in JSON as
`todo`, `doing`, and `done`. Task IDs are system-assigned visible IDs such as
`MPI-42`; use those IDs when asking an agent to show, continue, or inspect
work. Read-only card questions such as `what is MPI-42?` route through
`mpi-continue` without starting implementation.

Direct card-state requests such as `move MPI-42 to doing`, `set MPI-42 to
validating`, or `mark MPI-42 done` also route through `mpi-continue`. A
validating card stays in `doing`, writes or updates `validation.md` first, and
uses `maturity: "validating"`. A done move requires represented validation
state and explicit final-completion approval.

Task-card `maturity` is also fixed, scoped per column: `todo` uses `idea`,
`planned`, `research`, `needs-decision`, `blocked`, or `deferred`; `doing` uses
`in-progress` or `validating`; `done` uses `complete` or `rejected`. Do not use
process labels such as `Validated`, `spec`, `active`, `done`, or `implementing`
as maturity values; the VS Code board treats unknown values as invalid cards.

Legacy projects may still contain `.agents/mpi-kanban/kanban.md` or
`.claude/mpi-kanban/kanban.md`. Treat those files as migration inputs or
snapshots after `board.json` exists, not as a second live board. Prefer moving
the old Markdown file under `.agents/mpi-kanban/legacy/`; if it must remain at
the old path, keep a strong tombstone/header and never route active boot docs
through it.

Do not assume sibling folders are part of the same work context. If an agent
needs a related folder that is outside the active `.code-workspace`, add it to
the workspace before sharing this board. If it should remain independent, keep
its own Kanban root and use only explicit same-machine peer messages between
the two roots.

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
