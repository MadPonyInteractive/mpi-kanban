# Mpi-Kanban Claude Code Plugin

Mpi-Kanban is distributed as an all-or-nothing Claude Code plugin. Skills,
enforcement hooks, and agents ship from one manifest at
`.claude-plugin/plugin.json`, published through `.claude-plugin/marketplace.json`.

```text
/plugin marketplace add MadPonyInteractive/mpi-kanban
/plugin install mpi-kanban@mad-pony-interactive
```

The pre-1.0 `npx skills` / skills.sh distribution is retired, along with the
Codex plugin manifests, the Codex marketplace bundle, and the Kilo-specific
generated skill trees. Do not restore any of them. This reverses the Phase 7
distribution decision; the user authorized the reversal on 2026-08-09 on the
grounds that Codex and Kilo are no longer used. `${CLAUDE_PLUGIN_ROOT}` is now
the required way to reference a shipped file.

## Companion VS Code Extension

The paired VS Code extension lives next to this repository:

```text
C:\AI\Mpi\Plugins\mpi-kanban-vscode
```

It is published from:

```text
https://github.com/MadPonyInteractive/mpi-kanban-vscode
```

The extension name is `Mpi-Kanban` and the VS Code Marketplace identity should
be `MadPonyInteractive.mpi-kanban`. It is a fork of
`holooooo.markdown-kanban`; keep the original MIT copyright in the extension
`LICENSE` and keep fork attribution in the extension `NOTICE`.

The board contract is `.agents/mpi-kanban/board.json` plus
`.agents/mpi-kanban/tasks/<id>/`. Legacy `.agents/mpi-kanban/kanban.md` boards
are migration inputs only; the plugin can migrate one but can no longer operate
one.

## Source of Truth

- [SPEC.md](./SPEC.md) - design source of truth.
- [PLAN.md](./PLAN.md) - phased implementation state.
- [README.md](./README.md) and [docs/install.md](./docs/install.md) -
  user-facing installation and usage.
- [docs/migrating-to-1.0.md](./docs/migrating-to-1.0.md) - what a project
  running the pre-1.0 pack has to remove or move. Kept in step with the
  `1.0 migration` drift category in `mpi-project-refresh`; change both or
  neither.
- [skills/mpi-lib/](./skills/mpi-lib/) - shared references consumed by the
  workflow skills.
- [hooks/](./hooks/) and [agents/](./agents/) - enforcement and read-only
  helper agents.

If SPEC and PLAN disagree, ask the user before choosing.

## Hard Constraints

- Do not add task-board columns or task-card fields beyond the SPEC board
  contract; the VS Code extension expects the fixed JSON board schema. This
  forbids new columns and new fields; it does not forbid widening an existing
  field's value set. MPI-22 widened `maturity` from 5 to 10 values that way,
  shipping both repos in lockstep. This is why an umbrella card is a large-plan
  `plan.md` with `## Parallel Batch` sections, not a `parent` field.
- Skills are pure Markdown. Shared reference docs live in `skills/mpi-lib/`.
- The plugin ships exactly one version stamp: `version` in
  `.claude-plugin/plugin.json`. It is the field Claude Code uses as the plugin
  update cache key: omit it and updates fall back to commit-SHA semantics,
  duplicate it and there are two stamps to drift apart. `/release` bumps it
  after promoting the changelog; `validate_pack_version()` enforces the match
  against the latest released `## [x.y.z]` changelog heading. Do not add a
  second stamp, and do not move it back to `skills/mpi-lib/SKILL.md`.
- Reference a shipped file as `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/<path>`,
  never project-relative: a bare `scripts/foo.py` resolves against the
  consuming project, not the plugin. `validate_lib_references()` fails the run
  when a skill points at an `mpi-lib` file that does not exist.
- The marketplace entry uses `source: "./"`, so the whole repository becomes
  `${CLAUDE_PLUGIN_ROOT}` - `docs/` and `scripts/` included. `scripts/` is
  maintainer tooling and no shipped skill may invoke it; a script a skill runs
  at runtime belongs in `skills/mpi-lib/scripts/`.
- The plugin is all-or-nothing. Every consuming skill must fail clearly when
  `mpi-lib` is missing and tell the user the install is broken and to reinstall
  the plugin.
- Every hook must exit 0 immediately when the project has no
  `.agents/mpi-kanban/board.json`, must fail closed with a reason rather than
  silently, and must get a case in `scripts/smoke_hooks.py`.
- `guard-card` and `guard-claim` must stay registered against `Bash` as well as
  `Edit|Write|NotebookEdit`. Registered on the edit tools alone they enforce
  nothing: `sed -i`, a `>` redirect, `tee`, `cp` and `mv` walk straight past
  them, and harness modes that tell an agent to prefer shell edits make that the
  default path. This shipped that way in 1.0.0 and was fixed in 1.0.1. Note what
  `scripts/smoke_hooks.py` can and cannot prove: it builds the hook payload
  itself, so it proves a hook's LOGIC and can never prove its MATCHER - 21/21
  was green throughout. Only a live session against the installed plugin proves
  registration, and a session cannot prove its own change, because `hooks.json`
  is read at session start exactly like `skills/`.
- A skill that dispatches `agents/<name>.md` must ship it;
  `validate_plugin.py` checks this.
- `isolation: "worktree"` is not the isolation mechanism for dispatch. A
  worktree branches from the default branch, not the parent's HEAD, and MPI
  commits only at close-out, so a worktree worker cannot see the session's
  uncommitted work. Disjoint ownership declared in the plan is the mechanism.
  `guard-claim` is NOT part of it between same-parent workers: sub-agents share
  the parent's `session_id` in the hook payload (established 2026-08-19 by a PEER agent's probe and not independently re-verified here - a worker's tool call read
  AND mutated the parent's own `state/hooks/` record; MPI-33 carries the
  re-verification as an open checklist box),
  so both guard rules read a sibling's claim as this session's own and allow
  the write. The guard binds between separate Claude sessions, not between
  workers of one. Do not write down that it protects workers from each other
  again unless a payload field distinguishes a worker from its parent. This is
  recorded at the spawn site in `mpi-execute-parallel` and in `mpi-continue`;
  expect a future session to try to "fix" it.
- Project onboarding uses `mpi-init`; project maintenance and mode changes use
  `mpi-project-refresh`. Do not restore separate `mpi-project-setup` or
  `mpi-project-mode` skills unless the user explicitly reverses the lifecycle
  simplification decision.
- Session switching and close-out are two skills, and the boundary is cost.
  `mpi-handoff` commits, pushes, writes the handoff from the plan's running
  notes, and stops. `mpi-end-session` runs the rule/doc, knowledge-healing,
  memory, consolidation, `validating`, and claim-auditor passes once, when the
  job is finished. v1.0 merged them into one skill with a `resume` exit; real
  use showed that made every session switch pay for a close-out - median
  session cost rose 56% and a handoff took about ten minutes - so v1.1 split
  them again. Do not re-merge them, and do not add a knowledge pass, a card
  move, or a sub-agent to `mpi-handoff`.
- `mpi-continue` must keep the active plan's `## Current State` fresh after
  every verified step. That note is what makes a cheap handoff possible; if it
  goes stale, `mpi-handoff` falls back to summarising a full context and the
  cost returns.
- A SKILL.md body is loaded in full on every invocation, so its length is a
  recurring token cost. The budget is 200 lines, enforced by
  `validate_skill_sizes()` in `scripts/validate_plugin.py`. Skills already over
  it when the budget landed carry a grandfathered ceiling that may only shrink;
  the check fails on growth AND on an unlowered ceiling after a shrink. Move
  detail behind a pointer in `skills/mpi-lib/` rather than raising a ceiling,
  and prefer a new small skill over a big one - but keep a step inline when it
  runs every time and an agent would skip the extra read.
- Do not remove `mpi-message`, file claims, `state/sessions/`, heartbeats,
  `mpi-brief-rule`, or `config-ops.md`. MPI-25 decided keep on 2026-07-31 and
  MPI-26 shipped their repair in v0.10.0.
- Session registration is the hooks' job, not the agent's: `session-start.py`
  writes `state/sessions/<claude-session-id>.json` and `guard-claim.py` renews
  it. Asking a skill to do it failed in production - the heaviest user of the
  pack ran eight days with zero session records and zero claims and nothing
  noticed, because the only enforcement was a guard that fires on a CONTESTED
  path and an empty `state/files/` has none. Do not move registration back into
  prose.
- `guard-claim`'s unclaimed-write rule binds only while another session is
  live. Do not "fix" it into an always-on requirement: a solo session has
  nobody to collide with, and a coordination cost charged to every session is
  the exact v1.0 mistake that made a handoff cost a close-out. Cheap when
  alone, strict when not, is the design.
- `mpi-continue` carries the `column` and `maturity` enums inline in its
  `## Card contract` section and defaults discovered work into the active card
  in its `## Discovered work` section. Both deliberately duplicate `mpi-lib`.
  Do not deduplicate them into a lib-only reference: the earlier
  preflight-read version of this rule failed in a month of real use, because
  agents skipped the extra file read when a value looked obvious from
  neighbouring cards. The single code-level source of truth for the maturity
  enum is `skills/mpi-lib/scripts/validate_board.py` (`TASK_MATURITIES`).
  `scripts/validate_plugin.py` imports it rather than keeping a second copy,
  and `validate_maturity_contract_docs()` in that same file checks the inline
  copies in `mpi-continue` and `mpi-execute-parallel` against it at release
  time. Do not remove that check believing the duplication is unguarded prose.
- The GPU lease is deliberately NOT a coordination record. It lives at
  `~/.mpi-kanban/gpu/<index>.lock`, outside every repo, and it is held by an OS
  exclusive lock for the lifetime of one command. Both halves are load-bearing:
  machine-global is the only scope that reaches two agents in two different
  repos, and the OS lock is what removes the heartbeat, the TTL, and the
  stale-reclaim path a `state/` record would need, because the kernel releases
  it on crash and kill. Do not move the lease into `state/`, do not give it a
  heartbeat or an `index.json` entry, and do not decide liveness by reading
  `<index>.owner.json` - that file is display only and a killed holder leaves it
  behind. `guard-gpu` stays opt-in per project; enabling it by default would
  block every `pytest` in every adopted repo the plugin is installed into.
- A contract stated only in prose will drift. Put a check behind it in
  `scripts/validate_plugin.py` or `skills/mpi-lib/scripts/validate_board.py`.

## Maintenance

- Run `python scripts/validate_plugin.py` and `python scripts/smoke_hooks.py`
  before release.
- Release by updating `CHANGELOG.md`, stamping `.claude-plugin/plugin.json`,
  tagging `v<version>`, and pushing the tag.
  `.github/workflows/release.yml` creates the GitHub Release.
- Test this checkout without installing it: `claude --plugin-dir .`. Validate
  the manifest with `claude plugin validate . --strict`.
- Editing `skills/` does not change what an already-running session loads.
  Restart the session before testing behaviour.

## Working Directory

This repository lives at:

```text
C:\AI\Mpi\Plugins\Mpi-Kanban
```

Do not commit anything to other projects from this build. CubricStudio and
other workspaces are integration-test targets only.
