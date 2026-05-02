---
# Folder where rule files live, relative to project root.
rules_dir: .claude/rules

# Rules that mpi-brief-rule can extract briefings from.
# Each entry: name (used in /mpi-brief-rule <name>) + file (resolves to <rules_dir>/<file>).
rules: []
# Example:
# rules:
#   - name: components
#     file: components.md
#   - name: events
#     file: events.md

# File holding the universal "Critical Rules Snapshot" all sub-agents must receive.
critical_snapshot_file: CLAUDE.md

# Heading id within critical_snapshot_file where the snapshot lives.
critical_snapshot_anchor: critical-rules-snapshot
---

# Mpi-Kanban project notes

This file is per-project plugin configuration for the `mpi-kanban` plugin.

**Gitignore reminder:** add `.claude/*.local.md` to your `.gitignore` so this file
is not committed. It contains project-specific configuration that should stay local.

The body below is currently unused by the plugin — reserved for future skills that
may want a project-level prose note. Safe to leave empty.
