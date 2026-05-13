# Mpi-Kanban

A Claude Code plugin that bundles the MPI workflow skills (`init`,
`brainstorm`, `create-plan`, `create-large-plan`, `continue`,
`execute-parallel`, `handoff`, `end-session`, `cleanup`, `archive`,
`brief-rule`) and drives a per-project Kanban board (`kanban.md`) so the board
reflects live work.

## Workflow

```text
/mpi-kanban:mpi-init [file]          -> bootstrap board, optional import
/mpi-kanban:mpi-brainstorm           -> explore idea, capture BACKLOG entry
/mpi-kanban:mpi-create-plan          -> compact/default plan, entry to PLANNING
/mpi-kanban:mpi-create-large-plan    -> adaptive/large plan, entry to PLANNING
/mpi-kanban:mpi-continue             -> resume/implement from current reality
/mpi-kanban:mpi-execute-parallel     -> run an explicit Parallel Batch
/mpi-kanban:mpi-handoff              -> preserve state for a fresh session
/mpi-kanban:mpi-end-session          -> commit + close active entry
/mpi-kanban:mpi-cleanup              -> propose workflow artifact cleanup
/mpi-kanban:mpi-archive completed    -> COMPLETED entries to archive file
```

Natural language is the intended interface:

```text
brainstorm with me
create a plan
create a large plan
continue this plan
handoff
read this handoff and continue
end session
cleanup MPI files
```

Each skill should tell you the next useful phrase to say. Kanban updates are
part of the workflow skills; you should not need to ask separately.

## Required: VS Code extension

The board file is rendered as an interactive Kanban by:

- **Markdown Kanban** (`holooooo.markdown-kanban`) - version 1.3.2 or later
- Marketplace: <https://marketplace.visualstudio.com/items?itemName=holooooo.markdown-kanban>

Without it, the skills still work; `.claude/mpi-kanban/kanban.md` is just plain
Markdown.

## Install

The plugin ships with its own marketplace manifest
(`.claude-plugin/marketplace.json`). End users install via the marketplace;
plugin authors iterate on a local clone with `--plugin-dir`.

### End users

```text
/plugin marketplace add MadPonyInteractive/Mpi-Kanban
/plugin install mpi-kanban@mpi-local
/reload-plugins
```

### Plugin authors

```bash
git clone https://github.com/MadPonyInteractive/Mpi-Kanban.git
claude --plugin-dir /absolute/path/to/Mpi-Kanban
```

After editing any skill, command, or hook, run `/reload-plugins`.

## Per-project setup

### Kanban board

The board file lives at `.claude/mpi-kanban/kanban.md`. It is auto-created on
first workflow skill invocation. `mpi-brief-rule`, `mpi-archive`, and
`mpi-cleanup` do not auto-create the board.

Commit `.claude/mpi-kanban/kanban.md` if you want shared board state; gitignore
it if you prefer per-developer boards.

### Plugin config

Create `.claude/mpi-kanban.local.md` from
[`templates/mpi-kanban.local.md`](templates/mpi-kanban.local.md) when you want
rule briefings or worker bundles:

```markdown
---
rules_dir: .claude/rules
rules:
  - name: components
    file: components.md
bundles:
  - name: frontend-worker
    rules: [components]
critical_snapshot_file: CLAUDE.md
critical_snapshot_anchor: critical-rules-snapshot
---
```

Add this to `.gitignore` if needed:

```gitignore
.claude/*.local.md
```

## Planning model

- `mpi-create-plan` is the default. It creates a compact living plan with one
  implementation flow and final verification.
- `mpi-create-large-plan` is for complex or uncertain work. It supports
  phases, plan drift notes, preservation notes, and explicit
  `## Parallel Batch` sections.
- `mpi-continue` is the default implementation/resume skill. It reads the plan,
  latest handoff, kanban entry, and current repo state before proposing work.
- `mpi-execute-parallel` only runs explicit parallel batches with declared,
  disjoint ownership.

Plans are living documents. Agents should update `Current State`, `Plan Drift`,
`Remaining Work`, and `Preservation Notes` when reality changes.

## Slash commands

| Command | Skill |
|---|---|
| `/mpi-kanban:mpi-init` | Bootstrap the board and optionally import entries. |
| `/mpi-kanban:mpi-brainstorm` | Explore an idea and capture it as BACKLOG. |
| `/mpi-kanban:mpi-create-plan` | Create a compact/default plan. |
| `/mpi-kanban:mpi-create-large-plan` | Create an adaptive large plan. |
| `/mpi-kanban:mpi-continue` | Continue active work from plan/handoff/current state. |
| `/mpi-kanban:mpi-execute-parallel` | Execute an explicit parallel batch. |
| `/mpi-kanban:mpi-handoff` | Generate a JSON handoff plus mandatory resume prompt. |
| `/mpi-kanban:mpi-end-session` | Commit, preserve docs/rules/memory, close kanban entry. |
| `/mpi-kanban:mpi-cleanup` | Propose cleanup for stale plans/handoffs/artifacts. |
| `/mpi-kanban:mpi-archive completed` | Archive completed kanban entries. |
| `/mpi-kanban:mpi-archive <title>` | Archive one exact-title kanban entry. |
| `/mpi-kanban:mpi-brief-rule <name>` | Return a configured rule briefing or bundle. |

## Migration from existing user-scope MPI skills

If you previously used `~/.claude/skills/mpi-*`, remove those user-scope
versions after installing this plugin so the bundled versions do not conflict:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-brainstorm"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-write-plan"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-execute-next"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-end-session"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-archive"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-handoff"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-brief-rule"
```

`mpi-write-plan` and `mpi-execute-next` are intentionally replaced by
`mpi-create-plan` / `mpi-create-large-plan` and `mpi-continue`.

## Troubleshooting

**Kanban not auto-creating.** Workflow skills (`brainstorm`, `create-plan`,
`create-large-plan`, `continue`, `end-session`) call `ensureKanban()` at the
right moment. Board-independent skills do not.

**Handoff did not include a pasteable prompt.** That is a bug. `mpi-handoff`
must always print the mandatory resume block pointing to `mpi-continue`.

**Parallel execution refused to run.** Add an explicit `## Parallel Batch`
section with `Ownership:`, `Briefings:`, and `**Verify:**` for every task.

**Extension not rendering the board.** Confirm the extension version is 1.3.2
or later and the file is at `.claude/mpi-kanban/kanban.md` with exactly these
columns: `BACKLOG`, `PLANNING`, `IMPLEMENTING`, `COMPLETED`.

## What's locked

For compatibility with the VS Code extension, do not modify these:

- The four columns: `BACKLOG`, `PLANNING`, `IMPLEMENTING`, `COMPLETED`.
- The metadata field schema (`due`, `tags`, `priority`, `workload`,
  `defaultExpanded`, `steps`).

For details, see [SPEC.md](./SPEC.md) section 4.

## License

MIT - see [LICENSE](./LICENSE).
