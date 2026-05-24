# Mpi-Kanban

An Agent Skills pack that lets multiple AI agents work side by side on the
same project - even on the same files - without overwriting each other.
Agents share a live coordination state so one can implement while another
reviews, verifies, or integrates, and a visible Kanban board keeps you in the
loop on what every agent is doing. Bundles the full MPI workflow (brainstorm,
plan, continue, parallel execution, handoff, end session, cleanup) so a single
session or a whole team of agents can pick up work, coordinate file ownership,
and ship together.

Skills: `mpi-init`, `mpi-project-setup`, `mpi-project-mode`,
`mpi-project-refresh`, `mpi-brainstorm`, `mpi-create-plan`,
`mpi-create-large-plan`, `mpi-continue`, `mpi-execute-parallel`,
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

More detail: [docs/install.md](docs/install.md).

## Use

Natural language is the intended interface:

```text
brainstorm with me
set up project knowledge
create a plan
create a large plan
continue this MPI plan
create an MPI handoff
MPI end session
run MPI cleanup
```

Direct invocation depends on the agent. Use the Agent Skills invocation surface
your tool provides, such as `mpi-continue`, `/mpi-continue`, or an equivalent
skill command.

## VS Code Board

The board file is plain Markdown. The companion **Mpi-Kanban** VS Code
extension renders it as an interactive board:

- Marketplace ID: `MadPonyInteractive.mpi-kanban`
- Repository: <https://github.com/MadPonyInteractive/mpi-kanban-vscode>
- Extension page: <https://marketplace.visualstudio.com/items?itemName=MadPonyInteractive.mpi-kanban>

![Mpi-Kanban board in VS Code](./imgs/board.png)

Without the extension, `.claude/mpi-kanban/kanban.md` still works as Markdown.

## Workflow

The normal loop is:

```text
brainstorm -> create-plan/create-large-plan -> continue -> handoff/continue -> end-session -> cleanup
```

- `mpi-brainstorm` explores an idea and can capture it on the board.
- `mpi-create-plan` creates compact plans for normal work.
- `mpi-create-large-plan` creates phased/adaptive plans and explicit parallel
  batches when work can be split safely.
- `mpi-continue` resumes from the current plan, handoff, board state, and repo
  state; it claims files before editing.
- `mpi-execute-parallel` executes explicit safe parallel batches.
- `mpi-handoff` writes canonical handoff JSON under
  `.agents/mpi-kanban/state/handoffs/`.
- `mpi-end-session` preserves knowledge, commits when appropriate, and closes
  board state.
- `mpi-cleanup` proposes conservative cleanup for old workflow artifacts.

## Project Knowledge

Mpi-Kanban can maintain durable project knowledge:

- `.agents/mpi-kanban/project-profile.md`
- `.agents/mpi-kanban/project-knowledge-index.md`

Run `mpi-project-setup` once per project. Later, use `mpi-project-refresh` to
audit drift and `mpi-project-mode` to review or change the project mode.

## Coordination

Agents coordinate through `.agents/mpi-kanban/state/`:

- `index.json` is the first file agents read.
- Sessions record role and heartbeat.
- Tasks connect work to a plan and board entry.
- File claims are active write locks.
- Handoffs preserve state for a fresh session.

Kanban tags are display summaries only. The coordination state is the source of
truth.

## Per-Project Config

For rule briefings and worker bundles, create `.claude/mpi-kanban.local.md`
using the template at
`skills/mpi-brief-rule/templates/mpi-kanban.local.md`.

## Migration

Older releases used Claude Code and Codex plugin manifests. Those install
surfaces are removed. Reinstall through skills.sh:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

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
