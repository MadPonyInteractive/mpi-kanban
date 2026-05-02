---
name: mpi-brief-rule
description: Extract and return the "## Sub-Agent Briefing" section from a project rule file, looked up via per-project config (.claude/mpi-kanban.local.md). Use when dispatching sub-agents or when the user runs "/mpi-brief-rule <name>".
---

# mpi-brief-rule Skill

Extract and return the `## Sub-Agent Briefing` section from a project rule
file. Used as a D4 (Agent → Sub-Agent) dispatch mechanism so sub-agents
receive rule briefings without manual copy-paste.

## Invocation

```
/mpi-brief-rule <rule_name>
```

`<rule_name>` is one of the names listed in
`.claude/mpi-kanban.local.md` under the `rules:` frontmatter list. The list is
project-specific — the plugin ships no hardcoded rules.

## Process

Read `lib/config-ops.md` once for the parsing recipes. Then:

1. **Load config.** Call `loadConfig()`.
   - If `null` (file missing) → emit the bootstrap notice from
     `lib/config-ops.md` ("No mpi-kanban config found..."), and stop. Do NOT
     auto-create the config.

2. **Resolve the rule.** Call `resolveRulePath(config, rule_name)`.
   - If `null` (rule not in config) → list the available rule names from
     `getRuleList(config)` and stop. Example output:
     ```
     Rule "<rule_name>" is not configured.
     Available rules: components, events, state
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
- The rule list is config-driven. The plugin must NOT carry a hardcoded list
  of rule names.
- Board-independent: do NOT auto-create `kanban.md` when this skill runs.

## Notes

- This skill is invoked BY a main agent when dispatching sub-agents — and is
  user-invocable for testing via the `/mpi-brief-rule` command.
- Briefing sections may contain markdown formatting; pass it through unchanged.
