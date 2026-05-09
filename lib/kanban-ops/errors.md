# kanban-ops/errors — error cases

Read this when a kanban operation hits an unexpected state. Skills MUST
surface errors to the user instead of silently editing around them.

| Case | Detection | Behavior |
|---|---|---|
| Duplicate title | `findEntry` returns a hit before `createEntry` runs | Abort with `Error: Duplicate kanban entry title: "<title>". Resolve manually before continuing.` |
| Missing column | One of the 4 H2 headings is absent | Abort with `Error: kanban.md is missing the "## <COLUMN>" heading. Restore from templates/kanban.md.` |
| Malformed entry | `### ` block missing required metadata bullets (tags, priority, defaultExpanded) | Report which entry, do not auto-fix. |
| Unknown metadata field | Bullet matches `- (\w+):` where `\w+` is outside the locked schema | Refuse to write it. If reading, ignore + warn. |
| `Plan file:` ref absent on PLANNING/IMPLEMENTING entry | Body fence contains no matching line | Abort the move and ask the user which plan to attach. |
