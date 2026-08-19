# config-ops â€” operations on `.agents/mpi-kanban.local.md`

Reference doc loaded by skills that need to read the per-project plugin
config. `mpi-brief-rule` consumes this directly; worker-dispatch skills use it
through `mpi-brief-rule`.

---

## File location

```
<project-root>/.agents/mpi-kanban.local.md
```

The `.local.md` suffix lets the user gitignore it via the standard
`.agents/*.local.md` pattern.

`mpi-init` scaffolds this file as part of project adoption, with approval. It
is the ONLY skill that creates it. Every consumer - `mpi-brief-rule` above all -
must treat a missing config as a stop condition and emit the bootstrap notice
below; consumers must never auto-create it. After adoption the file is
user-managed.

---

## Schema

```markdown
---
rules_dir: .agents/rules
rules:
  - name: components
    file: components.md
  - name: events
    file: events.md
bundles:
  - name: frontend-worker
    rules: [components, events]
critical_snapshot_file: AGENTS.md
critical_snapshot_anchor: critical-rules-snapshot
gpu_command_patterns:
  - python .*(train|sweep|generate)
  - pytest .*-m gpu
---

# Mpi-Kanban project notes

(Optional free-form body.)
```

| Frontmatter field | Purpose |
|---|---|
| `rules_dir` | Folder where rule files live, relative to project root. |
| `rules` | List of `{name, file}` entries `mpi-brief-rule` exposes. `name` is the user-facing handle (`mpi-brief-rule <name>`); resolved path is `<rules_dir>/<file>`. |
| `bundles` | Optional list of `{name, rules}` entries. `rules` is an ordered list of configured rule names to return together for sub-agent dispatch. |
| `critical_snapshot_file` | File holding the universal "Critical Rules Snapshot" all sub-agents must receive. |
| `critical_snapshot_anchor` | Heading id within `critical_snapshot_file` where the snapshot lives. |
| `gpu_command_patterns` | Optional list of regexes matched against a raw Bash command. A match that is not routed through `gpu_lease.py` is blocked by `guard-gpu`. Absent or empty means the GPU lease is not enforced in this project - it is opt-in, because blocking every `pytest` in every adopted repo on the chance it touches a GPU costs more than the collision it prevents. See `coordination-ops/lifecycle.md` § Lease A GPU. |

---

## Procedures

### `loadConfig()`

1. Resolve path: `<project-root>/.agents/mpi-kanban.local.md`.
2. Try to `Read` it.
3. If missing â†’ return `null`. The caller emits the bootstrap notice (below).
4. If found â†’ parse the YAML frontmatter and return a config object:

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

(No hook in v0.1.0 needs this â€” included for forward reference.)

### `getRuleList(config)`

Return `config.rules` (a list of `{name, file}` objects). If the list is empty
or missing, return `[]`.

### `getBundleList(config)`

Return `config.bundles` (a list of `{name, rules}` objects). If the list is
empty or missing, return `[]`.

### `resolveRulePath(config, ruleName)`

1. Find the entry in `config.rules` where `name === ruleName`.
2. If none â†’ return `null`. The caller lists available rule names.
3. Otherwise return `<project-root>/<config.rules_dir>/<entry.file>`.

### `resolveBundle(config, bundleName)`

1. Find the entry in `config.bundles` where `name === bundleName`.
2. If none â†’ return `null`.
3. Otherwise return the ordered list of rule names in the bundle.
4. The caller resolves each rule through `resolveRulePath(config, ruleName)`.
   If any rule is missing, report the broken bundle and stop.

### `loadCriticalSnapshot(config)`

1. Resolve path: `<project-root>/<config.critical_snapshot_file>`.
2. `Read` it.
3. Find the heading whose anchor matches `config.critical_snapshot_anchor`.
   Anchor matching is "lowercase the heading text, replace non-alphanumerics
   with hyphens" â€” the standard Markdown anchor convention.
4. Return the content from that heading up to (but not including) the next
   heading at the same level or above.
5. If the file or anchor is missing â†’ return `null` and surface a clear
   message to the user (they have a config but the snapshot file is broken).

---

## Bootstrap snippet (config missing)

When a consumer calls `loadConfig()` and it returns `null`, emit this verbatim
(substituting the project-relative path):

```
No mpi-kanban config found at .agents/mpi-kanban.local.md, so no rule briefings
can be resolved. Any sub-agent dispatched right now receives no briefing at all.

Fix it in one of two ways:

1. Run `/mpi-init` in this project. It scaffolds the config and fills the rules
   list by scanning the rules folder for files with a `## Sub-Agent Briefing`
   heading. Projects adopted before this was added need one `/mpi-init` pass, or
   a `/mpi-project-refresh`, which reports the missing config as a finding.

2. Hand-write [.agents/mpi-kanban.local.md](.agents/mpi-kanban.local.md) with
   this shape:

---
rules_dir: .agents/rules
rules:
  - name: components
    file: components.md
bundles:
  - name: frontend-worker
    rules: [components, events]
critical_snapshot_file: AGENTS.md
critical_snapshot_anchor: critical-rules-snapshot
---

Reminder: `.local.md` files are user-local. Add `.agents/*.local.md` to your
`.gitignore` if it is not already covered.
```

After printing the notice, stop. Do not auto-create the file. Only `mpi-init`
creates it.

---

## `scaffoldConfig()` - `mpi-init` only

Runs once, during project adoption, after approval. No other skill may call it.

1. If `<project-root>/.agents/mpi-kanban.local.md` already exists, stop and keep
   it. Never overwrite a user-managed config.
2. Determine `rules_dir`: the first existing directory of `.agents/rules`,
   `.claude/rules`, `docs/rules`. If none exists, use `.agents/rules`.
3. Scan `rules_dir` (top level, then one level deep) for `*.md` files containing
   a `## Sub-Agent Briefing` heading. Each match becomes one `{name, file}`
   entry: `file` is the path relative to `rules_dir`, `name` is the filename
   without its extension. A rule file with no such heading is skipped from the
   list - it is a rule for humans, not a dispatchable briefing.
3b. If the scan found nothing, seed the first rule with `seedFirstRule()` below
   rather than writing an empty `rules: []`. A project with no rules dispatches
   sub-agents that know nothing about it.
4. Leave `bundles: []`. Bundles group rules per worker archetype and need project
   judgement; the user adds them later.
5. Set `critical_snapshot_file` to the first project entrypoint that exists,
   preferring `AGENTS.md`, then `CLAUDE.md`, then `README.md`. Set
   `critical_snapshot_anchor` to the anchor of the heading holding the universal
   rules snapshot. If no such heading exists, write `critical-rules-snapshot` and
   say in the report that the anchor does not resolve yet.
6. Report what was written: rules found, files skipped, whether a first rule was
   seeded, and whether the snapshot anchor resolved.

---

## `seedFirstRule(rulesDir)`

For a project whose `rules_dir` holds no briefing-carrying rule file. Called by
`scaffoldConfig()`, and by `mpi-project-refresh` when it finds the same gap.

Rules are not optional furniture: `mpi-brief-rule` is how a cold sub-agent
learns what the project expects of it, and it has nothing to return until at
least one rule file exists. So seed one - but seed it from evidence, never from
invention.

1. Create `rules_dir` if missing.
2. Write `<rules_dir>/project.md` from `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/rule.md`.
3. Fill it ONLY from what adoption already established - the project profile,
   the knowledge index, `AGENTS.md`/`CLAUDE.md`, and the repo conventions
   actually observed. Every line must trace to something read. A convention you
   cannot point at does not go in.
4. Its `## Sub-Agent Briefing` should let a sub-agent that has read nothing else
   start work: what the project is, the build/test/lint commands that exist, the
   conventions a worker would otherwise violate, and the things it must never do.
   Keep it short. A briefing nobody reads is worth nothing.
5. Where evidence is thin, write the heading with a one-line `TODO:` naming what
   is unknown, and say so in the report. An honest gap beats a confident guess.
6. Register it in the config as `{name: project, file: project.md}`.
7. Show the seeded file to the user in the proposal. It is a rule file, so the
   per-file approval in `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/project-knowledge/updates.md` applies.

One rule is a starting point, not a target. `mpi-end-session` splits specific
rules out of it as real conventions appear in real work.
