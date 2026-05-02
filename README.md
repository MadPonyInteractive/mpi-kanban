# Mpi-Kanban

A Claude Code plugin that bundles the MPI workflow skills (`brainstorm`,
`write-plan`, `execute-next`, `end-session`, `handoff`, `brief-rule`) and
drives a per-project Kanban board (`kanban.md`) so the board always reflects
the live state of work.

## Workflow

```
/mpi-brainstorm        →  BACKLOG entry captured
/mpi-write-plan        →  entry → PLANNING, plan file written
/mpi-execute-next × N  →  entry → IMPLEMENTING, steps tracked
/mpi-end-session       →  commit + entry → COMPLETED
```

Each skill moves the matching kanban entry one column forward. The board is
the live state of every workstream in the project.

## Required: VS Code extension

The board file is rendered as an interactive Kanban by:

- **Markdown Kanban** (`holooooo.markdown-kanban`) — version 1.3.2 or later
- Marketplace: <https://marketplace.visualstudio.com/items?itemName=holooooo.markdown-kanban>

Install it before first use. Without it, the skills still work — you just
read `.claude/mpi-kanban/kanban.md` as plain Markdown.

## Install

The plugin ships with its own marketplace manifest
(`.claude-plugin/marketplace.json`). End users install via the marketplace;
plugin authors iterate on a local clone with `--plugin-dir`.

### End users (recommended)

Once the repository is published on GitHub:

```text
/plugin marketplace add MadPonyInteractive/Mpi-Kanban
/plugin install mpi-kanban@mpi-local
/reload-plugins
```

Claude Code copies the plugin into `~/.claude/plugins/cache/` so it persists
across sessions and works offline. The local clone (if any) is no longer
needed after install.

**Updating:**

```text
/plugin marketplace update mpi-local
/plugin install mpi-kanban@mpi-local
```

**Uninstalling:**

```text
/plugin uninstall mpi-kanban@mpi-local
/plugin marketplace remove mpi-local
```

### Plugin authors (live-editing a local clone)

`/plugin install` copies the plugin into the cache — edits to your clone
will NOT show up in the installed copy. Use the `--plugin-dir` flag instead;
it loads the plugin directly from disk and picks up edits on
`/reload-plugins`.

1. Clone the repository:

   ```bash
   git clone https://github.com/MadPonyInteractive/Mpi-Kanban.git
   ```

2. Launch Claude Code pointed at the clone:

   ```bash
   claude --plugin-dir /absolute/path/to/Mpi-Kanban
   ```

   On Windows, use the absolute path of your clone (for example
   `D:\repos\Mpi-Kanban`).

3. After editing any skill, command, or hook, run `/reload-plugins` to
   refresh — no reinstall needed.

If a marketplace-installed copy of `mpi-kanban` is already present, the
`--plugin-dir` version takes precedence for that session, so you can test
changes without uninstalling the released version first.

## Per-project setup

### Kanban board

The board file lives at `.claude/mpi-kanban/kanban.md`. It is **auto-created
on first skill invocation** (any of the workflow skills — not
`mpi-brief-rule`). When auto-created, the skill emits a one-time setup notice
with a link to the file and the VS Code extension marketplace page.

Commit `.claude/mpi-kanban/kanban.md` if you want to share board state across
collaborators; gitignore it if you prefer per-developer boards.

### Plugin config (only needed for `mpi-brief-rule`)

Create `.claude/mpi-kanban.local.md` in the project root using
[`templates/mpi-kanban.local.md`](templates/mpi-kanban.local.md) as the
starting point:

```markdown
---
rules_dir: .claude/rules
rules:
  - name: components
    file: components.md
  - name: events
    file: events.md
critical_snapshot_file: CLAUDE.md
critical_snapshot_anchor: critical-rules-snapshot
---
```

Then add this line to your project `.gitignore` (if not already present):

```gitignore
.claude/*.local.md
```

The plugin will NOT auto-create this config — it is project-specific and you
must opt in to a rule list.

## Migration from existing user-scope MPI skills

If you previously used `~/.claude/skills/mpi-*` (the user-scope versions),
remove that folder after installing this plugin so the bundled versions
don't conflict:

```powershell
# After verifying the plugin works:
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-brainstorm"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-write-plan"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-execute-next"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-end-session"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-handoff"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-brief-rule"
```

(`mpi-quick-plan` is intentionally NOT bundled — keep it as a separate
user-scope skill if you still want it.)

## Slash commands

Each bundled skill ships with a thin `/mpi-<name>` wrapper for unambiguous
invocation when multiple plugins offer overlapping functionality:

| Command | Skill |
|---|---|
| `/mpi-brainstorm` | Explore an idea, capture as BACKLOG. |
| `/mpi-write-plan` | Decompose into a plan file, move entry to PLANNING. |
| `/mpi-execute-next` | Run one to-do (gated), move entry to IMPLEMENTING on first call. |
| `/mpi-end-session` | Commit + sync rules/docs + move entry to COMPLETED if all steps done. |
| `/mpi-handoff` | Generate a JSON handoff document for a fresh session. |
| `/mpi-brief-rule <name>` | Return the Sub-Agent Briefing for a configured rule. |

Skills also auto-activate on natural-language phrases — see each skill's
`description` frontmatter for trigger words.

## Troubleshooting

**Kanban not auto-creating.** All workflow skills (`brainstorm`, `write-plan`,
`execute-next`, `end-session`) call `ensureKanban()` at the right moment.
`mpi-brief-rule` does NOT — it is board-independent. If you only ran
`/mpi-brief-rule`, no board is created — that's expected. Run any workflow
skill once and the board will appear at `.claude/mpi-kanban/kanban.md`.

**Extension not rendering the board.** Confirm the extension version is
1.3.2 or later. Confirm the file is at `.claude/mpi-kanban/kanban.md` (NOT at
project root). Confirm the four columns are exactly `## BACKLOG`,
`## PLANNING`, `## IMPLEMENTING`, `## COMPLETED` — the extension breaks on
unknown column names. The plugin will refuse to write metadata fields outside
the locked schema; if you hand-edited the file and added unknown fields,
remove them.

**`/mpi-brief-rule` says "No mpi-kanban config found".** Create
`.claude/mpi-kanban.local.md` from the template and add at least one rule.
The plugin does not auto-create this file by design.

**Bootstrap notice loops on every invocation.** The notice prints on the
invocation that creates the file. If you see it on subsequent runs, the file
was deleted between invocations or the path is wrong — check
`.claude/mpi-kanban/kanban.md` exists exactly there.

## What's locked

For compatibility with the VS Code extension, do not modify these:

- The four columns: `BACKLOG`, `PLANNING`, `IMPLEMENTING`, `COMPLETED`.
- The metadata field schema (`due`, `tags`, `priority`, `workload`,
  `defaultExpanded`, `steps`).

For details, see [SPEC.md](./SPEC.md) §4.

## Distribution

This plugin targets Patreon (direct zip / git URL) and the Claude Code
marketplace once it stabilises. SPEC.md and PLAN.md are dev-facing and may
be excluded from a published bundle.

## License

MIT — see [LICENSE](./LICENSE).
