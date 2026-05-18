# Mpi-Kanban

Claude Code plugin. Bundles MPI workflow skills, drives a per-project Kanban
board (`.claude/mpi-kanban/kanban.md`) that reflects live work, and defines a
shared `.agents/mpi-kanban/state/` coordination contract for Claude and Codex.

Skills: `init`, `brainstorm`, `create-plan`, `create-large-plan`, `continue`, `execute-parallel`, `handoff`, `end-session`, `cleanup`, `archive`, `brief-rule`.

## Install

In Claude Code, run:

```text
/plugin marketplace add MadPonyInteractive/mpi-kanban
/plugin install mpi-kanban@mad-pony-interactive
```

Claude Code clones the public GitHub repo, registers the marketplace, and installs the plugin. Restart Claude Code so the skills register, then type `/mpi-kanban:` — you should see eleven skills in the autocomplete list.

### (Recommended) Install the VS Code extension

The board file is plain Markdown, but the **Mpi-Kanban** VS Code extension renders it as an interactive Kanban board:

- Marketplace ID: `MadPonyInteractive.mpi-kanban`
- Repository: <https://github.com/MadPonyInteractive/mpi-kanban-vscode>
- Extension page: <https://marketplace.visualstudio.com/items?itemName=MadPonyInteractive.mpi-kanban>

![Mpi-Kanban board in VS Code](./imgs/board.png)

Without it, `.claude/mpi-kanban/kanban.md` still works — it is just Markdown.

## Using the plugin

Natural language is the intended interface. Each skill auto-triggers from phrases like:

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

You can also invoke any skill directly via slash command. After each skill runs, it tells you the next useful phrase. Kanban updates happen automatically inside the workflow — you do not need to ask separately.

### Slash commands

| Command | What it does |
|---|---|
| `/mpi-kanban:mpi-init` | Bootstrap the board, optionally import a backlog file. |
| `/mpi-kanban:mpi-brainstorm` | Explore an idea, capture it as a BACKLOG entry. |
| `/mpi-kanban:mpi-create-plan` | Create a compact default plan. |
| `/mpi-kanban:mpi-create-large-plan` | Create an adaptive plan for complex/uncertain work. |
| `/mpi-kanban:mpi-continue` | Resume active work from plan/handoff/current state. |
| `/mpi-kanban:mpi-execute-parallel` | Execute an explicit `## Parallel Batch`. |
| `/mpi-kanban:mpi-handoff` | Generate a JSON handoff + resume prompt for a fresh session. |
| `/mpi-kanban:mpi-end-session` | Commit, preserve docs/rules, close the active kanban entry. |
| `/mpi-kanban:mpi-cleanup` | Propose cleanup for stale plans, handoffs, artifacts. |
| `/mpi-kanban:mpi-archive completed` | Archive all COMPLETED entries. |
| `/mpi-kanban:mpi-archive <title>` | Archive one entry by exact title. |
| `/mpi-kanban:mpi-brief-rule <name>` | Return a configured rule briefing or bundle. |

## Per-project setup

### Kanban board

Lives at `.claude/mpi-kanban/kanban.md`. Auto-created on first workflow skill that mutates it (`brainstorm`, `create-plan`, `create-large-plan`, `continue`, `end-session`). Board-independent skills (`brief-rule`, `archive`, `cleanup`) do not auto-create it.

Commit `.claude/mpi-kanban/kanban.md` for shared boards. Gitignore it for per-developer boards.

### Shared agent coordination state

Canonical machine-readable coordination state lives at
`.agents/mpi-kanban/state/`. The board remains the human-visible workflow file;
agent session, task, file-claim, and handoff records belong under `.agents/`.

Agents read `.agents/mpi-kanban/state/index.json` first when it exists. The
shared contract is documented in [`docs/coordination/`](docs/coordination/).
Use `python scripts/new_uuid.py` to generate record IDs.

Lifecycle procedures live under [`lib/coordination-ops/`](lib/coordination-ops/).
They define session registration, heartbeats, task records, file claims, handoff
records, stale reclaim behavior, and cleanup expectations.

Kanban tags may be used as a coarse human-visible summary such as
`agent-active`, `claimed`, `needs-review`, `needs-verify`,
`needs-integration`, `blocked`, `stale-claim`, or `handoff-ready`. Tags are not
coordination authority; agents use `.agents/mpi-kanban/state/` first.

File ownership and commit ownership are separate. A released or completed file
claim means there is no active writer, but pending-change provenance can still
matter. The final commit summary belongs to `mpi-end-session` or an explicit
integrator after rereading current state.

New canonical handoffs live under `.agents/mpi-kanban/state/handoffs/`.
`docs/handoffs/` is legacy compatibility during migration.

### Optional plugin config

For rule briefings and worker bundles, copy [`templates/mpi-kanban.local.md`](templates/mpi-kanban.local.md) to `.claude/mpi-kanban.local.md` and edit:

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

Add to `.gitignore` if local-only:

```gitignore
.claude/*.local.md
```

## Planning model

- `mpi-create-plan` — default. Compact living plan, one implementation flow, final verification.
- `mpi-create-large-plan` — complex/uncertain work. Phases, plan drift notes, preservation notes, explicit `## Parallel Batch` sections.
- `mpi-continue` — default implementation/resume skill. Reads plan, shared coordination index when present, latest handoff, kanban entry, current repo state before proposing work; claims files before editing.
- `mpi-execute-parallel` — runs only explicit parallel batches with declared, disjoint ownership and per-worker file claims.

Plans are living documents. Agents update `Current State`, `Plan Drift`, `Remaining Work`, and `Preservation Notes` as reality changes.

## Troubleshooting

**Slash commands not showing up.** Restart Claude Code. If still missing, uninstall + reinstall:
```text
/plugin uninstall mpi-kanban@mad-pony-interactive
/plugin install mpi-kanban@mad-pony-interactive
```

**Kanban not auto-creating.** Only workflow skills that mutate the board call `ensureKanban()`. `brief-rule`, `archive`, and `cleanup` do not.

**Handoff did not include a resume prompt.** That is a bug — `mpi-handoff` must always print the mandatory resume block pointing to `mpi-continue`.

**A handoff is under `docs/handoffs/`.** Treat it as legacy compatibility. New
handoffs should use `.agents/mpi-kanban/state/handoffs/<uuid>.json`; legacy
files may point to the canonical handoff during migration.

**Parallel execution refused to run.** The plan must contain an explicit `## Parallel Batch` section with `Ownership:`, `Briefings:`, and `**Verify:**` for every task.

**VS Code extension not rendering the board.** Confirm the extension is installed and the file is at `.claude/mpi-kanban/kanban.md` with exactly these columns: `BACKLOG`, `PLANNING`, `IMPLEMENTING`, `COMPLETED`.

## Migration from user-scope MPI skills

If you previously used `~/.claude/skills/mpi-*`, remove the user-scope versions after installing this plugin so they do not conflict with the bundled versions:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-brainstorm"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-write-plan"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-execute-next"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-end-session"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-archive"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-handoff"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-brief-rule"
```

`mpi-write-plan` and `mpi-execute-next` are intentionally replaced by `mpi-create-plan` / `mpi-create-large-plan` and `mpi-continue`.

## What's locked

For compatibility with the VS Code extension, do not modify:

- The four columns: `BACKLOG`, `PLANNING`, `IMPLEMENTING`, `COMPLETED`.
- The metadata field schema (`due`, `tags`, `priority`, `workload`, `defaultExpanded`, `steps`).

See the Kanban Contract in [SPEC.md](./SPEC.md) for details.

## For plugin authors

If you are editing the plugin itself rather than just using it:

- See [CLAUDE.md](./CLAUDE.md) for build constraints and live-copy maintenance.
- See [SPEC.md](./SPEC.md) and [PLAN.md](./PLAN.md) for design.
- Run `python scripts/validate_plugin.py` before copying or releasing plugin
  changes.
- After editing skills/hooks, run `/reload-plugins` in Claude Code, or uninstall + reinstall the plugin if you added or removed a skill folder.

## License

MIT — see [LICENSE](./LICENSE).
