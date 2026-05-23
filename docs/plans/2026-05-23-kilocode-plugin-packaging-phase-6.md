# KiloCode Plugin Packaging - Phase 6

## Project Mode

`scalable-foundation` (per `.agents/mpi-kanban/project-profile.md`). New surfaces ship with validator coverage, manifest sync, and docs.

## Current State

Mpi-Kanban currently ships as a dual Claude Code + Codex plugin:

- Claude manifest: `.claude-plugin/plugin.json`
- Codex manifest: `.codex-plugin/plugin.json`
- Shared skill tree: `skills/mpi-*/SKILL.md` (14 skills, all `name` + `description` frontmatter)
- Codex marketplace bundle: `plugins/MadPonyInteractive/mpi-kanban/` (Phase 5 in flight)
- Coordination contract: `.agents/mpi-kanban/state/`

Phase 5 (Codex plugin install/update distribution) is running in parallel and currently owns these uncommitted files:

- `plugins/MadPonyInteractive/mpi-kanban/plugins.json`
- `scripts/validate_plugin.py`

Phase 6 must not touch those files until Phase 5 lands; Phase 6 may extend them later with additive validator coverage, but only after Phase 5 commits.

## KiloCode Distribution Model (Verified)

Sources: <https://kilo.ai/docs/customize/skills>, <https://github.com/Kilo-Org/kilo-marketplace>.

KiloCode does not consume a single plugin archive. Instead its agent runtime discovers **Agent Skills** from filesystem and URL sources:

- Project skills: `.kilo/skills/<skill>/SKILL.md` (highest precedence).
- Global skills: `~/.kilo/skills/<skill>/SKILL.md`.
- Compatibility directories loaded alongside: `.claude/skills/`, `.agents/skills/`.
- Additional paths or URLs configured via `kilo.jsonc` keys `skills.paths` and `skills.urls`.
- Marketplace: `Kilo-Org/kilo-marketplace` indexes remote skills by `metadata.source.repository` / `.path` / `.license_path` in SKILL.md frontmatter.

SKILL.md frontmatter schema:

- `name` (required, <=64 chars, lowercase + digits + hyphens) - already satisfied by all `mpi-*` skills.
- `description` (required, <=1024 chars) - already satisfied.
- `license` (optional) - currently absent.
- `compatibility` (optional) - currently absent.
- `metadata` (optional free-form) - currently absent; the marketplace submission script writes `metadata.source` automatically.

Custom modes live under the `agent` key in `kilo.jsonc` (description, mode, color, prompt, model, permission, steps, temperature, hidden, disable). Modes can reference the surrounding skill tree but are not required for skill discovery.

KiloCode therefore needs no separate manifest archive analogous to `.claude-plugin/` or `.codex-plugin/`. The "official KiloCode plugin" deliverable is:

1. A clean import surface in this repo so KiloCode users get the skill tree natively.
2. A submission to `Kilo-Org/kilo-marketplace` so KiloCode users can pull MPI skills without cloning this repo.
3. Documentation for both flows.

## Goals

- Make MPI workflow skills installable into a fresh KiloCode workspace without cloning this whole repo.
- Preserve the existing Claude + Codex shipping paths unchanged.
- Keep coordination state, kanban contract, and skill source tree single-source.
- Validate the Kilo path with the existing `scripts/validate_plugin.py` once Phase 5 lands.

Non-goals:

- Authoring a custom Kilo agent/mode beyond a single optional MPI orchestrator example.
- Building a Kilo CLI wrapper or runtime adapter (the existing skills are pure markdown).
- Hosting skills directly inside `Kilo-Org/kilo-marketplace` (the marketplace rejects in-repo skill source; MadPonyInteractive/mpi-kanban remains the source repo).

## Multi-Target Adapter Note

KiloCode is the first runtime-native target adapter built on the shared
`skills/mpi-*` canonical source. The generator is deliberately structured as
five separable steps (discover, transform, resolve, write, validate) with
target-neutral function names so a follow-up Codex or OpenCode adapter can
reuse the structure. Kilo-specific constants (output dir, reference pattern,
prose replacement, max inline depth, marketplace assumptions) are isolated
near the top of `scripts/build_kilo_skills.py`.

The shared `skills/` tree is the canonical source. Kilo output is a target
adapter, not a new canonical source. A later refactor may extract
`scripts/build_agent_skills.py --target kilo|codex|opencode`; until then, the
Kilo script name and `skills-kilo/` output dir stay as-is for this phase. The
reference model is `obra/superpowers`: shared skills source, runtime-native
packaging/adapters around it.

Follow-up sketch (not in scope for Phase 6):

- Codex consumes `skills/` natively via `.codex-plugin/plugin.json`, so a
  Codex adapter probably does not inline. It may instead generate overlay
  metadata, install/update artifacts, or marketplace-bundle validation.
- OpenCode (and similar) likely lands somewhere between Kilo (full inline) and
  Codex (no inline) depending on fetch model.

## Architecture Decisions

1. **No new manifest format.** Reuse the existing `skills/mpi-*` tree as the source. KiloCode discovers it via compatibility paths or marketplace entries.
2. **Marketplace bundle dir is separate from the Codex bundle.** New: `plugins/MadPonyInteractive/mpi-kanban-kilo/` is reserved only if KiloCode submission requires repo-local artifacts. Default: no new top-level dir; the marketplace PR points at the existing `skills/` tree.
3. **kilo.jsonc template is opt-in.** Add `templates/kilo.jsonc` so KiloCode users can drop it into a project to wire `skills.paths`. Do not ship a project-level `kilo.jsonc` inside this repo (would conflict with the maintainer's own KiloCode usage).
4. **`metadata.source` in SKILL.md is deferred** to the submission step. Adding it now would conflict with Phase 5 validator logic. The marketplace submission script (`npx tsx bin/add-remote-skill.ts`) writes the block, so locally we only need to verify the result before the PR.
5. **AGENTS.md is the KiloCode entrypoint too.** KiloCode reads AGENTS.md natively (per <https://kilo.ai/docs/customize/agents-md>). A short Kilo section in AGENTS.md is enough; do not duplicate per-agent entrypoint files.
6. **No coupling to update_live.py for Kilo.** KiloCode users install via marketplace or `kilo.jsonc`; the live-copy script remains Claude+Codex maintainer tooling.

## Phase 6.1: Authoring Audit and Compatibility Map

Ownership: this plan file only.

- [x] Confirm all 14 skills meet Kilo `name` + `description` constraints.
- [x] Cross-check each skill's reference paths. **Result:** 12/14 skills reference `${CLAUDE_PLUGIN_ROOT}/lib/...`; 2 skills (`mpi-brief-rule`, parts of `mpi-init`) reference a single `lib/` file each. Templates referenced: `templates/project-profile.md`, `templates/project-knowledge-index.md` (used by `mpi-project-setup`).
- [x] Conclusion: marketplace pull breaks 12/14 skills; cloned-repo install relies on `${CLAUDE_PLUGIN_ROOT}` resolution. See Plan Drift section.

**Verify:** Audit complete. No SKILL.md edits.

## Phase 6.1a: Generator Design and Implementation

Ownership: `scripts/build_kilo_skills.py` (new), `skills-kilo/` (new, gitignored output by default).

- [ ] Write `scripts/build_kilo_skills.py`:
  - Walk `skills/mpi-*/SKILL.md`.
  - For each skill, find every `${CLAUDE_PLUGIN_ROOT}/<path>` reference. Resolve each path against the repo root.
  - Inline the referenced file's contents into the output SKILL.md under a clearly delimited block, e.g. `\n### Inlined: <path>\n<contents>\n### End inlined: <path>\n`. Keep the inline near the original reference for context.
  - Strip the `${CLAUDE_PLUGIN_ROOT}/` prefix from any remaining bullet pointer so the surviving text reads naturally.
  - Detect transitive references (an inlined file that itself references another lib path) and resolve them too, up to depth 3. Cycle-guard with a visited set.
  - Preserve YAML frontmatter unchanged.
  - Write output to `skills-kilo/<name>/SKILL.md`. Copy any non-SKILL.md files (scripts/, references/, assets/) from the source skill folder if present.
  - Emit a summary table to stdout: skill name, inlined files count, output bytes.
- [ ] Add `skills-kilo/` to `.gitignore` by default (generated artifact). The marketplace PR is opened from a fork branch that has the generated tree committed; this repo does not need to track the output.
- [ ] Make the script idempotent: rerun overwrites cleanly.

**Verify:** `python scripts/build_kilo_skills.py` produces `skills-kilo/mpi-*/SKILL.md` for all 14 skills with no `${CLAUDE_PLUGIN_ROOT}` references remaining; no path outside the skill folder is referenced; cycle guard reports clean.

## Phase 6.1b: Generated-Tree Audit and Smoke

Ownership: this plan file + generator output review.

- [ ] Grep generated SKILL.md files for `${CLAUDE_PLUGIN_ROOT}` and any remaining `lib/` / `docs/coordination/` paths. Zero hits required.
- [ ] Eyeball one inlined skill (`mpi-continue` is the heaviest dep web) to confirm readability and that the inlined operations are intelligible to an agent without the broader plugin tree.
- [ ] Confirm each generated SKILL.md is below a sane size limit (target <100 KB).
- [ ] Optional: install one generated skill folder into a fresh `~/.kilo/skills/mpi-init/` and run the skill end-to-end in Kilo.

**Verify:** No residual sibling refs; sample skill readable; size sane.

## Phase 6.2: KiloCode Install Documentation

Ownership: `README.md` (Kilo install section only, append below Codex section), new `docs/kilocode-install.md`, `templates/kilo.jsonc`.

Hard constraint: do not edit the Codex install section of README.md while Phase 5 is in flight. If Phase 5 has not yet appended its Codex install block, write the Kilo section to `docs/kilocode-install.md` only and stop until Phase 5 commits, then add the README pointer.

- [ ] Write `docs/kilocode-install.md` covering:
  - Install via Kilo Marketplace (after Phase 6.4 submission lands).
  - Manual install via `kilo.jsonc` `skills.paths` pointing at a cloned `MadPonyInteractive/mpi-kanban` checkout.
  - Manual install via copying `skills/mpi-*` into `.kilo/skills/` or `~/.kilo/skills/`.
  - Compatibility path: Kilo auto-loads `.claude/skills/` and `.agents/skills/`, so existing Claude-installed plugins surface in Kilo with no extra work.
  - Companion VS Code extension link (board renderer is editor-agnostic).
- [ ] Add `templates/kilo.jsonc` with a minimal `skills.paths` entry pointing at the cloned repo and a brief comment block.
- [ ] Append a `## KiloCode users` pointer section to `README.md` linking the docs file.
- [ ] Add a `## KiloCode` pointer section in `AGENTS.md` (short, links to docs).

**Verify:** Docs file renders, `kilo.jsonc` parses as valid JSONC, README pointer compiles in markdown, no edits to Codex install block.

## Phase 6.3: Marketplace Submission Artifacts

Ownership: new `docs/kilocode-marketplace-submission.md` (maintainer runbook).

- [ ] Document the exact submission flow against `Kilo-Org/kilo-marketplace`:
  - Fork target repo, branch `add-mpi-kanban-skills`.
  - For each of the 14 skills, run `npx tsx bin/add-remote-skill.ts https://github.com/MadPonyInteractive/mpi-kanban/tree/main/skills/<name>` so the marketplace tooling writes `metadata.source` automatically.
  - PR title format: `Add mpi-* skills`.
  - Per-skill content checklist required by Kilo (description, "When to Use", "What This Skill Does", "How to Use", example, tips). The MPI skills already include similar structure; the runbook lists per-skill gaps to fill before PR.
  - License declaration: MIT, referencing repo `LICENSE`.
- [ ] Capture the post-submission verification: install one MPI skill into a fresh KiloCode workspace via marketplace, run `$mpi-init` smoke step.

**Verify:** Runbook lists all 14 submission commands, PR template, validation step. No marketplace PR is sent in this sub-phase.

## Phase 6.4: Marketplace Submission Execution

Ownership: submission PR against `Kilo-Org/kilo-marketplace`, separate fork. No file edits in this repo unless a skill content gap is found.

- [ ] Run the submission runbook from 6.3.
- [ ] If a skill is rejected for missing content sections, file gaps as a follow-up todo (do not block other skills).
- [ ] Capture the merged PR URL in `CHANGELOG.md` (under a new `Phase 6` entry, gated on Phase 5's CHANGELOG edits committing first).

**Verify:** PR opened or merged; skill discoverable in `kilo-marketplace`; smoke-install works in a fresh KiloCode workspace.

## Phase 6.5: Validator Coverage (Coordination Gate)

Ownership: `scripts/validate_plugin.py` - **owned by Phase 5 until Phase 5 commits**. Phase 6 work on this file is blocked on a Phase 5 handoff or merge.

- [ ] After Phase 5 lands, add an additive `validate_kilo_assets()` step that:
  - confirms `docs/kilocode-install.md` exists.
  - confirms `templates/kilo.jsonc` parses as JSON (strip `//` comments first).
  - re-checks SKILL.md `name` <=64 chars and `description` <=1024 chars.
  - confirms `scripts/build_kilo_skills.py` exists and is runnable.
  - optional: regenerate `skills-kilo/` into a temp dir and diff against committed `skills-kilo/` (if checked in) to catch drift; skipped if `skills-kilo/` is gitignored.
- [ ] Do not validate marketplace remote URLs (network-side; out of scope for offline validator).

**Verify:** `python scripts/validate_plugin.py` passes with the new step and the Phase 5 step both wired.

## Phase 6.6: SPEC, PLAN, Project Profile Sync

Ownership: `SPEC.md`, `PLAN.md`, `.agents/mpi-kanban/project-profile.md`, `.agents/mpi-kanban/project-knowledge-index.md`.

Coordination: Phase 5 may also touch `PLAN.md` validation checklist. Read PLAN.md fresh and append the Phase 6 section, never rewrite Phase 5's lines.

- [ ] Append `## KiloCode packaging Phase 6` block to `PLAN.md` with sub-phase checkboxes.
- [ ] Add a short `## 14. KiloCode Distribution` (or next free section) to `SPEC.md` covering the three install paths and the marketplace contract.
- [ ] Update `.agents/mpi-kanban/project-profile.md` "Architecture Summary" with the Kilo install paths and the marketplace bundle dir (if introduced in 6.3).
- [ ] Update `.agents/mpi-kanban/project-knowledge-index.md` so KiloCode topics map to the new docs.

**Verify:** SPEC + PLAN + profile + index reference Phase 6 deliverables; no overwrites of Phase 5 lines.

## Phase 6.7: Release

Ownership: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md`, git tag.

- [ ] Sync version bump across both manifests (current 0.5.1 -> 0.6.0 because new distribution surface).
- [ ] Run `/release 0.6.0` (the maintainer command) which handles validator, CHANGELOG, tag, push.
- [ ] After release, run `/update-live` to refresh local caches.

**Verify:** Tag `v0.6.0` pushed, GitHub release auto-created, `validate_plugin.py` green.

## Parallel Batch

Eligible for parallel execution **only after Phase 5 commits** and the validator handoff is clear. Until then Phase 6 runs sequential.

```
## Parallel Batch: Phase 6 documentation pass
Trigger: Phase 5 merged into main; .agents/mpi-kanban/state/ shows no active Phase 5 claims.

- [ ] Write docs/kilocode-install.md + templates/kilo.jsonc
  Ownership: docs/kilocode-install.md, templates/kilo.jsonc
  Briefings: none
  **Verify:** docs file renders; JSONC parses after stripping comments.

- [ ] Write docs/kilocode-marketplace-submission.md
  Ownership: docs/kilocode-marketplace-submission.md
  Briefings: none
  **Verify:** Runbook lists all 14 skills + submission commands.

- [ ] Append KiloCode sections to README.md and AGENTS.md (pointer-only)
  Ownership: README.md, AGENTS.md
  Briefings: none
  **Verify:** Existing Claude + Codex sections untouched (git diff scoped to appended block).
```

Sub-phases 6.4, 6.5, 6.6, 6.7 stay sequential because they cross repo boundaries (marketplace fork, validator script, manifest version bump, release tag) and must observe ordering.

## Completed

- 6.0 Planning: KiloCode model researched, schema verified, coordination state registered.
- 6.1 Authoring audit: 14 skills compliant; sibling-dep map produced.
- 6.1a Generator: `scripts/build_kilo_skills.py` written, refactored into five separable steps (discover/transform/resolve/write/validate) with target-neutral function names and Kilo constants isolated near top; `skills-kilo/` gitignored.
- 6.1b Audit pass: generator output has zero residual `${CLAUDE_PLUGIN_ROOT}` refs, no missing/cycle markers, sizes 3-40 KB; in-script `validate_generated()` also passes.
- 6.2 Install docs: `docs/kilocode-install.md` (includes generator/multi-target note), `templates/kilo.jsonc`, AGENTS.md pointer.
- 6.3 Submission runbook: `docs/kilocode-marketplace-submission.md`.
- 6.5 Additive validator coverage: `validate_kilo_assets()` and `validate_kilo_skill_limits()` added to `scripts/validate_plugin.py` (additive beside the committed Codex marketplace bundle check from Phase 5 commit `eb0362e`). Validator green.
- PLAN.md appended with Phase 6 sub-phase tracking.

## Remaining Work

- 6.4 Open marketplace PR against `Kilo-Org/kilo-marketplace` per runbook (requires user-authorized push to a `kilo-release-0.6.0` branch).
- 6.6 Add `## 14. KiloCode Distribution` section to `SPEC.md`; update `.agents/mpi-kanban/project-profile.md` architecture summary; update `.agents/mpi-kanban/project-knowledge-index.md` with KiloCode topics.
- 6.7 Release `0.6.0`: bump manifests, run `/release`, run `/update-live`.

## Plan Drift

**2026-05-23 (post-approval, during 6.1 audit):**

KiloCode marketplace pull (`add-remote-skill.ts`) uses git sparse-checkout of the skill folder only. Sibling references via `${CLAUDE_PLUGIN_ROOT}/lib/...` and `${CLAUDE_PLUGIN_ROOT}/templates/...` do not survive the pull — 12 of 14 MPI skills reference `lib/`, so they break in a marketplace install. Additionally Kilo defines no `${CLAUDE_PLUGIN_ROOT}` equivalent, so even a cloned-repo `kilo.jsonc skills.paths` install relies on Kilo treating the var literally or the maintainer documenting a fallback.

Architecture revision (user-approved):

- **Generator approach.** Keep shared `skills/mpi-*/SKILL.md` untouched (no collision with Phase 5). Add `scripts/build_kilo_skills.py` that resolves every `${CLAUDE_PLUGIN_ROOT}/...` reference by inlining the target file's contents into the skill, emits portable copies to `skills-kilo/mpi-*/SKILL.md`. Marketplace PR ships the generated tree, not the shared source.
- **Two sub-phases inserted:**
  - **6.1a Generator design and implementation** (new, before 6.2).
  - **6.1b Generated-tree audit and smoke test** (new, before 6.3).
- **6.4 marketplace submission targets `skills-kilo/`** not `skills/`.
- **6.5 validator** gains a `validate_generated_kilo_tree()` step (drift check between source and generated tree).

The compatibility-path install (`.claude/skills/` via Claude plugin) keeps working with zero Phase 6 effort and remains documented as Option 1 in `docs/kilocode-install.md`.

## Verification

End-to-end acceptance:

- A fresh KiloCode workspace can list `mpi-init`, `mpi-brainstorm`, `mpi-create-plan` via Kilo Marketplace search.
- Pulling `mpi-init` into a fresh project produces a working board after `$mpi-init`.
- `python scripts/validate_plugin.py` reports green with both Phase 5 (Codex bundle) and Phase 6 (Kilo assets) checks active.
- `README.md` shows three install surfaces: Claude, Codex, KiloCode.
- Existing Claude + Codex behavior is unchanged (smoke a single `/mpi-kanban:mpi-cleanup` and `$mpi-kanban:mpi-cleanup` after release).

## Preservation Notes

- Phase 5 owns `plugins/MadPonyInteractive/mpi-kanban/plugins.json` and `scripts/validate_plugin.py` until its commit lands. Phase 6 must not edit those files mid-flight.
- README install order should be: Claude (existing), Codex (Phase 5), KiloCode (Phase 6) - chronological.
- Marketplace PR is opened from a fork, not from this repo; the submission runbook lives in `docs/kilocode-marketplace-submission.md` for repeatable releases.
- Kilo's marketplace tool (`add-remote-skill.ts`) writes `metadata.source` into SKILL.md frontmatter on the fork side; do not pre-write that block in this repo or it will conflict with the tool.
