# Mpi-Kanban

An Agent Skills pack that lets multiple AI agents work side by side on the
same project - even on the same files - without overwriting each other.
Agents share a live coordination state so one can implement while another
reviews, verifies, or integrates, and a visible JSON task board keeps you in
the loop on what every agent is doing. Bundles the full MPI workflow (brainstorm,
plan, continue, parallel execution, handoff, end session, cleanup) so a single
session or a whole team of agents can pick up work, coordinate file ownership,
and ship together.

Skills: `mpi-init`, `mpi-project-refresh`, `mpi-brainstorm`,
`mpi-create-plan`, `mpi-create-large-plan`, `mpi-continue`,
`mpi-execute-parallel`, `mpi-message`, `mpi-nimbalyst-sync`,
`mpi-handoff`, `mpi-end-session`, `mpi-cleanup`, `mpi-archive`,
`mpi-brief-rule`, and the support skill `mpi-lib`.

## Install

Install the complete pack with skills.sh / `npx skills`:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

The `--all` flag is required. The workflow skills locate shared reference
docs through the sibling `mpi-lib` support skill; partial installs are
unsupported.

> **Red `Failed to install` lines are expected.** `--all` targets every agent
> the `skills` CLI knows about, and some (e.g. `PromptScript`) reject the `-g`
> global flag. The pack still installs for every compatible agent — verify the
> skill folders exist under `~/.agents/skills/`.

More detail: [docs/install.md](docs/install.md).

## Update

Update the installed pack with the same command:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

Restart your agent sessions after updating so they reload the installed skills.

## Use

Natural language is the intended interface:

```text
brainstorm with me
initialize MPI
what is MPI-5?
show the Agent Message Bus card
create a plan
create a large plan
continue this MPI plan
read inbox
tell another agent
refresh MPI
create an MPI handoff
MPI end session
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

Task-card `maturity` is a fixed enum: `idea`, `planned`, `in-progress`,
`validating`, and `complete`. Values like `Validated`, `spec`, `active`,
`done`, or `implementing` are not maturity values and will render as invalid
cards; keep that detail in the task workspace or `status` instead.

Ask `what is MPI-42?`, `show MPI-42`, or `look at the <title> card` to trigger
`mpi-continue`'s read-only mode. It reads one card and its direct task-folder
context without starting implementation.

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

## Workflow

The normal loop is:

```text
brainstorm -> create-plan/create-large-plan -> continue -> handoff/continue -> end-session -> cleanup
```

- `mpi-brainstorm` explores an idea and can capture it as a `todo` task.
- `mpi-create-plan` creates compact plans for normal work.
- `mpi-create-large-plan` creates phased/adaptive plans and explicit parallel
  batches when work can be split safely.
- `mpi-continue` resumes from the current task ID, plan, handoff, board state,
  and repo state; it claims files before editing.
- `mpi-execute-parallel` executes explicit safe parallel batches.
- `mpi-nimbalyst-sync` coordinates source-of-truth mode, detection, dry-run
  import/export boundaries, and tracker mappings for Nimbalyst interop.
- `mpi-handoff` writes canonical handoff JSON under
  `.agents/mpi-kanban/state/handoffs/`.
- `mpi-end-session` preserves knowledge, commits when appropriate, and moves
  implemented work into validation or closes explicitly validated work.
- `mpi-cleanup` proposes conservative cleanup for old workflow artifacts.

Board lifecycle is `To do -> Doing -> Done`. Planning, checklists, validation,
attention, and handoffs live in the task workspace instead of being embedded in
card bodies.

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

For Nimbalyst interop, source-of-truth mode lives in
`.agents/mpi-kanban/state/interop.json`. Default `file` mode keeps normal MPI
JSON board updates. In `nimbalyst` mode, Nimbalyst trackers/sessions are
canonical and MPI board snapshots happen only at explicit sync boundaries.

Expected behavior by environment:

- VS Code and generic agents: stay in `file` mode; MPI updates
  `.agents/mpi-kanban/board.json`, task folders, and event logs, and the
  extension renders them.
- Nimbalyst: switch to `nimbalyst` mode only after explicit approval; update
  Nimbalyst trackers/sessions during normal work, and use `mpi-nimbalyst-sync`
  for import/export snapshots.

## Per-Project Config

For rule briefings and worker bundles, create `.agents/mpi-kanban.local.md`
using the template at
`skills/mpi-brief-rule/templates/mpi-kanban.local.md`.

## Migration

Older releases used Claude Code and Codex plugin manifests. Those install
surfaces are removed. Reinstall through skills.sh:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

**Removed skills.** The separate `mpi-project-setup` and `mpi-project-mode`
skills no longer exist. Use `mpi-init` for onboarding/adoption and
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

If a workflow skill cannot find `mpi-lib`, reinstall with the full command
above.

## Development

- [SPEC.md](SPEC.md) is the design source of truth.
- [PLAN.md](PLAN.md) tracks implementation phases.
- Run `python scripts/validate_plugin.py` before release.
- Update your local installed copy from this checkout with:
  `npx skills add . --all -y -g`.
- Release by tagging and pushing; `.github/workflows/release.yml` builds the
  GitHub Release from `CHANGELOG.md`.

## License

MIT - see [LICENSE](LICENSE).
