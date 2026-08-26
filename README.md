# Mpi-Kanban

A Claude Code plugin that lets multiple AI agents work side by side on the
same project - even on the same files - without overwriting each other.
Agents share a live coordination state so one can implement while another
reviews, verifies, or integrates, and a visible JSON task board keeps you in
the loop on what every agent is doing. Bundles the full MPI workflow (brainstorm,
plan, continue, parallel execution, handoff, end session, cleanup) so a single
session or a whole team of agents can pick up work, coordinate file ownership,
and ship together.

Fourteen workflow skills: `mpi-init`, `mpi-project-refresh`, `mpi-brainstorm`,
`mpi-create-plan`, `mpi-create-large-plan`, `mpi-continue`,
`mpi-execute-parallel`, `mpi-message`, `mpi-umbrella`, `mpi-handoff`,
`mpi-end-session`, `mpi-cleanup`, `mpi-archive`, `mpi-brief-rule` - plus the
support skill `mpi-lib`, six enforcement hooks, and two read-only agents.

## Install

```text
/plugin marketplace add MadPonyInteractive/mpi-kanban
/plugin install mpi-kanban@mad-pony-interactive
```

> **Upgrading from the pre-1.0 skills pack?** Remove it first, or every
> request matches two skills and one of them runs the old contract.
> [docs/install.md](docs/install.md) leads with the removal commands.

## Update

```text
/plugin update mpi-kanban@mad-pony-interactive
```

The version is the `version` field in `.claude-plugin/plugin.json`; `/plugin
list` shows it. `mpi-project-refresh` reports it too, and flags an install
older than the one the project last recorded. See
[docs/install.md](docs/install.md).

## Use

Natural language is the intended interface:

```text
brainstorm with me
initialize MPI
what is MPI-5?
show the Agent Message Bus card
set MPI-5 to validating
create a plan
create a large plan
continue this MPI plan
run the ready cards
read inbox
tell another agent
refresh MPI
MPI end session
create an MPI handoff
run MPI cleanup
```

Direct invocation depends on the agent. Use the Agent Skills invocation surface
your tool provides, such as `mpi-continue`, `/mpi-continue`, or an equivalent
skill command.

## Task Board

Mpi-Kanban uses one Kanban root per work context, not one board per folder. In a
single-folder project, that work context is the project folder. In a VS Code
multi-root workspace, the active `.code-workspace` file defines the member
folders that share one board, coordination state, and same-filesystem message
inbox.

The primary board is a small JSON index:

```text
.agents/mpi-kanban/board.json
```

It has three fixed human columns: `To do`, `Doing`, and `Done`. Each card has a
system-assigned visible ID such as `MPI-42`, and its detailed workspace lives
under:

```text
.agents/mpi-kanban/tasks/MPI-42/
```

Task folders keep the card compact: `task.json` stores the visible metadata,
while `brief.md`, `plan.md`, `checklist.md`, `validation.md`, `files.json`,
`events.jsonl`, `handoffs/`, and `research/` hold the work detail.

Task-card `maturity` is a fixed enum, scoped per column: `todo` uses `idea`,
`planned`, `research`, `needs-decision`, `blocked`, or `deferred`; `doing` uses
`in-progress` or `validating`; `done` uses `complete` or `rejected`. Values like
`Validated`, `spec`, `active`, `done`, or `implementing` are not maturity values
and will render as invalid cards; keep that detail in the task workspace or
`status` instead.

Ask `what is MPI-42?`, `show MPI-42`, or `look at the <title> card` to trigger
`mpi-continue`'s read-only mode. It reads one card and its direct task-folder
context without starting implementation.

Ask `move MPI-42 to doing`, `set MPI-42 to validating`, or `mark MPI-42 done`
to trigger `mpi-continue`'s direct card-state update mode. The skill reads the
task-board schema before writing; `validating` means the card stays in `Doing`,
`validation.md` is written or updated first, and `maturity` becomes
`validating`. `Done` still requires represented validation state and explicit
final-completion approval.

The companion **Mpi-Kanban** VS Code extension renders the board as an
interactive task surface:

- Marketplace ID: `MadPonyInteractive.mpi-kanban`
- Repository: <https://github.com/MadPonyInteractive/mpi-kanban-vscode>
- Extension page: <https://marketplace.visualstudio.com/items?itemName=MadPonyInteractive.mpi-kanban>

![Mpi-Kanban board in VS Code](./imgs/board.png)

To open the board, press `Ctrl+Shift+P` (`Cmd+Shift+P` on macOS) and run
**Mpi-Kanban: Open Mpi-Kanban Board**.

If a related repository is not listed in the active `.code-workspace`, agents
should not silently treat it as part of the same work context. Add that folder
to the workspace when it should share the board, or keep it as a separate
Kanban root and route only explicit same-machine peer messages between roots.

Legacy projects may still contain `.agents/mpi-kanban/kanban.md`. That file is
kept for migration or snapshots; once `board.json` exists, workflows should not
maintain both files as live sources of truth.

After migration, prefer moving the old Markdown board to
`.agents/mpi-kanban/legacy/`. If the old path must remain for compatibility,
keep only a tombstoned/generated file there and update project boot docs so
agents continue from `board.json` and `tasks/<id>/`.

## Board Validator

The `mpi-lib` support skill ships a runnable script that validates any
project's live JSON task board:

```text
python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/validate_board.py" <project-root>
```

`${CLAUDE_PLUGIN_ROOT}` resolves inside skill and agent content; from a plain
terminal use the install path `/plugin list` reports.
`<project-root>` is the project directory containing
`.agents/mpi-kanban/board.json`; it defaults to the current directory.
A project with no `board.json` is not an error.

The script checks board schema, the fixed column set, card/column and
maturity-enum coherence, required task fields, link paths, orphaned task
folders, and board-level and task-level event logs. Exit 0 means the board
is consistent; exit 1 prints one line per violation. `mpi-end-session` runs
this check automatically before committing.

## Board In A Browser

The companion VS Code extension is one way to see a board. The other is a small
read-only server, for a harness with no webview:

```text
python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/board_server.py" <project-root>
```

`<project-root>` defaults to the current directory. Open the printed URL -
`http://localhost:7337` - in the Claude Code browser pane, in Chrome, or in
both at once.

Run the same command from a second project and it registers that one into the
server already running rather than fighting for the port, so one address holds
every board and each gets a tab. The port is pinned and never auto-picked: the
address is a bookmark. Pass `--port` to move it, `--forget` to drop a project
registered by mistake.

Start it once from a terminal and leave it up - it outlives sessions, which is
the point when several projects share it. The page polls every two seconds, so a
card moved by `mpi-continue` appears without a reload, in every browser watching.

The registry of projects lives at `~/.mpi-kanban/boards.json`, machine-global
for the same reason a GPU lease is: a record spanning repos cannot live in one.
It is a list of paths and nothing else - the server never writes to a board, and
moving a card stays `mpi-continue`'s job.

## Workflow

The normal loop is:

```text
brainstorm -> create-plan/create-large-plan -> continue -> end-session -> cleanup
```

- `mpi-brainstorm` explores an idea and can capture it as a `todo` task.
- `mpi-create-plan` creates compact plans for normal work.
- `mpi-create-large-plan` creates phased/adaptive plans and explicit parallel
  batches when work can be split safely.
- `mpi-continue` resumes from the current task ID, plan, handoff, board state,
  and repo state; it claims files before editing.
- `mpi-execute-parallel` executes parallel batches and dispatches the ready
  cards on the board.
- `mpi-umbrella` folds related board cards into one umbrella card. Ask it to
  group named cards, or to review the board and propose the clusters.
- `mpi-handoff` switches sessions. It commits, pushes, writes a handoff JSON
  under `.agents/mpi-kanban/state/handoffs/`, and prints a paste-ready resume
  block - typically under two minutes, because it reads the running notes
  `mpi-continue` keeps in the plan instead of summarising the session.
- `mpi-end-session` is close-out for finished work: rules, docs, memory,
  knowledge healing, the `validating` sweep, commit, and closing the card. It
  runs once per job, not once per session.
- `mpi-cleanup` proposes conservative cleanup for old workflow artifacts.

Board lifecycle is `To do -> Doing -> Done`. Planning, checklists, validation,
attention, and handoffs live in the task workspace instead of being embedded in
card bodies.

## Enforcement

Six hooks ship with the plugin and register themselves on install. They replace
rules that used to be prose, and prose rules were fired through. Every hook is a
no-op in a project with no `.agents/mpi-kanban/board.json`, and every block
prints the reason - none of them fail silently.

| Hook | Fires on | Blocks |
| --- | --- | --- |
| `guard-git` | `Bash` | `git checkout -- <path>`, `git checkout .`, `git restore` without `--staged`, destructive `git stash`, `git reset --hard`, `git clean -f/-d/-x`. `checkout -b`, branch switches, `restore --staged` and read-only `stash` subcommands pass. |
| `guard-card` | `Edit`, `Write`, `Bash` | Editing code with no card in `doing`, and creating a second card in one session. The block message carries the card contract inline and names the file, so ownership is seeded from the real first touch. An approved second card passes on retry. |
| `guard-claim` | `Edit`, `Write`, `Bash` | Writing a path another live session has claimed. Reads both `path` and `paths` claim shapes. |
| `guard-shell` | `Bash` | Heredocs and multi-line escaped strings. Use a script file or a single-quoted `python -c`. |
| `guard-gpu` | `Bash` | A GPU command not routed through `gpu_lease.py`. Off until the project sets `gpu_command_patterns`. |
| `session-start` | session start | Nothing - reports open claims, unresolved messages, active handoffs, and `doing` cards, so coordination no longer depends on typing a command. |
| `precompact-handoff` | before compaction | Nothing - offers a handoff before context is auto-compacted. |

`guard-card` and `guard-claim` watch `Bash` as well as the edit tools, because a
guard that only watches `Edit` and `Write` is bypassed by `sed -i`, a `>`
redirect, `tee`, `cp` or `mv` - and some harness modes tell the agent to prefer
exactly those. They read the written path out of the command; a write hidden
inside `python -c` or an interpreted script is still invisible to them.

## Dispatch

`mpi-continue` evaluates dispatch on every start. When the ready work splits
into two or more disjoint file sets that are each independently verifiable, it
dispatches workers and announces the split rather than asking first. It greps
the real file footprint instead of trusting `files.json`, builds a conflict
graph, dispatches at most four workers, and reports every card it excluded with
the reason. Ownership is written at `todo -> doing`, where it is knowable.

Two read-only agents ship with the plugin:

- `dispatcher` - plans the split. Read-only, so it cannot clobber a worker.
- `claim-auditor` - runs at close-out. Extracts every factual assertion from the
  changelog, release notes, and cards closed this cycle, finds the commit and
  source line proving each, and classifies them PROVEN / UNPROVEN / FALSE /
  OVERSTATED, worst first, capped at 40 lines.

## Project Knowledge

Mpi-Kanban can maintain durable project knowledge:

- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`

Two skills own the lifecycle:

- `mpi-init` is the one-time onboarding/adoption skill. Run it once per project.
  It creates or migrates the JSON board, establishes project knowledge, and
  records the project mode. If the project is already initialized, it stops and
  points you to `mpi-project-refresh`.
- `mpi-project-refresh` is the ongoing maintenance skill for an already-adopted
  project. It audits drift, updates project knowledge, changes the project mode,
  and proposes migration of any legacy `kanban.md` board files that still need
  JSON migration, snapshot cleanup, tombstoning, or stale boot-doc pointer
  repairs.

There are no separate `mpi-project-setup` or `mpi-project-mode` skills. Setup
folded into `mpi-init`; mode review and changes folded into
`mpi-project-refresh`.

## Coordination

Agents coordinate through `.agents/mpi-kanban/state/`:

- `index.json` is the first file agents read.
- Sessions record role and heartbeat.
- Coordination tasks connect agent sessions to a plan and task-board item.
- File claims are active write locks.
- Handoffs preserve state for a fresh session.

Task-card badges and attention state are display summaries only. The
coordination state is the source of truth for agent ownership and handoffs.

Workspace-aware records can disambiguate files with a workspace folder alias,
resolved folder root, and path relative to that folder. Shared reference details
for `.code-workspace` discovery live in
`skills/mpi-lib/workspace-ops/discovery.md`.

### What claims can and cannot lock

File claims are enforced locally: the `guard-claim` hook blocks a write to a
path another live session has claimed, on every edit, whether or not a skill
was invoked. Within one Claude Code session and the workers it dispatches,
that is a real lock.

Across two independently launched Claude Code windows it is advisory. Nothing
can make it otherwise - there is no native cross-session file lock on any
platform, and cross-session messaging is not available everywhere. Two windows
share the same `state/` directory and will both see a claim, but neither can
stop the other's process. Prefer one session dispatching workers over N
windows editing the same repo.

### GPU leases

A GPU is the exception to the paragraph above, and it needs one: agents in
different repos running sweeps on the same card corrupt each other's results
silently. Claims cannot cover it - they live in one repo's `state/`, key on
paths, and bind on writes, and two agents in two repos share no file at all.

So the GPU lease is machine-global, and its lock is the kernel's:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/gpu_lease.py" run -- python sweep.py
python "${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/gpu_lease.py" status
```

`run` takes a free device under an OS exclusive lock held for the lifetime of
the command, sets `CUDA_VISIBLE_DEVICES` for the child, and waits when every
device is busy. Run it as a background Bash call and the waiting costs no
tokens. This is a real lock across sessions, repos, and windows - unlike a file
claim, because the kernel is enforcing it rather than a cooperating agent.

There is no release step. The lock drops when the command exits, including on
crash or kill, so there is no heartbeat to tune and no stale lease to reclaim.

Devices come from `nvidia-smi`. An onboard Intel or AMD adapter never becomes a
slot, so no agent is handed a GPU too weak to run on, and a machine with no
NVIDIA device runs the command unleased. More GPUs simply means more slots.

Enforcement is opt-in per project - see `gpu_command_patterns` below.

## Per-Project Config

For rule briefings and worker bundles, create `.agents/mpi-kanban.local.md`
using the template at
`skills/mpi-brief-rule/templates/mpi-kanban.local.md`.

The same file turns on GPU lease enforcement. It stays off until you list the
commands that need a device:

```yaml
gpu_command_patterns:
  - python .*(train|sweep|generate)
  - pytest .*-m gpu
```

Each entry is a regex matched against the raw Bash command. Keep them narrow -
a pattern that catches your whole test suite blocks work that never touches the
GPU. Leave the list empty in projects with no GPU contention.

## Migration

Releases 0.7 through 0.10 installed as an all-or-nothing Agent Skills pack.
Remove those 15 skill folders before installing the plugin - see
[docs/install.md](docs/install.md), which leads with the removal.

A repo that ran the pre-1.0 pack also carries local scaffolding for gaps 1.0
closes - a close-out wrapper skill, a copy of the destructive-git hook, rules
restating contracts hooks now enforce. See
[docs/migrating-to-1.0.md](docs/migrating-to-1.0.md), or run
`mpi-project-refresh` and let it propose each removal with its diff.

**Removed skills.** `mpi-nimbalyst-sync` is gone. The separate
`mpi-project-setup` and `mpi-project-mode` skills no longer exist. Use `mpi-init` for onboarding/adoption and
`mpi-project-refresh` for maintenance and mode changes. Update any saved
commands or scripts that referenced the old skill names.

**Projects not yet on Mpi-Kanban.** For a project never adopted into the JSON
board, run `mpi-init` after updating. (If the project still has a legacy
`.claude/mpi-kanban/` or `.agents/mpi-kanban/kanban.md` Markdown board,
`mpi-init` proposes a one-time JSON migration without overwriting current files
or deleting legacy directories.)

**Projects already on the JSON board.** For a project that already has a
`board.json` but still carries legacy drift (old `kanban.md` snapshots, stale
profile/index, outdated mode), run `mpi-project-refresh`. It proposes the
migration and knowledge updates without re-running onboarding.

If a workflow skill cannot find `mpi-lib`, the plugin install is broken;
reinstall it.

## Development

- [SPEC.md](SPEC.md) is the design source of truth.
- [PLAN.md](PLAN.md) tracks implementation phases.
- Run `python scripts/validate_plugin.py` before release.
- Test this checkout without installing it: `claude --plugin-dir .`.
- Validate the manifest with `claude plugin validate . --strict`.
- Release by tagging and pushing; `.github/workflows/release.yml` builds the
  GitHub Release from `CHANGELOG.md`.

## License

MIT - see [LICENSE](LICENSE).
