# config-ops — operations on `.claude/mpi-kanban.local.md`

Reference doc loaded by skills that need to read the per-project plugin
config. `mpi-brief-rule` consumes this directly; worker-dispatch skills use it
through `mpi-brief-rule`.

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
bundles:
  - name: frontend-worker
    rules: [components, events]
critical_snapshot_file: CLAUDE.md
critical_snapshot_anchor: critical-rules-snapshot
---

# Mpi-Kanban project notes

(Optional free-form body.)
```

| Frontmatter field | Purpose |
|---|---|
| `rules_dir` | Folder where rule files live, relative to project root. |
| `rules` | List of `{name, file}` entries `mpi-brief-rule` exposes. `name` is the user-facing handle (`/mpi-kanban:mpi-brief-rule <name>`); resolved path is `<rules_dir>/<file>`. |
| `bundles` | Optional list of `{name, rules}` entries. `rules` is an ordered list of configured rule names to return together for sub-agent dispatch. |
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
     bundles: [{ name, rules: [...] }, ...],
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
- For the optional `bundles` list: each entry has a name and a list of rule
  names, e.g.
  ```
    - name: frontend-worker
      rules: [components, events]
  ```

If a hook script ever needs the same data from bash, the standard pattern is:

```bash
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$FILE")
RULES_DIR=$(echo "$FRONTMATTER" | grep '^rules_dir:' | sed 's/rules_dir: *//')
```

(No hook in v0.1.0 needs this — included for forward reference.)

### `getRuleList(config)`

Return `config.rules` (a list of `{name, file}` objects). If the list is empty
or missing, return `[]`.

### `getBundleList(config)`

Return `config.bundles` (a list of `{name, rules}` objects). If the list is
empty or missing, return `[]`.

### `resolveRulePath(config, ruleName)`

1. Find the entry in `config.rules` where `name === ruleName`.
2. If none → return `null`. The caller lists available rule names.
3. Otherwise return `<project-root>/<config.rules_dir>/<entry.file>`.

### `resolveBundle(config, bundleName)`

1. Find the entry in `config.bundles` where `name === bundleName`.
2. If none → return `null`.
3. Otherwise return the ordered list of rule names in the bundle.
4. The caller resolves each rule through `resolveRulePath(config, ruleName)`.
   If any rule is missing, report the broken bundle and stop.

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
bundles:
  - name: frontend-worker
    rules: [components, events]
critical_snapshot_file: CLAUDE.md
critical_snapshot_anchor: critical-rules-snapshot
---

Add the rules and optional bundles you want sub-agents to receive briefings for.

Reminder: `.local.md` files are user-local. Add `.claude/*.local.md` to your
`.gitignore` if it is not already covered.
```

After printing the notice, stop — do not auto-create the file.
