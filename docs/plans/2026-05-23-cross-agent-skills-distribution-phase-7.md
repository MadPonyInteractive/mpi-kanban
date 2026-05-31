# Cross-Agent Skill Distribution Refactor - Phase 7

## Project Mode

`scalable-foundation` (per `.agents/mpi-kanban/project-profile.md`).

## Status

**Plan only â€” not approved yet. Read full investigation in handoff
`.agents/mpi-kanban/state/handoffs/a681c21d-bb5c-4905-976c-56d612fa17d8.json`
before continuing.**

Supersedes the in-flight Phase 6 KiloCode-narrow work. Phase 6 sub-phases 6.4
(Kilo marketplace PR) and 6.7 (release 0.6.0) are paused. Phase 6
deliverables that survive (validator additions, project-knowledge layer
edits, AGENTS.md pointer) stay; Phase 6 deliverables that get replaced are
listed in `## Replaces / Drops` below.

## Current State (2026-05-23)

- Repo at commit `8f15f69`. Branch `main`. Tree dirty with 0.6.0 manifest bumps,
  Phase 6 docs, SPEC Â§14 KiloCode block, knowledge-index update, file-claim
  records, and `.claude/commands/update-live.md` Pre-release test loop section.
- Manifests bumped to `0.6.0` locally but no release tag pushed.
- Claude user-scope install patched at `~/.claude/plugins/installed_plugins.json`
  to point at `~/.claude/plugins/cache/.../0.6.0/` (cache dir mirrored via
  `update_live.py`).
- Kilo verified discovering MPI skills in fresh VS Code workspace via
  `~/.agents/skills/` user-global path.
- Phase 6 commits already pushed: `8b2350c`, `20a3cbc`, `116eda3`, `a2904f3`,
  `8f15f69`.

## Goals

- Make Mpi-Kanban skills installable into any of 40+ Agent-Skills-compatible
  agents (Claude Code, Codex, Kilo, OpenCode, Cursor, Copilot, Windsurf,
  Cline, Gemini CLI, Goose, OpenHands, Roo, etc.) via a single `npx skills`
  command.
- Keep context bloat minimal: shared `lib/` reference content lives in ONE
  place (a sibling `mpi-lib` skill) that all 14 workflow skills read on
  demand, not duplicated per-skill.
- Preserve all-or-nothing pack semantics: install command includes `--all`,
  documentation calls this out, partial installs are explicitly unsupported.
- Drop Kilo-specific packaging (marketplace PR, generator, install docs).
  skills.sh covers Kilo plus 39 other agents in one channel.

## Non-Goals

- Pre-resolving the mpi-lib path at install time. Each skill discovers the
  install path at first use via plain filesystem checks and Read.
- Preserving Claude/Codex plugin compatibility. The old Claude plugin and Codex
  marketplace install paths are removed; `npx skills add --all` is the only
  supported install and update channel after Phase 7.
- Backporting these changes to 0.5.1. Phase 7 ships as the next release.

## Architecture Decisions

0. **Hard drop of Claude plugin + Codex plugin + Codex marketplace bundle.**
   `npx skills add MadPonyInteractive/mpi-kanban --all -y -g` becomes the
   ONLY install command. Existing Claude `/plugin install` and Codex
   marketplace install paths are deleted from the repo entirely, not left as
   alternates. The 0.6.0 release notes mark them deprecated with a one-line
   migration path. Trade-off accepted: any user who previously installed via
   `/plugin install` must reinstall via `npx skills`. Risk noted: if a future
   feature needs deep Claude plugin integration (hooks, plugin-only frontmatter
   fields, plugin-scope settings), this decision will block it until reversed.

1. **Sibling skill for shared lib.** A new 15th skill, `mpi-lib`, contains the
   entire current `lib/` tree as flat folders under the skill root. The other
   14 skills locate it via filesystem search at first use, cache the path for
   the session, and read individual lib files on demand. No `${CLAUDE_PLUGIN_ROOT}`,
   no `!` injection (Claude Code-only feature).

2. **Path discovery via candidate list.** Each consuming SKILL.md instructs
   the agent to probe a short list of standard install paths and use the
   first hit:

   ```
   1. ~/.agents/skills/mpi-lib/...        (npx skills global)
   2. .agents/skills/mpi-lib/...          (npx skills project)
   3. ~/.claude/skills/mpi-lib/...        (Claude Code personal scope)
   4. .claude/skills/mpi-lib/...          (Claude Code project scope)
   ```

   Agent runs once per session, caches resolved root path, reads any file by
   `<cached_root>/<sub/path>.md`. The `.claude/skills` probes are for manual
   or Agent Skills-compatible Claude installs only; the old Claude plugin cache
   is deliberately not part of the supported path contract.

3. **All-or-nothing pack signaled in docs + skill descriptions.** Every
   SKILL.md description begins with "MPI workflow pack â€”". The install
   command published everywhere is:

   ```
   npx skills add MadPonyInteractive/mpi-kanban --all -y -g
   ```

   `skills.sh.json` groups the full current skill surface under a single "MPI
   Workflow" pack.

4. **skills.sh-only distribution.** `npx skills add MadPonyInteractive/mpi-kanban --all -y -g`
   becomes the canonical install and update path for every supported agent.
   Claude `/plugin install` and Codex marketplace routes are removed from the
   repo and docs. Compatibility with those install routes is intentionally not
   maintained. The migration note tells existing users to uninstall the old
   plugin package and reinstall through `npx skills`.

5. **Drop the Kilo-specific generator.** `scripts/build_kilo_skills.py` and
   `skills-kilo/` are deleted. Inlining is no longer required because each
   skill's references are already inside the skill folder (`mpi-lib` for
   shared content; per-skill `references/` for skill-private content).

6. **Project mode unchanged.** Stays `scalable-foundation`. The refactor is
   a distribution-layer change, not a structural one.

## Investigation Findings (Carryover From Phase 6 Decision Spike)

- skills.sh is the **open Agent Skills ecosystem** registry. Skills-only,
  no plugins concept. Repo-based. `npx skills add owner/repo` clones the
  repo, discovers SKILL.md files (top-level or in `skills/` subdir), and
  installs to per-agent dirs.
- Skills CLI supported flags: `-g/--global`, `-a/--agent`, `-s/--skill`,
  `-l/--list`, `--copy`, `-y/--yes`, `--all`, `--full-depth`.
- Supported agents (`npm view skills` keywords): Claude Code, Codex, Kilo,
  OpenCode, Cursor, Copilot, Windsurf, Cline, Gemini CLI, Goose,
  OpenHands, Roo, Aider, Continue, Cortex, Crush, Devin, Droid,
  Firebender, Junie, Kimi, Kiro, Kode, MCPJam, Mistral Vibe, Mux,
  Neovate, Pi, Pochi, Qoder, Qwen, Replit, Rovodev, Tabnine, Trae,
  Warp, Zencoder, Adal, and a `universal` target. ~40 agents.
- Skill discovery on install copies the entire skill folder (every file
  beneath `skills/<name>/`), so siblings like `mpi-lib/coordination-ops/`
  travel with the skill. Verified locally: `npx skills add MadPonyInteractive/mpi-kanban -l`
  listed all 14 MPI skills; `--all -y --copy` deployed them under
  `~/AppData/Local/Temp/.agents/skills/mpi-*/` with the expected per-skill
  contents.
- Sibling files load **on demand** per the Agent Skills standard's
  "progressive disclosure" model. They do NOT enter context until SKILL.md
  instructs the agent to read them. Confirmed in Claude Code official docs:
  "long reference material costs almost nothing until you need it"; and
  "Move detailed reference material to separate files."
- `!` (backtick-bang) shell injection is Claude Code-specific, not in the
  Agent Skills standard. Cannot rely on it for cross-agent path resolution.
- Reference repos for the multi-skill / shared-content pattern:
  - `vercel-labs/skills` â€” multi-skill repo with `skills/<name>/`, plus
    repo-level `packages/` for shared build helpers. Each skill is
    self-contained (e.g. `react-best-practices/rules/*.md`). No shared
    runtime lib; duplication is acceptable in their model.
  - `playwright` skill â€” uses `references/`, `scripts/`, `agents/`,
    `assets/` sibling folders.
  - `shadcn` skill â€” uses `rules/`, `agents/`, `assets/`, `evals/` siblings.
- Decision: shared-lib pattern is NON-standard for skills.sh skills but
  acceptable in our case because we treat the pack as a single unit and own
  the install command. Trade-off accepted by user: partial installs break,
  documented explicitly.

## Replaces / Drops

Hard drops (Claude/Codex plugin identity is going away):

- `.claude-plugin/plugin.json` â€” delete. Mpi-Kanban stops being a Claude
  Code plugin. Existing `/plugin install mpi-kanban@mad-pony-interactive`
  becomes obsolete. CHANGELOG records the deprecation.
- `.codex-plugin/plugin.json` â€” delete. Mpi-Kanban stops being a Codex
  plugin / marketplace entry.
- `plugins/MadPonyInteractive/mpi-kanban/` directory (Codex marketplace
  bundle: `plugins.json`, `icon.svg`, `composerIcon` reference) â€” delete.
- `.agents/plugins/marketplace.json` (public Codex marketplace manifest) â€”
  delete.
- `scripts/register_codex_plugin.py` â€” delete.
- `scripts/validate_plugin.py` Claude/Codex/marketplace checks
  (`validate_codex_marketplace_bundle`, `validate_public_codex_marketplace`,
  `PUBLIC_CODEX_MARKETPLACE` constant, manifest sync check) â€” delete. Keep
  only skill-level checks: SKILL.md frontmatter validity, `mpi-lib` present
  + referenced, `skills.sh.json` parseable.
- `update_live.py` â€” repurpose. Drop the Claude plugin cache mirror, drop
  the Codex marketplace install. Becomes a thin "mirror current tree into
  `~/.agents/skills/` so local edits are testable in skills.sh-installed
  agents" helper. Or delete entirely if `npx skills add ./<local-path>`
  serves the same need.
- `.claude/commands/release.md` â€” rewrite. No more 3-manifest version
  sync (no manifests left). Only thing that changes per release: git tag
  + GitHub release notes. Skills.sh users see new content automatically on
  next `npx skills update`.
- `.github/workflows/release.yml` â€” review and likely simplify; no plugin
  validator step needed if manifests are gone.

Phase 6 deliverables also dropped (skills.sh covers the same need):

- `scripts/build_kilo_skills.py` â€” delete; no inlining needed once `mpi-lib`
  carries shared content.
- `skills-kilo/` â€” delete (currently gitignored).
- `docs/kilocode-install.md` â€” replace with `docs/install.md` (skills.sh only).
- `docs/kilocode-marketplace-submission.md` â€” delete.
- `templates/kilo.jsonc` â€” delete.
- SPEC.md Â§14 KiloCode Distribution â€” rewrite to "Cross-Agent Skill
  Distribution via skills.sh". Keep section number; replace contents.
- SPEC.md Â§2 Packaging and Invocation â€” rewrite. Claude/Codex plugin
  packaging language is now historical. Distribution = npx skills only.
- `scripts/validate_plugin.py` `validate_kilo_assets`,
  `validate_kilo_skill_limits` â€” fold into the new
  `validate_universal_skill_limits` (Agent Skills standard limits).
- `.agents/mpi-kanban/project-profile.md` Architecture Summary +
  Important Commands â€” rewrite. No `.claude-plugin/` or `.codex-plugin/`
  manifest mentions, no `/release` 3-manifest sync, no `update_live.py`
  for Claude/Codex caches.
- `.agents/mpi-kanban/project-knowledge-index.md` `kilocode-packaging`
  topic + any `release-and-live-copy` references to plugin manifests â€”
  rewrite.
- AGENTS.md KiloCode pointer + any "Codex plugin" framing â€” replace with
  skills.sh-first install instructions.
- CHANGELOG.md â€” add a `### Removed` block under the new release explaining
  the hard drop, with the migration line:

  ```
  Removed: Claude Code plugin manifest and Codex marketplace bundle.
  Install Mpi-Kanban with:
      npx skills add MadPonyInteractive/mpi-kanban --all -y -g
  Old users on `/plugin install mpi-kanban@mad-pony-interactive` should
  `/plugin uninstall mpi-kanban@mad-pony-interactive --scope user` and
  reinstall via the npx command above.
  ```

What survives:

- `.claude/commands/update-live.md` Pre-release test loop section â€” kept,
  but rewritten to test the npx-only install flow, not the old plugin flow.
- `skills/` tree (the actual skill content) â€” kept; this is now the product.
- `lib/` content â€” moved into `skills/mpi-lib/`.
- `templates/` content â€” moved into per-consuming-skill private subfolders
  (Phase 7.1 option b).
- Coordination state contract under `.agents/mpi-kanban/state/` â€” unchanged.
- Kanban board contract at `.claude/mpi-kanban/kanban.md` â€” unchanged. The
  VS Code extension keeps watching the same path.
- Companion VS Code extension fork at `mpi-kanban-vscode` â€” unchanged.
- README.md, CLAUDE.md, AGENTS.md â€” kept and rewritten to reflect npx-only.

## Release Strategy

Decision made 2026-05-23: **R2**. Skip the Kilo-narrow 0.6.0 ship. Phase 7
hard-drop refactor lands as the next public release.

Version bump target: **0.6.0** (keeps the version number we already prepared
locally; the diff under this tag is large and the version-jump reflects it).
Alternative: bump to **1.0.0** to signal the breaking change of dropping
Claude/Codex plugin identity. User to confirm in Phase 7.0.

Hard drop affects existing users of `/plugin install mpi-kanban@mad-pony-interactive`.
CHANGELOG `### Removed` block (text in `## Replaces / Drops`) is the
migration path.

## Phase 7.0: Spike Confirmation

Ownership: this plan file.

- [x] Confirm final version number for the hard-drop release: 0.6.0.
- [x] Read `templates/` to confirm `kanban.md` and other runtime templates
      that mpi-init / mpi-project-setup consume. Confirm option (b): templates
      go into per-consuming-skill private subfolders.
- [x] Decide whether `update_live.py` is repurposed (npx-style local mirror)
      or deleted outright. Recommended: delete it unless local-path
      `npx skills add` testing proves inadequate; fewer maintainer-only
      bridges is the point of Phase 7.
- [x] Decide whether `.github/workflows/release.yml` needs adjustment beyond
      dropping the manifest-validator step.

**Verify:** Decisions recorded in plan + handoff.

## Phase 7.1: mpi-lib Skill Authoring

Ownership: `skills/mpi-lib/` (new).

- [x] Create `skills/mpi-lib/SKILL.md`:
  - `name: mpi-lib`
  - Use only portable Agent Skills frontmatter: `name`, `description`, and
    optional `metadata` fields. Do not rely on Claude-only frontmatter such as
    `user-invocable` or `disable-model-invocation`.
  - Description: "MPI workflow pack - shared reference library for the
    mpi-kanban skills. Install with the full MPI workflow pack; do not invoke
    directly."
  - Body: short pointer index of what lives in each subfolder. No content
    duplication. First body line should repeat that this is a support skill
    for the all-or-nothing pack, not a user workflow.
- [x] Copy the full `lib/` tree into `skills/mpi-lib/`. Final layout:

  ```
  skills/mpi-lib/
    SKILL.md
    coordination-ops/lifecycle.md, statuses.md, ...
    kanban-ops/find.md, mutate.md, steps.md, ...
    plan-ops/...
    project-intent/...
    project-knowledge/...
    config-ops.md
  ```

- [x] Decide on `templates/` content. Two options:
  - **a.** Move `templates/project-profile.md`, `templates/project-knowledge-index.md`,
    `templates/kanban.md`, etc. into `skills/mpi-lib/templates/`. Consuming
    skills locate them via the same path-discovery logic.
  - **b.** Inline each template into the consuming skill that uses it
    (mpi-init -> kanban.md template, mpi-project-setup -> profile +
    index templates). Smaller per-skill, no extra discovery.
  - **Recommended:** b. Templates are skill-private, not cross-skill shared.

**Verify:** `skills/mpi-lib/` contains the full lib tree; `templates/`
content placed correctly per chosen option.

## Phase 7.2: Rewrite 13 Consuming SKILL.md Files

Ownership: each of the 13 SKILL.md files that currently reference
`${CLAUDE_PLUGIN_ROOT}/lib/...` (audit shows: archive 5, brainstorm 4,
brief-rule 1, continue 10, create-large-plan 4, create-plan 4, end-session 8,
execute-parallel 3, handoff 7, init 5, project-mode 4, project-refresh 5,
project-setup 9 â€” total 69 references). `mpi-cleanup` has zero.

- [x] Add a short "Locating mpi-lib" block near the top of each SKILL.md:

  ```
  ## Locating shared references

  Shared reference docs live in the sibling skill `mpi-lib`. At first use,
  find the first existing directory from this candidate list:

  1. `~/.agents/skills/mpi-lib`
  2. `.agents/skills/mpi-lib`
  3. `~/.claude/skills/mpi-lib`
  4. `.claude/skills/mpi-lib`

  Cache that root path for the rest of this session. All references below
  resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and
  tell the user to reinstall the complete pack with:

  `npx skills add MadPonyInteractive/mpi-kanban --all -y -g`
  ```

  The block must stay tool-neutral: no `!` injection, no Bash-only command,
  no PowerShell-only command, and no `${CLAUDE_PLUGIN_ROOT}`.

- [x] Rewrite every `${CLAUDE_PLUGIN_ROOT}/lib/foo/bar.md` reference to
  `<mpi-lib-root>/foo/bar.md` (or `coordination-ops/lifecycle.md` style
  relative-to-root form).

- [x] Prefix every skill `description` with "MPI workflow pack - " so the
  pack semantics show in skill listings.

- [x] Smoke read each rewritten SKILL.md to confirm no broken pointers,
  no stray `${CLAUDE_PLUGIN_ROOT}` strings, no stale `lib/` paths.

**Verify:**
- `grep -rn 'CLAUDE_PLUGIN_ROOT' skills/` returns zero hits.
- `grep -rn '\${CLAUDE_PLUGIN_ROOT}\|lib/' skills/*/SKILL.md` matches only
  intentional `<mpi-lib-root>/...` style refs.

## Phase 7.3: skills.sh Manifest + Pack Description

Ownership: `skills.sh.json` (new), root README.md.

- [x] Add `skills.sh.json` at repo root declaring the "MPI Workflow" grouping
  with all current skill names. Reference the
  `https://skills.sh/schemas/skills.sh.schema.json` schema. Display only â€” no
  install behavior change.
- [x] Update README.md install section: skills.sh `npx skills add --all`
  becomes the only supported install command. Include the all-or-nothing
  warning and a migration note for old Claude/Codex plugin users.
- [x] Update AGENTS.md: replace Phase 6 KiloCode pointer with a general
  "Cross-agent install" pointer to `docs/install.md`.

**Verify:** `skills.sh.json` parses; README.md renders; `npx skills add
MadPonyInteractive/mpi-kanban -l` (after push) lists the current skill surface.

## Phase 7.4: Replace Kilo Docs With Universal Install Docs

Ownership: `docs/install.md` (new), delete `docs/kilocode-install.md` and
`docs/kilocode-marketplace-submission.md`, delete `templates/kilo.jsonc`.

- [x] Write `docs/install.md` covering, in order:
  - Primary: `npx skills add MadPonyInteractive/mpi-kanban --all -y -g`.
    Works for all skills.sh-compatible agents.
  - Migration from old Claude plugin install:
    `/plugin uninstall mpi-kanban@mad-pony-interactive --scope user`, then the
    npx install command above.
  - Migration from old Codex plugin install: remove the old Codex plugin
    registration/cache through Codex's normal plugin removal flow, then use
    the npx install command above.
  - Per-agent path notes (Claude Code, Codex, Kilo, OpenCode, Cursor, etc.).
  - "All or nothing" warning: missing mpi-lib breaks the other 14.
  - Updating notes.
- [x] Delete the three Kilo-named files. Keep their git history; they're
  not symlinks or import sources.

**Verify:** `docs/install.md` renders; deleted files removed; no internal
links broken (grep README/AGENTS/SPEC for refs to old paths).

## Phase 7.5: Validator + Build Helper Updates

Ownership: `scripts/validate_plugin.py`, delete `scripts/build_kilo_skills.py`.

- [x] Rename `validate_kilo_assets()` -> `validate_universal_skill_limits()`.
  Drop the `kilo.jsonc` parse step. Keep the SKILL.md name/description length
  check (which is Agent Skills standard, not Kilo-specific).
- [x] Add a new check `validate_mpi_lib_present()`:
  - confirms `skills/mpi-lib/SKILL.md` exists.
  - confirms every other `skills/mpi-*/SKILL.md` includes the "Locating
    shared references" block (grep for the `mpi-lib-root` token).
  - confirms zero `${CLAUDE_PLUGIN_ROOT}` references remain in any
    `skills/*/SKILL.md`.
- [x] Add `validate_skills_sh_json()`:
  - parses `skills.sh.json` as JSON.
  - confirms every entry in `groupings[*].skills` matches an actual
    `skills/<name>/SKILL.md`.
- [x] Delete `scripts/build_kilo_skills.py`. Delete `skills-kilo/`.

**Verify:** `python scripts/validate_plugin.py` reports green with the new
checks.

## Phase 7.6: SPEC + Project-Profile + Knowledge-Index Sync

Ownership: `SPEC.md`, `.agents/mpi-kanban/project-profile.md`,
`.agents/mpi-kanban/project-knowledge-index.md`, `PLAN.md`.

- [x] Rewrite SPEC.md Â§14 from "KiloCode Distribution" to "Cross-Agent
  Skill Distribution via skills.sh". Cover:
  - Skill pack model + 15-skill count + mpi-lib sibling.
  - skills.sh as the only supported distribution channel.
  - Path-discovery contract (`<mpi-lib-root>/...` candidate list).
  - All-or-nothing semantics; `--all` flag in install command.
  - Validator coverage.
  - Non-goals (no per-skill self-containment, no Kilo-specific shim).
- [x] Update project-profile.md Architecture Summary: drop Kilo-specific
  lines, add `skills/mpi-lib/` + skills.sh distribution lines.
- [x] Update project-knowledge-index.md: rename `kilocode-packaging` ->
  `skills-sh-distribution`; update files-to-read.
- [x] Append `## Cross-agent skills distribution Phase 7` block to PLAN.md
  with sub-phase checkboxes.

**Verify:** SPEC Â§14 numbering unchanged; all three project-knowledge
files refer to Phase 7; PLAN.md tracks Phase 7.

## Phase 7.7: Smoke Test Cycle

Ownership: scratch test workspace + this plan.

- [x] If Phase 7.0 keeps a local mirror helper, run it to mirror the Phase 7
  tree into `~/.agents/skills/`. Otherwise install from a local checkout with
  the supported `npx skills` local-path flow.
- [ ] In a fresh Claude Code session after installing with
  `npx skills add MadPonyInteractive/mpi-kanban --all -y -g`, invoke the
  `mpi-continue` skill through Claude's Agent Skills surface and confirm the
  mpi-lib discovery block resolves to a valid path and reads
  `coordination-ops/lifecycle.md` correctly.
- [ ] In a fresh VS Code Kilo workspace, install via
  `npx skills add MadPonyInteractive/mpi-kanban --all -y -g` (after the Phase 7
  push lands), invoke `/mpi-continue`, confirm same.
- [ ] Codex smoke: after installing with `npx skills add --all`, invoke
  `$mpi-continue` or the equivalent Agent Skills invocation supported by the
  installed Codex build, and confirm mpi-lib resolution works.
- [ ] Roll back the Phase 7 packaging edits if smoke fails.

**Verify:** Three agents (Claude + Kilo + Codex) successfully resolve mpi-lib
and execute one MPI skill end-to-end after npx install.

## Phase 7.8: Release (npx-only)

Ownership: `CHANGELOG.md`, git tag. No plugin manifests left to bump.

- [x] Confirm Phase 7.0 version decision: 0.6.0.
- [x] Append a `### Removed` block to `## [Unreleased]` in CHANGELOG.md per
  the migration text in `## Replaces / Drops`.
- [ ] Promote `## [Unreleased]` -> `## [<version>] - <YYYY-MM-DD>` in
  CHANGELOG.md and update link references.
- [ ] Commit (`Release <version>`) and tag (`v<version>`). Push branch + tag.
- [ ] Confirm `.github/workflows/release.yml` creates the GitHub release.
- [ ] Post-release smoke: `npx skills add MadPonyInteractive/mpi-kanban -l`
  lists the current skill surface; `--all -y -g` installs cleanly; one MPI skill runs
  end-to-end.

**Verify:** Tag pushed; release-workflow succeeds; npx install works on a
clean machine.

## Open Questions

- Does skills.sh require a separate listing/registration step, or does
  `npx skills add owner/repo` work for any public GitHub repo without
  registration? (Empirical answer: works without registration.)
- Does `npx skills` accept a branch/tag ref (`owner/repo@tag`)? Earlier
  research did not confirm. If yes, we could ship the pack from a `release`
  branch and let users pin versions. Investigate during Phase 7.0.
- Should mpi-lib include a `version` field in frontmatter so consuming
  skills can refuse to run against incompatible versions? Defer; revisit if
  pack ever has breaking lib changes.

## Notes Preserved From The Investigation Spike (2026-05-23)

- skills.sh / `npx skills` / Agent Skills standard at <https://agentskills.io>
  is owned by Anthropic, open-spec, adopted by ~40 agents.
- Sibling files load on demand per the spec's progressive-disclosure model.
- Claude Code-only features: `!` bash injection, `${CLAUDE_PLUGIN_ROOT}`,
  `--scope user/project/local`. Avoid relying on any of them for cross-agent
  skills.
- `~/.agents/skills/` is the user-global cross-agent skill dir; `.agents/skills/`
  the project-scope equivalent. Different from `~/.claude/skills/` (Claude
  Code personal) and `~/.claude/plugins/cache/...` (Claude plugin cache).
  Phase 7 keeps `claude` path probes only as a convenience for users who
  manually place skills there. The supported install route is still
  `npx skills add --all`; `/plugin install` is not a supported fallback.
- Context cost of shared mpi-lib: at worst, one read per lib file per
  session per skill that uses it. Agent intelligence (Claude noting "already
  read this") plus the `<mpi-lib-root>` caching pattern keep it bounded.
  Empirically: lifecycle.md ~6KB ~1500 tokens; Opus 1M context absorbs many
  copies without harm.


