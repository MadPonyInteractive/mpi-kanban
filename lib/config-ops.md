# config-ops — operations on `.claude/mpi-kanban.local.md`

Reference doc loaded by skills that need to read the per-project plugin
config. Currently only `mpi-brief-rule` consumes this file.

---

## File location

```
<project-root>/.claude/mpi-kanban.local.md
```

The `.local.md` suffix lets the user gitignore it via the standard
`.claude/*.local.md` pattern. The file is ALWAYS user-managed — never
auto-create it (config is project-specific; the user must opt in).

---

## Schema

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

# Mpi-Kanban project notes

(Optional free-form body.)
```

| Frontmatter field | Purpose |
|---|---|
| `rules_dir` | Folder where rule files live, relative to project root. |
| `rules` | List of `{name, file}` entries `mpi-brief-rule` exposes. `name` is the user-facing handle (`/mpi-brief-rule <name>`); resolved path is `<rules_dir>/<file>`. |
| `critical_snapshot_file` | File holding the universal "Critical Rules Snapshot" all sub-agents must receive. |
| `critical_snapshot_anchor` | Heading id within `critical_snapshot_file` where the snapshot lives. |

---

## Procedures

### `loadConfig()`

1. Resolve path: `<project-root>/.claude/mpi-kanban.local.md`.
2. Try to `Read` it.
3. If missing → return `null`. The caller emits the bootstrap notice (below).
4. If found → parse the YAML frontmatter and return a config object:

   ```
   {
     rules_dir: "<string>",
     rules: [{ name, file }, ...],
     critical_snapshot_file: "<string>",
     critical_snapshot_anchor: "<string>"
   }
   ```

### Frontmatter parsing pattern

The frontmatter is the block between the first `---` and the next `---` at the
top of the file. To extract it without a YAML parser:

- The model performing this read can parse the frontmatter directly from the
  `Read` tool output. No `sed`/`awk` is required when a skill calls `Read` and
  reasons over the contents itself.
- For scalar fields (`rules_dir`, `critical_snapshot_file`,
  `critical_snapshot_anchor`): take the text after the colon, trim, strip
  surrounding quotes if present.
- For the `rules` list: each entry is two indented lines, e.g.
  ```
    - name: components
      file: components.md
  ```
  An empty `rules: []` is valid (means "no rules configured yet").

If a hook script ever needs the same data from bash, the standard pattern is:

```bash
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$FILE")
RULES_DIR=$(echo "$FRONTMATTER" | grep '^rules_dir:' | sed 's/rules_dir: *//')
```

(No hook in v0.1.0 needs this — included for forward reference.)

### `getRuleList(config)`

Return `config.rules` (a list of `{name, file}` objects). If the list is empty
or missing, return `[]`.

### `resolveRulePath(config, ruleName)`

1. Find the entry in `config.rules` where `name === ruleName`.
2. If none → return `null`. The caller lists available rule names.
3. Otherwise return `<project-root>/<config.rules_dir>/<entry.file>`.

### `loadCriticalSnapshot(config)`

1. Resolve path: `<project-root>/<config.critical_snapshot_file>`.
2. `Read` it.
3. Find the heading whose anchor matches `config.critical_snapshot_anchor`.
   Anchor matching is "lowercase the heading text, replace non-alphanumerics
   with hyphens" — the standard Markdown anchor convention.
4. Return the content from that heading up to (but not including) the next
   heading at the same level or above.
5. If the file or anchor is missing → return `null` and surface a clear
   message to the user (they have a config but the snapshot file is broken).

---

## Bootstrap snippet (config missing)

When `mpi-brief-rule` is invoked and `loadConfig()` returns `null`, emit this
verbatim (substituting the project-relative path):

```
No mpi-kanban config found.

To enable rule briefings, create [.claude/mpi-kanban.local.md](.claude/mpi-kanban.local.md)
with this shape:

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

Add the rules you want sub-agents to receive briefings for.

Reminder: `.local.md` files are user-local. Add `.claude/*.local.md` to your
`.gitignore` if it is not already covered.
```

After printing the notice, stop — do not auto-create the file.
