# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Cross-repo GPU leases. `skills/mpi-lib/scripts/gpu_lease.py run -- <command>`
  takes a free NVIDIA device, sets `CUDA_VISIBLE_DEVICES` for the child, and
  waits when every device is busy; `status` names the holder of each. Agents in
  different repos were running sweeps on the same card at the same time and
  quietly corrupting each other's results, which file claims cannot prevent -
  they live in one repo's `state/`, key on paths, and bind on writes, and two
  agents in two repos share no file at all.
- The lease is machine-global (`~/.mpi-kanban/gpu/`) and its lock is an OS
  exclusive lock held for the lifetime of the wrapped command. That is the
  design, not an implementation detail: the kernel drops the lock when the
  holder exits, including on crash or kill, so there is no heartbeat to tune, no
  TTL, and no stale-lease reclaim path. It is also a real lock across sessions,
  repos, and windows, which a file claim can never be.
- `guard-gpu` (`PreToolUse`/`Bash`) blocks a GPU command that is not routed
  through the lease. Opt-in per project via `gpu_command_patterns` in
  `.agents/mpi-kanban.local.md`: the plugin is installed globally, and blocking
  every `pytest` in every adopted repo on the chance it touches a GPU would cost
  more than the collisions it prevents. It never checks whether a device is free
  first, because free at check time is not free at run time.
- `mpi-project-refresh` reports a project whose agents run GPU work with no
  `gpu_command_patterns` set, so the opt-in does not have to be remembered per
  repo. Updating the plugin already ships the lease and the guard everywhere;
  only the enforcement line is per-project. Absorbed into the existing line
  budget: the new drift category cost 3 lines and paid for them by compressing
  the pack-install and 1.0-migration bullets, so the skill ends at 335 lines and
  its grandfathered ceiling did not move.
- Multi-GPU is the same loop over more slots. Devices come from `nvidia-smi`, so
  an onboard Intel or AMD adapter never becomes a slot and no agent can be
  handed a GPU too weak to run the work; a machine with no NVIDIA device runs
  the command unleased rather than blocking. A nested `run` inside an existing
  lease passes through instead of deadlocking on its own parent's lock.

## [1.1.1] - 2026-08-13

### Fixed

- `mpi-continue`'s autonomous dispatch now authorizes its own agent, the same
  way `mpi-end-session` § 7 does. 1.1.0 fixed only one of the two call sites
  MPI-29 named, so `dispatcher` was still losing to a standing "do not call
  agents unless the user asked" instruction while the claim auditor no longer
  did. The skill also states which path it took when the agent is absent or
  deliberately skipped, so a silent inline fallback stops looking like a
  dispatch.
- Absorbed into the existing line budget: the dispatcher fix cost 5 lines and
  paid for them by compressing prose in the same sections, so `mpi-continue`
  ends at 601 lines - the same count 1.1.0 shipped - and its grandfathered
  ceiling did not move. (Across both releases it went 592 -> 601; the growth is
  1.1.0's running-notes rule, and 601 is where the budget's ceiling was set.)

A week of real use showed the v1.0 close-out merge was a mistake. Median
session cost rose 56% (149.6k -> 233.3k tokens) and median session length rose
50% (84 -> 126 minutes) after 1.0, and nearly half of all sessions started from
a handoff. Every one of those switches was paying for a full close-out.

### Added

- `mpi-handoff` is back as its own skill, and this time it is cheap. It commits,
  pushes per `push_policy`, writes the handoff JSON, prints the resume block,
  and leaves the card in `doing`. Budget: under two minutes, ~20k tokens. It
  runs no rule/doc pass, no knowledge healing, no memory pass, no board
  validation, no consolidation sweep, no `validating` sweep, and spawns no
  sub-agent - the skill says so explicitly, with the reason, so the passes do
  not creep back in.
- `validate_skill_sizes()` in `scripts/validate_plugin.py` enforces a 200-line
  budget per `SKILL.md`. A skill body is loaded in full on every invocation, so
  its length is a recurring token cost rather than a one-off. The five skills
  already over the budget carry a grandfathered ceiling that may only shrink;
  the check fails both on growth and on a ceiling left unlowered after a
  shrink, so the ratchet cannot quietly slip.
- `skills/mpi-lib/close-out/consolidation.md` holds the umbrella-clustering
  sweep, which `mpi-end-session` now reads only when the board has 8+ `todo`
  cards.
- `mpi-umbrella` makes that sweep something you can ask for. Name the cards, or
  point it at the board and let it propose the clusters. It was previously
  reachable only as something close-out offered, gated at 8+ `todo` cards - so
  "evaluate the cards and make an umbrella", a thing users actually say, matched
  no skill in the pack at all.

### Changed

- The handoff body is read from the active plan's `## Current State`,
  `## Plan Drift`, and `## Preservation Notes` instead of being reconstructed
  from the session. Summarising a large context was the expensive half of a
  handoff, and it produced a worse answer than notes written while the details
  were fresh. When the notes are stale `mpi-handoff` still falls back to
  reconstructing, and says so in the report rather than hiding it.
- `mpi-continue` keeps `## Current State` handoff-ready after every verified
  step: where the work stands, the next action, and any decision or gotcha not
  obvious from the diff.
- `mpi-end-session` is close-out only. The `resume` exit, the handoff JSON
  template, and the two-exit framing are gone; it routes to `mpi-handoff` when
  the work is not finished. 582 -> 394 lines.
- `precompact-handoff` now offers `/mpi-handoff` before compaction drops the
  context, and `session-start` names all three skills.

### Fixed

- The claim auditor now actually gets dispatched. `mpi-end-session` § 7 said
  only "run it here too", which lost every time against a harness instruction
  like "do not call agents unless the user requested it" - so in one repo it
  ran twice in a month, and the two runs it did get caught a false claim about
  a release that would have shipped. The step now states that invoking the
  skill IS the request, mirroring the wording § 8 already uses for the commit,
  and records that the auditor's findings are evidence to re-verify rather than
  edits to apply.
- A skipped close-out step is now visible. The four-bullet report gained a
  `Did not run:` slot, because a silent skip read identically to a clean pass -
  which is exactly how the auditor went unnoticed.

## [1.0.1] - 2026-08-09

The first live install pass found that two of the three enforcement hooks were
enforcing nothing against a shell write. This release closes that.

### Fixed

- `guard-card` and `guard-claim` now watch `Bash` as well as `Edit`, `Write` and
  `NotebookEdit`. Registered against the edit tools alone they enforced nothing
  against a shell write: with a live claim armed, `sed -i` rewrote the claimed
  file with exit 0 one call after the same write through the Edit tool was
  blocked. Harness modes that instruct the agent to prefer `sed`/redirects over
  the edit tools made that bypass the default path, not a corner case. Found by
  the first live install pass; `smoke_hooks.py` could not see it, because a
  synthetic payload never shows which tool calls the harness routes to a hook.
- Both guards now take a list of written paths rather than a single one.
  `_mpi.written_paths()` reads `>`/`>>` redirects, `sed -i`, `tee`, `cp`, `mv`,
  `truncate` and `install` out of a command with `shlex` in `punctuation_chars`
  mode, so a quoted `grep 'x >> y'` is not mistaken for a redirect. A write
  hidden inside `python -c` or an interpreted script is still not seen.

### Removed

- The root `docs/coordination/` copy, a stale fork of the shipped
  `skills/mpi-lib/docs/coordination/`. Nothing referenced it; it is now in
  `REMOVED_PATHS` so it cannot come back.

## [1.0.0] - 2026-08-09

Mpi-Kanban is a Claude Code plugin. It ships hooks and agents, which a skills
pack could not, and it enforces the rules it used to merely state.

**Upgrading is not automatic.** Remove the 15 pre-1.0 skill folders before
installing, or every request matches two skills and one of them runs the old
contract. `docs/install.md` leads with the removal commands, and
`docs/migrating-to-1.0.md` covers the local scaffolding a repo should now drop.

### Added

- **Six enforcement hooks**, registered on install. `guard-git` refuses
  destructive git (`checkout -- <path>`, `checkout .`, `restore` without
  `--staged`, destructive `stash`, `reset --hard`, `clean -f/-d/-x`) while
  letting branch operations through. `guard-card` refuses a code edit when no
  card is in `doing`, with the card contract inline and the edited file named
  so ownership seeds from the first real touch, and refuses a second card in
  one session so the finding folds into the active card. `guard-claim` refuses
  a write to a path another live session claimed. `guard-shell` refuses
  heredocs and multi-line escaped strings. `session-start` reports open claims,
  unresolved messages, active handoffs, and `doing` cards. `precompact-handoff`
  offers a handoff before auto-compaction. Every hook is inert in a project
  with no board, and every block prints its reason.
- **Two read-only agents.** `dispatcher` plans the parallel split; being
  read-only it cannot clobber a worker. `claim-auditor` runs at close-out and
  classifies every factual assertion in the changelog, release notes, and cards
  closed this cycle as PROVEN, UNPROVEN, FALSE, or OVERSTATED, with the commit
  and source line that proves it, worst first, capped at 40 lines.
- **Dispatch without being asked.** `mpi-continue` evaluates every start: when
  ready work splits into two or more disjoint, independently verifiable file
  sets, it dispatches up to four workers and announces the split instead of
  waiting to be asked. It greps the real file footprint rather than trusting
  `files.json`, and reports every card it excluded with the reason.
- **Ownership written at `todo -> doing`**, where it is knowable, rather than
  at card creation, where it was a guess. Board dispatch had never fired
  because no card declared ownership.
- **Umbrella cards are reachable.** `mpi-continue` recognises a large-plan card
  carrying `## Parallel Batch` sections and dispatches its batch. A
  consolidation sweep at close-out and in `mpi-project-refresh` clusters `todo`
  cards by shared file footprint and proposes umbrellas. No new card field: a
  `parent` key would break the VS Code board.
- **`push_policy`** in the project profile - `auto`, `ask`, or `never` - asked
  once by `mpi-init`. Close-out pushes accordingly, retrying a rejected push
  once with `fetch` + `merge --ff-only`, and never rebasing a shared tree.
- **`.agents/mpi-kanban/close-out.md`**, a project extension point close-out
  runs at a defined slot, so a repo keeps its own release or propagation steps
  without forking the pack skill.
- **A shipped behaviour-rules template** covering claims discipline, shell
  style, changelog restraint, multi-agent isolation, and reporting style;
  `mpi-init` writes it and `mpi-project-refresh` keeps it current.
- **Worker archetype stubs** scaffolded from the bundles a project already
  declares in `.agents/mpi-kanban.local.md`.
- **Stale-install detection.** The project records `pack_version` in its
  profile; `mpi-project-refresh` compares it against the installed plugin
  version, reports the installed version every run, and raises a stale-install
  finding above all others. It detects a downgrade or a second machine on an
  old install. It cannot detect a newer upstream release - that needs a network
  call the plugin deliberately does not make - and it never reinstalls itself.
- **`docs/migrating-to-1.0.md`** plus a matching `1.0 migration` drift category
  in `mpi-project-refresh`, so a repo is audited by the skill it already runs.
  Every finding is proposed with its diff, one at a time. Refresh never edits
  the plugin.

### Changed

- **Distribution is the Claude Code plugin marketplace.** Install with
  `/plugin marketplace add MadPonyInteractive/mpi-kanban` then
  `/plugin install mpi-kanban@mad-pony-interactive`. Skills, hooks, and agents
  ship from one manifest.
- **Shared references resolve through `${CLAUDE_PLUGIN_ROOT}`.** The four-path
  discovery probe is gone from every skill, and with it the symlink class of
  bug it caused.
- **Close-out is one skill with two exits.** `mpi-handoff` merged into
  `mpi-end-session`: **resume** writes the handoff JSON, **done** closes the
  card. Both commit, heal project knowledge, run the claim auditor, and resolve
  every card parked in `validating` - evidence closes a card, and genuine human
  judgement is asked for in the same session rather than deferred.
- **Close-out reports are capped at four bullets**: CHANGED, VERIFIED with the
  command that proved it, STILL OPEN, NEXT AGENT NEEDS.
- **Close-out skips the coordination step-0 reads** when the state index shows
  no active sessions, tasks, claims, pending states, or messages, and says so
  in one line.
- **The version stamp moved to `version` in `.claude-plugin/plugin.json`.** It
  is the field Claude Code uses as the plugin update cache key. Still exactly
  one stamp; `validate_pack_version()` binds it to the latest released
  changelog heading.
- Three rules that guaranteed zero dispatch were softened: ownership may be
  inferred by grep as long as the inference is reported, provably disjoint
  footprints may be parallelised whatever produced the plan, and evidence may
  close a card. Workers still never commit or push, `mpi-init` still never
  overwrites project knowledge without approval, and the dispatcher stays
  read-only.

### Removed

- The `npx skills` / skills.sh install channel, and `skills.sh.json`.
- `mpi-nimbalyst-sync`, `state/interop.json` handling, and every
  source-of-truth mode gate. `mpi-project-refresh` offers to delete an orphaned
  `interop.json`.
- Markdown board *operation*. `skills/mpi-lib/kanban-ops/` and the board
  templates are gone, along with the legacy fallbacks in `mpi-continue`,
  `mpi-archive`, `mpi-cleanup`, and close-out. Adoption still migrates a legacy
  `kanban.md` into JSON through `task-board-ops/migrate.md`.
- Codex and Kilo residue: manifests, marketplace bundles, the generated skill
  tree, and the three-runtime acceptance criterion.
- `kanban_entry` from newly written handoff and coordination records. Nothing
  read it. Existing records keep the field.

Skill count is 12 workflow skills plus `mpi-lib`.

### Fixed

- **The `next_id` race that silently overwrote cards.** Two agents creating a
  card at once could both take the same ID, and the writer opened the file in
  write mode, so the loser's card vanished without an error - three overwrites
  in 90 minutes in one repo. `createTask` now claims the ID with
  `os.mkdir(tasks/<id>)` as an exclusive lock, creates `task.json` with
  exclusive-create mode, and retries at the next free ID, up to ten times. The
  cap is ten rather than five because every loser retries at the same ID, so a
  herd of N creators clears one ID per round; at five, an eight-way race
  starved a claimant. `validate_board.py` also asserts `next_id` exceeds every
  card id on the board.
- The version stamp had sat at `0.8.4` through the 0.9.0 and 0.10.0 releases
  because nothing checked it - the exact silent staleness it exists to detect.
  `validate_pack_version()` now fails the release when the stamp does not match
  the latest released changelog heading, and `/release` bumps it after
  promoting the changelog.

### Known limitation

File claims are enforced locally. Within one session and the workers it
dispatches, `guard-claim` is a real lock on every edit. Across two
independently launched Claude Code windows it stays advisory: there is no
native cross-session file lock on any platform, so both windows see the claim
and neither can stop the other's process. Prefer one session dispatching
workers over several windows on one repo.

## [0.10.0] - 2026-08-08

### Fixed

- Coordination could be silently off in an installed pack. `scripts/new_uuid.py`
  lived at the repo root, and only `skills/` ships, so it reached no install -
  and its four references used the project-relative path `scripts/new_uuid.py`
  rather than `<mpi-lib-root>/scripts/new_uuid.py`. Generating a UUID is step 2
  of *Register Or Renew Session*, the first mechanical action in the whole
  coordination lifecycle, so agents hit a missing script at the first write of
  the first record and skipped coordination entirely: no session records, no
  file claims, concurrent sessions overwriting each other. The helper now ships
  at `skills/mpi-lib/scripts/new_uuid.py`, every reference is anchored to
  `<mpi-lib-root>`, and `lifecycle.md`, `messages.md`, `uuid-helper.md`, and
  `mpi-handoff` all carry the dependency-free fallback
  `python -c "import uuid; print(uuid.uuid4())"` so a future packaging slip
  degrades instead of stopping the lifecycle. Regression-guarded in
  `scripts/validate_plugin.py`.
- Nothing created `.agents/mpi-kanban.local.md`, so `mpi-brief-rule` stopped
  with its bootstrap notice for every rule name and every sub-agent dispatched
  from a project started with `mpi-init` received no briefing at all. `mpi-init`
  now scaffolds the config during adoption via `scaffoldConfig()`, filling the
  `rules` list by scanning `rules_dir` for files with a `## Sub-Agent Briefing`
  heading. `mpi-project-refresh` reports a missing or drifted config as a
  finding so projects adopted earlier are told rather than left silent, and the
  bootstrap notice now names the fix and states plainly that a sub-agent
  dispatched right now would run unbriefed. `mpi-brief-rule` still refuses to
  auto-create the file.
- `mpi-project-refresh` and `task-board-ops/read.md` still carried the
  pre-0.9.0 five-value `maturity` enum, so a card legitimately marked
  `research`, `needs-decision`, `blocked`, `deferred`, or `rejected` was read as
  board drift by the reader and by the skill whose job is detecting drift.
  `validate_maturity_contract_docs()` only checked a hand-kept file list and
  missed both. It now also scans every shipped skill doc that enumerates the
  enum and fails on any stale subset, so the next widening cannot leave a copy
  behind.
- Nothing validated `.agents/mpi-kanban/state/files/`, and it had drifted three
  separate ways in this repo's own state: five records used
  `schema: "mpi-kanban/file/v1"`, two carried a UTF-8 BOM, and 16 of 44 stored
  `paths` while the schema documented only `path`. `validate_board.py` now
  checks every claim record - schema, exactly one of `path`/`paths`, a known
  status, and no BOM - and `mpi-project-refresh` reports the same shapes as
  drift.
- Multi-file claims were undocumented. All 16 `paths` records covered 3 to 18
  files each, which is what "module ownership" in `coordination-ops/lifecycle.md`
  means in practice, so this was a gap in the schema rather than sloppy writing:
  a reader following `schemas.md` and matching only `path` silently missed every
  multi-file claim. `paths` is now first-class alongside `path`, an entry ending
  in `/` explicitly claims that subtree, and `lifecycle.md` and `messages.md`
  tell readers to match both fields.

### Added

- Rules bootstrap. A project with no rule file carrying a `## Sub-Agent
  Briefing` heading now gets a first one instead of an empty `rules: []`:
  `seedFirstRule()` in `mpi-lib/config-ops.md` writes `<rules_dir>/project.md`
  from the new `mpi-lib/templates/rule.md`, drafted only from what adoption
  actually read, with `TODO:` lines where evidence is thin. `mpi-init` proposes
  it during adoption and `mpi-project-refresh` proposes it for projects that
  never had one. Both need per-file approval like any rule file.
- `mpi-end-session` now proposes a new rule file when a session established or
  enforced a convention no existing rule covers, and registers it in
  `.agents/mpi-kanban.local.md`. Rules grow from work that proved them rather
  than from a one-time guess at adoption. Capped at one or two per session and
  gated on the same per-file approval.

## [0.9.0] - 2026-07-31

### Fixed

- `mpi-continue` now carries the task-card contract inline: the `column` and
  `maturity` enums, the column/maturity coherence rules, and the reject-list of
  common non-maturity words. The enum previously lived only in `mpi-lib` behind
  a "read these two files first" preflight that agents skipped when a value
  looked obvious from neighbouring cards, so invalid maturities kept reaching
  the board through the pack's most-used skill.

### Added

- A `## Discovered work` rule in `mpi-continue`. Work found while implementing
  the active card now folds into that card by default (checklist item, plan
  edit, validation note) instead of becoming a new card. Genuinely separate
  work is reported under `Noticed, not actioned:` for the user to decide, and a
  card is created only when the user asks in the current request. `mpi-continue`
  had no card-creation path at all, so agents improvised both the card and its
  maturity, producing card sprawl that had to be repaired with umbrella cards.
- `mpi-end-session` reports a `Noticed, not actioned:` list in its final report
  so deferred findings surface instead of dying with the session.
- Widened the task-card `maturity` enum from 5 values to 10. New `todo`
  values: `research` (needs investigation before planning), `needs-decision`
  (understood but a user/product decision is outstanding), `blocked` (ready but
  waiting on another card or an external dependency), `deferred` (deliberately
  postponed). New `done` value: `rejected` (closed without being built; kept as
  a record of the decision). `deferred` was previously treated as an invalid
  value and is now a first-class maturity for the `todo` column. Updated
  `SPEC.md`, `skills/mpi-lib/task-board-ops/`, `skills/mpi-continue/SKILL.md`,
  `skills/mpi-execute-parallel/SKILL.md`, and `scripts/validate_plugin.py`.
- `skills/mpi-lib/scripts/validate_board.py`, a runnable check that validates a
  live JSON task board in any project: board schema and column set, card/column
  and maturity coherence, required fields, link containment, orphaned task
  folders, and event logs. Run it as
  `python <mpi-lib-root>/scripts/validate_board.py <project-root>`; exit 0 means
  consistent, exit 1 prints one line per violation. `mpi-end-session` runs it
  before committing, and it is the gate a board batch must pass before
  dispatch. Nothing an agent ran had previously checked a real board.
- A board batch source in `mpi-execute-parallel`. A batch can now come from
  ready cards on `board.json`, not only from a `## Parallel Batch` section
  inside one plan, so work can be split across cards instead of only within
  one. A card is selectable when it is in `todo` with `maturity: "planned"`, has
  a `plan.md`, carries no required attention, and has ownership derivable from
  `files.json` or a plan `Ownership:` line that is disjoint from every other
  selected card. Every excluded card is reported with its reason. Dispatch
  proceeds without asking, because the plan is the approval.
- A single worker-to-worker messaging case: a worker that needs a file outside
  its ownership files one `mpi-message` record and stops that line of work
  rather than editing or negotiating. No read-receipt loop.
- Board-dispatch routing and trigger phrases in `mpi-continue` ("run the ready
  cards", "dispatch ready cards", "work the board"). `mpi-continue` still never
  spawns workers itself.

### Changed

- `scripts/validate_plugin.py` now imports the maturity enum, the JSON and
  event-log helpers, and the whole board-tree check from
  `skills/mpi-lib/scripts/validate_board.py` instead of keeping its own copy.
  The enum has one code-level source of truth rather than two that had to be
  kept comparable by hand.
- The release-time maturity contract check now also covers the deliberate
  inline enum copies in `mpi-continue` and `mpi-execute-parallel`. Those copies
  are duplicated on purpose; this is what keeps them honest as they multiply.

## [0.8.5] - 2026-06-20

### Changed

- Made the `mpi-continue` post-implementation gate conditional. Plans now
  declare `**Verify mode:**` (`auto` or `user-ux`) in their `## Verification`
  section. For an `auto` card whose self-verification passed, `mpi-continue`
  reports the passing result and continues without stopping for the user; it
  stops only when the card has a `user-ux` surface to judge in the running app,
  or when self-verification failed or could not run. Untagged or legacy plans
  default to `auto`. This removes the per-step "press 1 to verify" prompt for
  work the agent has already verified.
- Taught `mpi-create-plan` and `mpi-create-large-plan` to set `Verify mode:` on
  the plan and, in `scalable-foundation` mode, to front-load architecture,
  pattern, and library decisions and push back before a card is implementable,
  so implementation does not stop mid-flight to ask.
- Added a proactive engineering bar to the `scalable-foundation` mode contract:
  enforce strong patterns where they pay off and proactively name
  future-proofing concerns at planning time.
- `mpi-end-session` now treats its own invocation as the user's explicit request
  to commit the session's touched files, so it commits without deferring to a
  general "ask before committing" instruction. It still never pushes and still
  will not commit over a contested file claim or in `nimbalyst` mode.

## [0.8.4] - 2026-06-10

### Changed

- Added direct task-card state update triggers to `mpi-continue` so requests
  such as `set MPI-42 to validating` load the right workflow instead of
  relying on agents to rediscover board rules from memory or grep.
- Promoted the card-write preflight into the card-writing workflows and
  `task-board-ops/mutate.md`: agents must read `_schema.md` and `mutate.md`
  before writing `column`, `maturity`, or `status`, and must write
  `validation.md` before setting `maturity: "validating"`.
- Clarified that `mpi-lib` reference files are safe for agents to read
  directly, even though `mpi-lib` itself is not a user workflow.

## [0.8.3] - 2026-06-08

### Changed

- Tightened the task-card maturity contract for labels agents were still
  inventing, including `Validated`, `validated`, `validation`, `spec`, and
  other process words. `moveTask` now documents column movement as maturity
  reconciliation, `read.md` reports invalid maturity drift, and refresh/repair
  guidance calls these out as board repair findings.
- Added validator coverage to keep the maturity enum and common invalid
  examples documented in the spec, shared task-board references, and default
  project profile template.

## [0.8.2] - 2026-06-05

### Changed

- Surface the `maturity` enum at write time so agents stop guessing it.
  `mpi-lib/task-board-ops/mutate.md` now opens with the allowed values
  (`idea`, `planned`, `in-progress`, `validating`, `complete`), the column
  coherence rules, and an explicit reject-list: `active`, `accepted`, `done`,
  `deferred`, `implementing`, and `implementation` are not maturity values.
- `mpi-lib/templates/project-profile.md` gains a "Task Board Card Contract"
  section with the maturity-by-column table, so the enum is visible in a
  read-first doc without opening the shared library.
- `mpi-end-session` now auto-corrects an invalid or column-incoherent
  `maturity` on a touched card before any board move, printing a one-line note.

### Fixed

- Cards that agents marked with non-enum maturity values (for example
  `deferred`, `active`, or `implementation`) rendered as red invalid cards in
  the VS Code board. The guidance above prevents those writes; a `doing` card
  under active work is `in-progress` (yellow), not `implementation` or `idea`.

## [0.8.1] - 2026-06-05

### Changed

- `mpi-create-plan`, `mpi-continue`, and `mpi-lib/task-board-ops/mutate.md` now
  enforce the `To do -> Doing -> Done` lifecycle: implementation must run through
  `mpi-continue`/`beginImplementation`, which moves a card into `Doing` before
  any edit. Inline implementation from a `todo` card is no longer allowed
  (MPI-18).
- `mpi-end-session` auto-corrects a `todo` card that carries real implementation
  work through `Doing` (with a one-line warning) before moving it to `Done`,
  instead of skipping the `Doing` phase (MPI-18).
- Retired legacy Markdown from the main product surface: `README.md`, `SPEC.md`,
  and `mpi-init` now present `kanban.md` only as a brief migration/compatibility
  note, not a primary workflow (MPI-15).

## [0.8.0] - 2026-05-31

### Added

- Added `mpi-message` for same-filesystem async coordination messages between
  agents, sessions, roles, tasks, files, users, and explicit peer workspaces.
- Added shared `mpi-lib` message and workspace-discovery references for
  `.agents/mpi-kanban/state/messages/` and VS Code `.code-workspace` scope.
- Added a message-bus smoke harness and validator checks for message records,
  open-message index pointers, claim negotiation, peer routing, and resolved
  message archival.

### Changed

- Workflow skills now check relevant open messages only at safe async
  boundaries such as continue, parallel execution, handoff, cleanup, and
  end-session.
- Documentation now describes the v0.8.0 model: one Kanban root per work
  context, with separate roots communicating through explicit same-machine
  peer messages.

## [0.7.2] - 2026-05-31

### Changed

- Folded read-only card lookup into `mpi-continue` instead of shipping a
  standalone `mpi-show` skill, keeping the installable pack at 14 skills for
  `npx skills`.

## [0.7.1] - 2026-05-31

### Changed

- Tightened post-migration cleanup so JSON-board projects treat legacy
  `kanban.md` files as moved/tombstoned compatibility artifacts, and refresh
  validation flags boot docs that still route active work through Markdown.

### Added

- `mpi-show` read-only workflow for natural board-card lookup requests such as
  "what is MPI-5?" or "show the <title> card".

## [0.7.0] - 2026-05-31

### Added

- JSON task board contract with `.agents/mpi-kanban/board.json`,
  `.agents/mpi-kanban/events.jsonl`, and task workspaces under
  `.agents/mpi-kanban/tasks/<id>/`.
- Shared `mpi-lib/task-board-ops/` references for JSON board schema, read,
  mutation, migration, and validation behavior.
- `mpi-nimbalyst-sync` for Nimbalyst source-of-truth mode, detection, and
  explicit import/export snapshot boundaries.
- Validator coverage for JSON board templates and live board/task workspace
  consistency.

### Changed

- `mpi-init` is now the single project onboarding/adoption skill. It owns JSON
  board bootstrap or migration, profile/index creation, project mode selection,
  interop mode initialization, and freeform backlog import.
- `mpi-project-refresh` is now the existing-project maintenance skill. It owns
  project knowledge drift checks, board/state consistency, and later project
  mode changes.
- Workflow skills now treat `board.json` as the primary human board once it
  exists, with fixed `To do`, `Doing`, and `Done` columns.
- Legacy Markdown boards remain readable as migration inputs or snapshots, not
  competing live sources of truth after JSON-board migration.
- Nimbalyst interop docs and workflow references map tracker state into the
  JSON board model instead of restoring legacy MPI lifecycle columns.
- Validator interop checks now use tracked templates rather than ignored local
  `.agents/` state, so release validation is reproducible from a clean checkout.

### Removed

- Retired separate `mpi-project-setup` and `mpi-project-mode` skills before
  release; their behavior is folded into `mpi-init` and `mpi-project-refresh`.

## [0.6.1] - 2026-05-24

### Changed

- Documentation updates and project migration housekeeping.

## [0.6.0] - 2026-05-23

### Added

- `mpi-lib` support skill carrying shared reference docs for the all-or-nothing
  Agent Skills pack.
- `skills.sh.json` pack metadata and `docs/install.md` npx install docs.

### Changed

- Distribution is now npx-only through skills.sh:
  `npx skills add MadPonyInteractive/mpi-kanban --all -y -g`.
- Workflow skills now resolve shared references through the sibling `mpi-lib`
  skill instead of plugin-root variables.

### Removed

- Removed Claude Code plugin manifest and Codex plugin/marketplace bundle.
- Removed Kilo-specific generated skill packaging, install docs, marketplace
  runbook, and template. Existing users should reinstall with:
  `npx skills add MadPonyInteractive/mpi-kanban --all -y -g`.

## [0.5.1] - 2026-05-23

### Changed

- Clarified that `mpi-project-setup` and `mpi-project-refresh` may propose new
  `.claude/rules/*.md` files, not only edits to existing rules, when reusable
  project-specific conventions need dedicated briefable rule files.

## [0.5.0] - 2026-05-23

### Added

- Durable project knowledge layer so fresh sessions stop rediscovering
  architecture, conventions, and intent each session. New reference docs under
  `lib/project-knowledge/` cover profile schema, index schema, adoption,
  context-budget indexing, and update/approval rules. Templates added for
  `project-profile.md` and `project-knowledge-index.md`.
- Project mode contract and intentional-engineering guardrails at
  `lib/project-intent/modes.md`. Default mode is `scalable-foundation`.
- Three new skills bringing the surface to 14:
  - `mpi-project-setup` — builds an adoption map and waits for approval before
    writing profile/index.
  - `mpi-project-mode` — records mode-change rationale and migration notes
    without rewriting code.
  - `mpi-project-refresh` — audits drift and runs lightweight mode reassessment.
- Phase 4 plan documents project-knowledge architectural intent and parallel
  implementation strategy.

### Changed

- Existing skills now consume project knowledge when present:
  - `mpi-brainstorm` routes new-project ideas to `mpi-project-setup`.
  - `mpi-create-plan` and `mpi-create-large-plan` read profile/index.
  - `mpi-continue` reads profile/index before the Continue Brief; brief gains
    Project mode and Conventions-in-play fields.
  - `mpi-handoff` records `project_knowledge` pointers in canonical JSON.
  - `mpi-end-session` runs a lightweight refresh on session-touched files.
  - `mpi-cleanup` treats profile/index as active by default and defers drift
    cleanup to `mpi-project-refresh`.
- SPEC, README, AGENTS, PLAN, plugin manifests, and marketplace description
  updated to reflect the 14-skill surface. Kanban schema unchanged.

## [0.4.3] - 2026-05-22

### Changed

- Parallel agents are now the default for eligible large-plan work rather than
  an opt-in extra, with ownership and verification safety gates intact. SPEC and
  README describe parallel investigation and disjoint-ownership parallel batches
  as the default.
- `mpi-brainstorm` and `mpi-create-plan` route parallel-capable work to
  `mpi-create-large-plan`; compact plans never carry parallel batches.
- `mpi-create-large-plan` defaults to parallel investigation sub-agents and to
  writing Parallel Batch sections when ownership is disjoint and verification is
  batch-safe.
- `mpi-continue` routes a valid next batch to `mpi-execute-parallel` instead of
  running it sequentially, and still never spawns workers itself.
- `mpi-execute-parallel` reworded from opt-in to default-for-eligible with
  refusal gates intact.

## [0.4.2] - 2026-05-21

### Added

- Shared coordination lifecycle reference docs under `lib/coordination-ops/`
  covering session registration, task records, file claims, pending file state,
  handoffs, stale reclaim, cleanup, and commit ownership.
- Phase 2 plan documenting local lifecycle automation and the decision to keep
  VS Code visualization deferred while using existing kanban tags as
  display-only summaries.
- README now shows the VS Code companion extension board screenshot.
- GitHub Actions workflow `validate.yml` runs on push/PR to main. Validates plugin
  manifest, marketplace manifest, every `skills/*/SKILL.md` frontmatter, and
  flags any symlink that would break Windows install.
- GitHub Actions workflow `release.yml` runs on `v*` tag push. Re-runs the
  validator, confirms the tag matches `plugin.json` version, extracts the
  matching CHANGELOG section, and creates a GitHub Release.
- `scripts/validate_plugin.py` — local equivalent of the CI validator. Run before
  pushing if you want to catch issues without waiting on CI.
- Native Codex plugin manifest at `.codex-plugin/plugin.json`, pointing to the
  shared `skills/` tree and exposing `$mpi-*` starter prompts.
- `scripts/register_codex_plugin.py` registers a local checkout in a Codex
  marketplace using Python 3.8+ standard-library APIs.

### Changed

- `mpi-continue`, `mpi-execute-parallel`, `mpi-handoff`, `mpi-end-session`, and
  `mpi-cleanup` now reference the shared `.agents/mpi-kanban/state/` lifecycle
  model.
- Codex local registration now rejects plugin paths outside the marketplace root
  instead of writing a marketplace entry Codex will skip.
- `update_live.py` now mirrors the plugin to `~/plugins/mpi-kanban`, registers
  that home-local path, and runs `codex plugin add` so Codex installs the
  current local plugin build.
- README now explains the multi-agent coordination workflow in user-facing
  terms: roles, file claims, pending state, integration, and display-only tags.
- README now documents that local Codex plugin paths must resolve under the home
  directory so the generated marketplace path starts with `./`, and that users
  must run `codex plugin add mpi-kanban@mad-pony-interactive` after registration.
- AGENTS and CLAUDE project instructions now describe the current dual Claude
  cache and Codex install behavior of `update_live.py`.
- Codex direct invocation docs and starter prompts now use the actual
  plugin-prefixed skill names, such as `$mpi-kanban:mpi-continue`.
- Shared coordination docs now distinguish active write claims from pending file
  provenance, and separate file ownership from commit ownership.
- Skill descriptions and docs now distinguish Claude Code slash commands from
  Codex `$mpi-*` skill invocation.

## [0.4.1] - 2026-05-13

### Changed

- Marketplace renamed from `mpi-local` to `mad-pony-interactive` so future
  MadPonyInteractive plugins can live under the same marketplace.
- README rewritten to lead with the public GitHub install path
  (`/plugin marketplace add MadPonyInteractive/mpi-kanban`) instead of local
  directory install.
- `update_live.py` now reads the destination version from `plugin.json` rather
  than hardcoding `0.2.0`, so the cache directory always matches the declared
  plugin version.

### Documented

- VS Code extension fork (`MadPonyInteractive.mpi-kanban`) and its publish
  sequence relative to this plugin.

## [0.4.0] - earlier

### Changed

- Workflow skills redesigned. `mpi-write-plan` split into `mpi-create-plan` and
  `mpi-create-large-plan`. `mpi-execute-next` split into `mpi-execute-parallel`
  and `mpi-continue`. New skill `mpi-cleanup` added for workflow artifact
  garbage collection.

[Unreleased]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.10.0...v1.0.0
[0.10.0]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.5...v0.9.0
[0.8.5]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.4...v0.8.5
[0.8.4]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.3...v0.8.4
[0.8.3]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/MadPonyInteractive/mpi-kanban/compare/v0.7.2...v0.8.0
[0.7.2]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.7.2
[0.7.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.7.1
[0.7.0]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.7.0
[0.6.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.6.1
[0.6.0]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.6.0
[0.5.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.5.1
[0.5.0]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.5.0
[0.4.3]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.3
[0.4.2]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.2
[0.4.1]: https://github.com/MadPonyInteractive/mpi-kanban/releases/tag/v0.4.1
