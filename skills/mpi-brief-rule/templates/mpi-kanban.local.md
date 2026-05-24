---
# Folder where rule files live, relative to project root.
rules_dir: .agents/rules

# Rules that mpi-brief-rule can extract briefings from.
# Each entry: name (used in mpi-brief-rule <name>) + file (resolves to <rules_dir>/<file>).
rules: []
# Example:
# rules:
#   - name: components
#     file: components.md
#   - name: events
#     file: events.md

# Optional bundles return several rule briefings together for sub-agent dispatch.
bundles: []
# Example:
# bundles:
#   - name: frontend-worker
#     rules: [components, events]

# File holding the universal "Critical Rules Snapshot" all sub-agents must receive.
critical_snapshot_file: AGENTS.md

# Heading id within critical_snapshot_file where the snapshot lives.
critical_snapshot_anchor: critical-rules-snapshot
---

# Mpi-Kanban project notes

This file is per-project plugin configuration for the `mpi-kanban` plugin.

**Gitignore reminder:** add `.agents/*.local.md` to your `.gitignore` so this
file is not committed. It contains project-specific configuration that should
stay local.

The body below is optional project-local context. Safe to leave empty.


