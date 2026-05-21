# Dual Claude/Codex Plugin Packaging and Invocation - Phase 3

## Current State

Mpi-Kanban is currently a Claude Code plugin with a Codex bridge:

- Claude plugin manifest: `.claude-plugin/plugin.json`
- Claude marketplace manifest: `.claude-plugin/marketplace.json`
- Shared workflow skills: `skills/mpi-*/SKILL.md`
- Codex bridge: `AGENTS.md`
- Shared coordination state contract: `.agents/mpi-kanban/state/`
- Human-visible board contract: `.claude/mpi-kanban/kanban.md`

The existing bridge already lets Codex read and follow the plugin's workflow
skills when the project or global instructions point Codex at the installed
Claude plugin. That is useful, but it is not the desired Phase 3 end state.

The Phase 3 goal is to make Mpi-Kanban feel native to Codex users while keeping
the same source repository and shared workflow behavior for Claude Code users.
Codex users should be able to install Mpi-Kanban as a Codex plugin and invoke
the MPI workflows through Codex-native skill invocation, especially:

- `$mpi-end-session`
- `$mpi-cleanup`
- `$mpi-continue`
- `$mpi-handoff`

Claude users should continue using the existing Claude plugin slash commands,
such as:

- `/mpi-kanban:mpi-end-session`
- `/mpi-kanban:mpi-cleanup`

Important decision:

- Do not mimic Claude slash commands in Codex unless Codex adds official
  custom/plugin slash command support.
- Treat Codex skills as the native Codex workflow command surface.
- Keep natural language invocation reliable by tuning skill descriptions.

Known constraints:

- Do not duplicate the MPI workflow implementation into separate Claude and
  Codex skill trees unless shared-source packaging proves impossible.
- Do not change kanban columns or metadata fields.
- Keep `.agents/mpi-kanban/state/` as the coordination authority.
- Preserve the pure Markdown skill/reference architecture unless a later phase
  explicitly introduces executable support.
- `update_live.py` currently targets the live Claude plugin cache; Phase 3 must
  either extend it safely or document a separate Codex install/update path.
- Phase 4 must remain blocked until Phase 3 is complete.

Relevant Codex-native packaging assumptions to verify during implementation:

- Codex plugin manifest path is `.codex-plugin/plugin.json`.
- Codex plugin manifests can point at `./skills/`.
- Codex plugin metadata should include an `interface` block for native display.
- Local marketplace entries live under `.agents/plugins/marketplace.json` or
  the user's home-level equivalent when needed.

## Completed

- [x] Confirmed the local Codex plugin scaffold contract from the installed
  `plugin-creator` reference: `.codex-plugin/plugin.json`, `skills:
  "./skills/"`, `interface` metadata, and home-local marketplace entries under
  `~/.agents/plugins/marketplace.json` for local development.
- [x] Added `.codex-plugin/plugin.json` for `mpi-kanban` using the existing
  public identity and shared `skills/` tree.
- [x] Updated skill descriptions and runtime notes so Codex uses `$mpi-*` and
  natural language while Claude Code keeps `/mpi-kanban:mpi-*`.
- [x] Updated README, SPEC, AGENTS, CLAUDE, CHANGELOG, validation, and
  live-copy guidance for the dual-package model.
- [x] Extended `scripts/validate_plugin.py` to validate the Codex manifest,
  shared skill path, interface metadata, and Claude/Codex identity drift.
- [x] Added `scripts/register_codex_plugin.py` to simplify local Codex
  registration without requiring users to hand-edit marketplace JSON.

## Remaining Work

## Phase 1: Codex Native Contract

- [x] Confirm the exact current Codex plugin and skill manifest contract from
  official docs or local installed references before editing files. **Verify:**
  the plan notes any drift from the assumptions in `Current State`, especially
  around `.codex-plugin/plugin.json`, skill discovery, marketplace entries, and
  explicit `$skill-name` invocation.
- [x] Define the accepted invocation contract for both systems in one short
  compatibility note: Claude uses `/mpi-kanban:mpi-*`; Codex uses `$mpi-*` and
  natural language triggers. **Verify:** the note explicitly says custom Codex
  slash commands are out of scope unless officially supported.
- [x] Decide whether Codex install support needs a repo-local marketplace file,
  home-local marketplace instructions, or both. **Verify:** the decision covers
  local development, public install, and user-facing docs without assuming a
  Claude installation already exists.

## Phase 2: Codex Plugin Manifest

- [x] Add `.codex-plugin/plugin.json` for `mpi-kanban` using the existing plugin
  identity, version, author, license, repository, and keywords where compatible.
  **Verify:** the manifest points to `./skills/` and includes native Codex
  interface metadata with concise default prompts for common workflows.
- [x] Add only the Codex metadata and assets required for a native Codex plugin
  card. **Verify:** no placeholder assets or unused manifest paths are shipped.
- [x] Keep `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`
  synchronized where they represent the same public identity. **Verify:** name,
  version, description, author, license, and repository fields do not drift
  accidentally.

## Phase 3: Shared Skill Compatibility

- [x] Audit every `skills/mpi-*/SKILL.md` for Claude-only wording that would
  confuse Codex users or models. **Verify:** Claude command references remain
  accurate, but Codex-facing instructions do not imply that Codex should use
  Claude slash commands.
- [x] Tune frontmatter descriptions for reliable Codex skill triggering,
  prioritizing `mpi-end-session`, `mpi-cleanup`, `mpi-continue`, and
  `mpi-handoff`. **Verify:** descriptions include natural phrases users are
  likely to type, such as "MPI end session", "run MPI cleanup", "continue this
  MPI plan", and "create an MPI handoff".
- [x] Replace hard Claude-only root assumptions where needed with dual-runtime
  wording. **Verify:** skill references still resolve for Claude plugin use and
  are understandable for Codex plugin use.
- [x] Check related `lib/` reference docs for runtime-specific instructions
  that should become model-neutral. **Verify:** shared workflow behavior is not
  forked between Claude and Codex.

## Phase 4: Installation and Invocation Documentation

- [x] Update `README.md` with separate Claude Code and Codex installation
  sections. **Verify:** a new Codex user can identify the native Codex install
  path without reading Claude-only instructions first.
- [x] Document the command surface by product:
  `/mpi-kanban:mpi-*` for Claude Code and `$mpi-*` for Codex. **Verify:**
  examples cover at least end session, cleanup, continue, handoff, and natural
  language invocation.
- [x] Update `AGENTS.md` so Codex bridge behavior distinguishes installed
  Codex plugin use from fallback Claude-plugin reference use. **Verify:** Codex
  is not told to browse arbitrary Claude plugins and the MPI fallback remains
  constrained to `mpi-kanban@mad-pony-interactive`.
- [x] Update `SPEC.md` with the new dual-packaging contract. **Verify:** the
  spec names both manifests and keeps the workflow source of truth in the
  shared `skills/` tree.

## Phase 5: Validation and Release Tooling

- [x] Extend `scripts/validate_plugin.py` or add targeted validation so it
  checks the Codex manifest, shared skills, and Claude manifest together.
  **Verify:** validation fails on missing `.codex-plugin/plugin.json`, missing
  `skills` path, or manifest identity drift.
- [x] Review `update_live.py` against the dual-plugin packaging model.
  **Verify:** it either supports the Codex live/update path explicitly or
  documents why Codex plugin installation is handled separately.
- [x] Update `CHANGELOG.md` only after implementation details are known.
  **Verify:** the changelog describes actual shipped Codex plugin behavior, not
  aspirational support.

## Phase 6: Native Codex Smoke Test

- [ ] In a test project, install or register Mpi-Kanban through the Codex-native
  path. **Verify:** Codex recognizes the plugin without relying on the global
  Claude-plugin fallback.
- [ ] Invoke `$mpi-cleanup` in Codex against a test project with no cleanup
  approval. **Verify:** it proposes cleanup and does not delete active files.
- [ ] Invoke `$mpi-end-session` in Codex against a safe test project state.
  **Verify:** it follows the MPI preservation/verification flow and does not
  rely on Claude slash command semantics.
- [ ] Confirm natural language triggering for "MPI cleanup" and "MPI end
  session". **Verify:** Codex selects the expected skills or asks a reasonable
  clarification instead of ignoring the plugin.
- [x] Run the existing Claude plugin validation path after Codex changes.
  **Verify:** Claude slash commands and plugin metadata still work.

## Plan Drift

- 2026-05-21: Native Codex packaging was implemented from the local installed
  Codex plugin scaffold reference rather than external docs. No repo-local
  `.agents/plugins/marketplace.json` was added because `.agents/` is project
  state and gitignored here; README documents the home-local marketplace path
  instead.
- 2026-05-21: Added a Python 3.8+ stdlib-only registration helper so local
  Codex installation does not require manual JSON editing.

## Verification

Before Phase 3 is considered complete:

1. Mpi-Kanban has both Claude and Codex plugin manifests.
2. Codex can install or register Mpi-Kanban as a native Codex plugin.
3. Codex users invoke MPI workflows with `$mpi-*` skills and natural language,
   not Claude-style slash commands.
4. Claude users retain the existing `/mpi-kanban:mpi-*` command surface.
5. Shared skill files remain the workflow source of truth for both systems.
6. README, SPEC, AGENTS, PLAN, and validation tooling agree on the dual-package
   model.
7. `mpi-end-session` and `mpi-cleanup` are smoke-tested in Codex because they
   are the primary high-frequency workflows.
8. Existing Claude plugin validation still passes.
9. Phase 4 remains blocked until this phase is completed and validated.

## Preservation Notes

- Preserve the current design decision that Codex should feel native to Codex,
  not like a Claude slash-command clone.
- Keep the existing Claude plugin behavior stable unless a shared compatibility
  issue forces a change.
- Do not run `update_live.py` until Phase 3 implementation is complete and the
  user asks for the live copy update.
- The untracked Phase 4 plan exists at
  `docs/plans/2026-05-20-project-knowledge-architectural-intent-phase-4.md`;
  leave it unimplemented until Phase 3 is complete.
