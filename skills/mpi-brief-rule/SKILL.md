---
name: mpi-brief-rule
description: MPI workflow pack - Extract and return Sub-Agent Briefing text from configured project rules or rule bundles. Use when dispatching sub-agents, resolving worker briefings, or when the user invokes "mpi-brief-rule <name>".
---

# mpi-brief-rule Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`
Extract and return the `## Sub-Agent Briefing` section from configured project
rules, or from a configured bundle of rules. Used as a D4 (Agent Ã¢â€ â€™ Sub-Agent)
dispatch mechanism so sub-agents receive rule briefings without manual
copy-paste.

## Invocation

```
mpi-brief-rule <rule_name>
```

`<rule_name>` is one of the names listed in `.agents/mpi-kanban.local.md`
under the `rules:` frontmatter list, or a name under optional `bundles:`.
The list is project-specific Ã¢â‚¬â€ the plugin ships no hardcoded rules.

## Process

All recipes (`loadConfig`, `resolveRulePath`, `resolveBundle`, `getRuleList`,
`getBundleList`, `loadCriticalSnapshot`, bootstrap notice) live in
`<mpi-lib-root>/config-ops.md`. Read it once when you actually
need the first recipe Ã¢â‚¬â€ not before. Resolve the file from `<mpi-lib-root>`.

1. **Load config.** Call `loadConfig()`.
   - If `null` (file missing), emit the bootstrap notice from
     `<mpi-lib-root>/config-ops.md` ("No mpi-kanban config found..."), and stop.
     Do NOT auto-create the config here. `mpi-init` is the skill that creates
     it, and `mpi-project-refresh` reports it missing; the notice tells the user
     to run one of them. Say plainly that a sub-agent dispatched right now would
     receive no briefing at all, so a silent no-op is not mistaken for success.

2. **Resolve the rule or bundle.**
   - Use `getBundleList(config)`. If `<rule_name>` matches a configured
     bundle, call `resolveBundle(config, rule_name)`, resolve each rule in
     order, and return all briefings with headings.
   - Otherwise call `resolveRulePath(config, rule_name)`.
   - If `null` (rule not in config) Ã¢â€ â€™ list the available rule names from
     `getRuleList(config)` and available bundle names, then stop. Example output:
     ```
     Rule "<rule_name>" is not configured.
     Available rules: components, events, state
     Available bundles: frontend-worker, backend-worker
     ```

3. **Read the rule file.** `Read` the resolved path.
   - If the file is missing on disk (config points at a non-existent file) Ã¢â€ â€™
     report the broken path and stop.

4. **Extract the briefing.** Find the `## Sub-Agent Briefing` heading. Return
   everything from that heading up to (but not including) the next `## `
   heading at the same level (or end of file). Return verbatim Ã¢â‚¬â€ no
   modification, no summarization.

5. **Fallback to critical snapshot.** If the rule file has no
   `## Sub-Agent Briefing` section, call `loadCriticalSnapshot(config)` and
   return that instead. Prefix the output with one line:
   ```
   Rule "<rule_name>" has no Sub-Agent Briefing Ã¢â‚¬â€ using critical snapshot from <critical_snapshot_file>:
   ```
   - If the critical snapshot also can't be resolved, report both failures
     clearly and stop.

## Hard rules

- Read-only and non-destructive. Never edit a rule file.
- Briefing text is returned verbatim Ã¢â‚¬â€ no paraphrasing, no summarization.
- Rule and bundle lists are config-driven. The plugin must NOT carry a
  hardcoded list of rule names.
- Board-independent: do NOT auto-create `kanban.md` when this skill runs.

## Notes

- This skill is invoked BY a main agent when dispatching sub-agents Ã¢â‚¬â€ and is
  user-invocable for testing through the installed Agent Skills invocation.
- Briefing sections may contain markdown formatting; pass it through unchanged.




