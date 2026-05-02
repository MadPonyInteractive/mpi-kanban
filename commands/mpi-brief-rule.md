---
name: mpi-brief-rule
description: Return the "## Sub-Agent Briefing" section from a configured project rule file. Usage: /mpi-brief-rule <rule-name>.
---

Invoke the `mpi-brief-rule` skill with the rule name passed as an argument
(`$ARGUMENTS`). Follow the skill's process — load config, resolve the rule,
extract the briefing, fall back to the critical snapshot if the rule has no
briefing section.
