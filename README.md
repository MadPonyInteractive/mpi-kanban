# Mpi-Kanban

A Claude Code plugin that bundles the MPI workflow skills (`brainstorm`,
`write-plan`, `execute-next`, `end-session`, `archive`, `handoff`,
`brief-rule`) and drives a per-project Kanban board (`kanban.md`) so the board
always reflects the live state of work.

## Workflow

```text
/mpi-kanban:mpi-init [file]       -> bootstrap board, optional import from a to-do file
/mpi-kanban:mpi-brainstorm        -> BACKLOG entry captured
/mpi-kanban:mpi-write-plan        -> entry to PLANNING, plan file written
/mpi-kanban:mpi-execute-next x N  -> entry to IMPLEMENTING, steps tracked
/mpi-kanban:mpi-end-session       -> commit + entry to COMPLETED
/mpi-kanban:mpi-archive completed -> COMPLETED entries to archive file
```

Each workflow skill moves the matching kanban entry one column forward. The
archive skill moves old entries out of the active board while preserving them
beside the board.

## Required: VS Code extension

The board file is rendered as an interactive Kanban by:

- **Markdown Kanban** (`holooooo.markdown-kanban`) - version 1.3.2 or later
- Marketplace: <https://marketplace.visualstudio.com/items?itemName=holooooo.markdown-kanban>

Install it before first use. Without it, the skills still work; you just read
`.claude/mpi-kanban/kanban.md` as plain Markdown.

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
across sessions and works offline. The local clone, if any, is no longer
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

`/plugin install` copies the plugin into the cache, so edits to your clone will
not show up in the installed copy. Use the `--plugin-dir` flag instead; it
loads the plugin directly from disk and picks up edits on `/reload-plugins`.

1. Clone the repository:

   ```bash
   git clone https://github.com/MadPonyInteractive/Mpi-Kanban.git
   ```

2. Launch Claude Code pointed at the clone:

   ```bash
   claude --plugin-dir /absolute/path/to/Mpi-Kanban
   ```

   On Windows, use the absolute path of your clone, for example
   `D:\repos\Mpi-Kanban`.

3. After editing any skill, command, or hook, run `/reload-plugins`.

If a marketplace-installed copy of `mpi-kanban` is already present, the
`--plugin-dir` version takes precedence for that session, so you can test
changes without uninstalling the released version first.

## Per-project setup

### Kanban board

The board file lives at `.claude/mpi-kanban/kanban.md`. It is **auto-created
on first workflow skill invocation**. `mpi-brief-rule` and `mpi-archive` do not
auto-create the board. When auto-created, the skill emits a one-time setup
notice with a link to the file and the VS Code extension marketplace page.

Commit `.claude/mpi-kanban/kanban.md` if you want to share board state across
collaborators; gitignore it if you prefer per-developer boards.

### Archives

Archived entries live beside the board:

```text
.claude/mpi-kanban/archived.md
.claude/mpi-kanban/archived-2.md
.claude/mpi-kanban/archived-3.md
```

`mpi-archive` uses `archived.md` until it has more than 200 lines, then moves
to the next incrementing file. Archive operations preserve whole entry blocks
verbatim and remove them from `kanban.md` only after the archive write
succeeds.

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

Then add this line to your project `.gitignore` if not already present:

```gitignore
.claude/*.local.md
```

The plugin will not auto-create this config. It is project-specific and you
must opt in to a rule list.

## Migration from existing user-scope MPI skills

If you previously used `~/.claude/skills/mpi-*`, remove those user-scope
versions after installing this plugin so the bundled versions do not conflict:

```powershell
# After verifying the plugin works:
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-brainstorm"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-write-plan"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-execute-next"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-end-session"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-archive"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-handoff"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\mpi-brief-rule"
```

`mpi-quick-plan` is intentionally not bundled. Keep it as a separate
user-scope skill if you still want it.

## Slash commands

Each bundled skill can be invoked directly with its plugin-namespaced name:

| Command | Skill |
|---|---|
| `/mpi-kanban:mpi-init` | Bootstrap the board and optionally import entries from a freeform to-do / backlog / ideas file. |
| `/mpi-kanban:mpi-brainstorm` | Explore an idea, capture as BACKLOG. |
| `/mpi-kanban:mpi-write-plan` | Decompose into a plan file, move entry to PLANNING. |
| `/mpi-kanban:mpi-execute-next` | Run one to-do (gated), move entry to IMPLEMENTING on first call. |
| `/mpi-kanban:mpi-end-session` | Commit + sync rules/docs + move entry to COMPLETED if all steps done. |
| `/mpi-kanban:mpi-archive completed` | Move COMPLETED entries from the active board into archive files. |
| `/mpi-kanban:mpi-archive <title>` | Move one exact-title entry from the active board into an archive file. |
| `/mpi-kanban:mpi-handoff` | Generate a JSON handoff document for a fresh session. |
| `/mpi-kanban:mpi-brief-rule <name>` | Return the Sub-Agent Briefing for a configured rule. |

Skills also auto-activate on natural-language phrases. See each skill's
`description` frontmatter for trigger words.

## Troubleshooting

**Kanban not auto-creating.** Workflow skills (`brainstorm`, `write-plan`,
`execute-next`, `end-session`) call `ensureKanban()` at the right moment.
`mpi-brief-rule` does not because it is board-independent. `mpi-archive` also
does not because archiving a missing board should be a no-op, not a bootstrap.
Run any workflow skill once and the board will appear at
`.claude/mpi-kanban/kanban.md`.

**Extension not rendering the board.** Confirm the extension version is 1.3.2
or later. Confirm the file is at `.claude/mpi-kanban/kanban.md`, not at project
root. Confirm the four columns are exactly `## BACKLOG`, `## PLANNING`,
`## IMPLEMENTING`, `## COMPLETED`. The extension breaks on unknown column names
and unknown metadata fields.

**`/mpi-kanban:mpi-brief-rule` says "No mpi-kanban config found".** Create
`.claude/mpi-kanban.local.md` from the template and add at least one rule. The
plugin does not auto-create this file by design.

**`/mpi-kanban:mpi-archive <title>` cannot find an entry.** The archive skill
requires an exact H3 title match. Re-run with the exact title from
`.claude/mpi-kanban/kanban.md`.

**Bootstrap notice loops on every invocation.** The notice prints on the
invocation that creates the file. If you see it on subsequent runs, the file
was deleted between invocations or the path is wrong. Check that
`.claude/mpi-kanban/kanban.md` exists exactly there.

## What's locked

For compatibility with the VS Code extension, do not modify these:

- The four columns: `BACKLOG`, `PLANNING`, `IMPLEMENTING`, `COMPLETED`.
- The metadata field schema (`due`, `tags`, `priority`, `workload`,
  `defaultExpanded`, `steps`).

For details, see [SPEC.md](./SPEC.md) section 4.

## Distribution

This plugin targets Patreon (direct zip / git URL) and the Claude Code
marketplace once it stabilizes. SPEC.md and PLAN.md are dev-facing and may be
excluded from a published bundle.

## License

MIT - see [LICENSE](./LICENSE).
