---
name: mpi-brief-rule
description: Extract and return Sub-Agent Briefing text from configured project rules or rule bundles. Use when dispatching sub-agents, resolving worker briefings, or when the user runs "/mpi-kanban:mpi-brief-rule <name>".
---

# mpi-brief-rule Skill

Extract and return the `## Sub-Agent Briefing` section from configured project
rules, or from a configured bundle of rules. Used as a D4 (Agent → Sub-Agent)
dispatch mechanism so sub-agents receive rule briefings without manual
copy-paste.

## Invocation

```
/mpi-kanban:mpi-brief-rule <rule_name>
```

`<rule_name>` is one of the names listed in `.claude/mpi-kanban.local.md`
under the `rules:` frontmatter list, or a name under optional `bundles:`.
The list is project-specific — the plugin ships no hardcoded rules.

## Process

All recipes (`loadConfig`, `resolveRulePath`, `resolveBundle`, `getRuleList`,
`getBundleList`, `loadCriticalSnapshot`, bootstrap notice) live in
`${CLAUDE_PLUGIN_ROOT}/lib/config-ops.md`. Read it once when you actually
need the first recipe — not before.

1. **Load config.** Call `loadConfig()`.
   - If `null` (file missing) → emit the bootstrap notice from
     `lib/config-ops.md` ("No mpi-kanban config found..."), and stop. Do NOT
     auto-create the config.

2. **Resolve the rule or bundle.**
   - Use `getBundleList(config)`. If `<rule_name>` matches a configured
     bundle, call `resolveBundle(config, rule_name)`, resolve each rule in
     order, and return all briefings with headings.
   - Otherwise call `resolveRulePath(config, rule_name)`.
   - If `null` (rule not in config) → list the available rule names from
     `getRuleList(config)` and available bundle names, then stop. Example output:
     ```
     Rule "<rule_name>" is not configured.
     Available rules: components, events, state
     Available bundles: frontend-worker, backend-worker
     ```

3. **Read the rule file.** `Read` the resolved path.
   - If the file is missing on disk (config points at a non-existent file) →
     report the broken path and stop.

4. **Extract the briefing.** Find the `## Sub-Agent Briefing` heading. Return
   everything from that heading up to (but not including) the next `## `
   heading at the same level (or end of file). Return verbatim — no
   modification, no summarization.

5. **Fallback to critical snapshot.** If the rule file has no
   `## Sub-Agent Briefing` section, call `loadCriticalSnapshot(config)` and
   return that instead. Prefix the output with one line:
   ```
   Rule "<rule_name>" has no Sub-Agent Briefing — using critical snapshot from <critical_snapshot_file>:
   ```
   - If the critical snapshot also can't be resolved, report both failures
     clearly and stop.

## Hard rules

- Read-only and non-destructive. Never edit a rule file.
- Briefing text is returned verbatim — no paraphrasing, no summarization.
- Rule and bundle lists are config-driven. The plugin must NOT carry a
  hardcoded list of rule names.
- Board-independent: do NOT auto-create `kanban.md` when this skill runs.

## Notes

- This skill is invoked BY a main agent when dispatching sub-agents — and is
  user-invocable for testing via the `/mpi-kanban:mpi-brief-rule` command.
- Briefing sections may contain markdown formatting; pass it through unchanged.
