# mpi-end-session - growth loop

Read from `mpi-end-session` step 2 only when this session PROVED an uncovered
convention: the same friction repeated here or in a recorded earlier session.
Then propose the artifact that would have prevented it. Four kinds, one loop:

| What repeated | Propose |
|---|---|
| A convention no rule file covers | a `.agents/rules/*.md` file, drafted from `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/templates/rule.md`, with a `## Sub-Agent Briefing` section, added to the `rules` list in `.agents/mpi-kanban.local.md` so `mpi-brief-rule` can dispatch it |
| The same worker briefing assembled by hand more than once | a `.claude/agents/<name>.md` definition |
| The same multi-step procedure typed out again | a project skill under `.claude/skills/` |
| A prose rule that fired and was ignored, or a mistake a check could have caught | a hook under `.claude/hooks/` plus its `settings.json` registration |

Rules for the loop, all four kinds:

- **Cap 1-2 proposals per session.** More is noise and gets ignored.
- **Only from repetition that already happened** here or in a recorded earlier
  session. **Never propose from directory structure** - an empty
  `.claude/agents/` directory is not evidence anyone needs an agent.
- Propose as a `Your call:` line with the agent's pick; nothing created before
  a yes. Short bullets, no prose bloat.
