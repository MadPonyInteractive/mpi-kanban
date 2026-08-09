# Install Mpi-Kanban

Mpi-Kanban is a Claude Code plugin. Skills, enforcement hooks, and agents all
ship from one manifest, so there is nothing to install per component.

Installing registers twelve workflow skills, the `mpi-lib` support skill, six
hooks, and two read-only agents.

## Remove the pre-1.0 skills pack first

Releases before 1.0 installed as an all-or-nothing Agent Skills pack. Plugin
skills are namespaced (`mpi-kanban:mpi-continue`), so they cannot collide by
name - but both sets load their descriptions, and those descriptions carry the
same trigger phrases. With both installed the agent sees two skills matching
"continue MPI-42", one of them running the pre-1.0 contract. Remove the old
pack before installing the plugin.

Remove the symlinks first, then the real directories:

```powershell
$pack = "mpi-archive","mpi-brainstorm","mpi-brief-rule","mpi-cleanup",
        "mpi-continue","mpi-create-large-plan","mpi-create-plan",
        "mpi-end-session","mpi-execute-parallel","mpi-handoff","mpi-init",
        "mpi-lib","mpi-message","mpi-nimbalyst-sync","mpi-project-refresh"
foreach ($n in $pack) {
  Remove-Item -Recurse -Force "$HOME/.claude/skills/$n" -ErrorAction SilentlyContinue
  Remove-Item -Recurse -Force "$HOME/.agents/skills/$n" -ErrorAction SilentlyContinue
}
```

```bash
for n in mpi-archive mpi-brainstorm mpi-brief-rule mpi-cleanup mpi-continue \
         mpi-create-large-plan mpi-create-plan mpi-end-session \
         mpi-execute-parallel mpi-handoff mpi-init mpi-lib mpi-message \
         mpi-nimbalyst-sync mpi-project-refresh; do
  rm -rf "$HOME/.claude/skills/$n" "$HOME/.agents/skills/$n"
done
```

Those 15 names are the whole pack. **Delete nothing else.** Projects commonly
hold their own project-scope skills with `mpi-` names - `mpi-end`,
`mpi-release`, `mpi-version-bump` and similar. Those are yours, not the pack's.

`mpi-init` and `mpi-project-refresh` both check for leftovers and report them as
a blocking finding with the removal commands, so a second machine cannot miss
this.

## Install

```text
/plugin marketplace add MadPonyInteractive/mpi-kanban
/plugin install mpi-kanban@mad-pony-interactive
```

## Update

```text
/plugin update mpi-kanban@mad-pony-interactive
```

### Which version is installed

The plugin ships exactly one version stamp: the `version` field in
`.claude-plugin/plugin.json`. `/plugin list` shows it, and
`mpi-project-refresh` prints it in every report and warns when the install is
older than the version the project last recorded. That comparison is against
the project, not the network, so it catches a downgrade or a second machine
running an old install - not "a newer release exists upstream".

## What the hooks do to your session

The hooks register on install and start guarding immediately. In a project with
no `.agents/mpi-kanban/board.json` every one of them exits without doing
anything, so installing the plugin does not change how an un-adopted project
behaves. In an adopted project, expect these blocks:

- Destructive git - `git checkout -- <path>`, `git checkout .`, `git restore`
  without `--staged`, destructive `git stash`, `git reset --hard`, and
  `git clean -f/-d/-x` are refused. Branch operations are not.
- No card - editing code outside `.agents/` with no card in `doing` is refused
  once, and the message carries the card contract so the card can be created on
  the spot.
- A second card in one session - refused, so the finding is folded into the
  active card or justified in one line. An approved second card passes on retry.
- A claimed path - writing a file another live session has claimed is refused.
- Heredocs and multi-line escaped shell strings - refused; use a script file or
  a single-quoted `python -c`.

Every block prints its reason. None of them fail silently. If a hook is in your
way, the message names what to do instead.

## Board Validator

To confirm a project's board is consistent after installing or after a session
ends unexpectedly, run:

```text
python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/validate_board.py" <project-root>
```

`${CLAUDE_PLUGIN_ROOT}` resolves inside skill and agent content; from a plain
terminal, use the install path `/plugin list` reports. `<project-root>`
defaults to the current directory. A project with no `board.json` is not an
error. Exit 0 means the board is consistent; exit 1 prints one line per
violation.

## Invoking the skills

Ask naturally, or use the namespaced skill name:

```text
what is MPI-5?
set MPI-5 to validating
continue this MPI plan
run the ready cards
read inbox
MPI end session
create an MPI handoff
run MPI cleanup
```

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

Pre-1.0 releases installed as an Agent Skills pack; releases before that
used plugin packaging. Remove whichever you have before installing, per
[Remove the pre-1.0 skills pack first](#remove-the-pre-10-skills-pack-first).

If a very old plugin install is still registered:

```text
/plugin uninstall mpi-kanban@mad-pony-interactive --scope user
```

If the project was already running the pre-1.0 pack, it almost certainly grew
local scaffolding to work around gaps 1.0 closes - a close-out wrapper skill, a
copy of the destructive-git hook, rules restating contracts that are now
enforced. [migrating-to-1.0.md](migrating-to-1.0.md) is the checklist, and
`mpi-project-refresh` audits all of it under its **1.0 migration** category.

After installing in a project, run `mpi-init`. It is the single onboarding
entrypoint: it creates or migrates the JSON board, writes the project profile
and knowledge index, records project mode, and can import a freeform backlog.
Use `mpi-project-refresh` later for maintenance, drift updates, and project
mode changes.
