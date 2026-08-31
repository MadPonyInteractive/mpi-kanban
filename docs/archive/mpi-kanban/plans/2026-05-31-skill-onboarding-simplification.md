# Skill Onboarding Simplification

## Current State

The release review found four readiness issues:

- Validator success depends on ignored local `.agents/mpi-kanban/state/interop.json`.
- Changelog entries are still under `[Unreleased]`, so tagged releases would get
  generic release notes.
- Legacy-board migration docs route users to `mpi-project-setup`, but JSON board
  conversion currently lives under `mpi-init` / extension migration behavior.
- Checklist event type docs do not match the VS Code extension output.

The larger design issue is that `mpi-init`, `mpi-project-setup`, and
`mpi-project-refresh` overlap from a user's point of view. Users should not need
to understand internal boundaries between board bootstrap, project knowledge
adoption, and legacy migration before they can start using the pack.

## Design Direction

Use two clear project-lifecycle entrypoints:

1. `mpi-init` becomes the single onboarding/adoption skill for a project.
   It handles new projects, existing projects, legacy MPI project state,
   JSON board bootstrap/migration, project profile/index creation, and initial
   source-of-truth mode setup.
2. `mpi-project-refresh` remains the existing-project maintenance skill.
   It audits and updates project knowledge, board/state consistency, migration
   drift, docs/rules pointers, and source-of-truth mode after MPI has already
   been initialized.

Proposed consolidation:

- Retire `mpi-project-setup` as a separate user-facing decision point.
  Either remove the skill before release, or keep it as a compatibility wrapper
  whose body immediately routes to `mpi-init`.
- Fold `mpi-project-mode` into the lifecycle model unless a separate command is
  still justified after the re-evaluation. Mode selection belongs in `mpi-init`;
  mode changes can be handled by `mpi-project-refresh` with an explicit
  "change project mode" path.
- Keep the implementation references modular in `mpi-lib` so `mpi-init` does not
  become a giant duplicated instruction file.

## Implementation

- [x] Re-evaluate project lifecycle skills before editing behavior.
  **Verify:** decide the public skill surface for `mpi-init`,
  `mpi-project-setup`, `mpi-project-refresh`, and `mpi-project-mode`; record the
  decision in this plan before making behavioral edits.

- [x] Redesign `mpi-init` as the project onboarding/adoption entrypoint.
  **Verify:** the skill supports these states: no MPI files, legacy
  `.claude/mpi-kanban/`, legacy `.agents/mpi-kanban/kanban.md`, existing
  `board.json` without profile/index, existing profile/index without board, and
  fully initialized project.

- [x] Redesign `mpi-project-refresh` as the maintenance/update entrypoint.
  **Verify:** the skill refuses to bootstrap a brand-new MPI project, but can
  update profile/index, validate JSON board/task workspaces, propose legacy
  migration cleanup, update mode, and repair documentation drift after approval.

- [x] Remove or route the redundant setup/mode surface.
  **Verify:** README, SPEC, skill descriptions, and `skills.sh.json` no longer
  present three competing project-start commands. If compatibility wrappers
  remain, their instructions clearly route to the canonical skill.

- [x] Fix validator release reproducibility.
  **Verify:** `python scripts/validate_plugin.py` passes from a clean checkout
  without ignored `.agents/` state, while still validating tracked templates,
  references, and any fixture state that should be release-gated.

- [x] Align release-facing documentation.
  **Verify:** README and `docs/install.md` describe the new lifecycle commands,
  legacy migration route, VS Code extension contract, and npx-only install path
  without stale setup/init ambiguity.

- [x] Align changelog for the target release.
  **Verify:** the changelog has a dated version section for the next tag and
  explicitly mentions the lifecycle-skill simplification, JSON board contract,
  `mpi-nimbalyst-sync`, validator fix, and documentation updates.

- [x] Sync event type references with the VS Code extension.
  **Verify:** SPEC and `mpi-lib` task-board references either include
  `checklist.item_checked` / `checklist.item_unchecked` or document them as
  extension-emitted event aliases.

- [x] Run release validation.
  **Verify:** validator passes, contradiction searches are clean, changelog
  extraction returns real release notes for the intended version, and any
  available local npx install/list smoke test is recorded.

## Completed

- [x] Lifecycle skill surface simplified: `mpi-init` owns onboarding/adoption,
  `mpi-project-refresh` owns maintenance and mode changes, and separate setup
  and mode skills are retired.
- [x] Validator now checks tracked interop/profile/index templates instead of
  requiring ignored local `.agents/` state.
- [x] README, install docs, SPEC, skill metadata, and event references were
  aligned with the new lifecycle model.

## Remaining Work

- None for this plan. Final tag/push and public remote install verification
  remain for the clean release session.

## Verification Log

- `python scripts/validate_plugin.py` passed.
- `python scripts/extract_changelog.py 0.7.0` returned real release notes.
- Targeted contradiction sweeps found no active docs or skill instructions that
  route users to retired setup/mode skills.
- `npx skills add . --all -y -g` found and installed 14 local skills.
- `npx skills add . -l` listed 14 local skills, with `mpi-project-setup` and
  `mpi-project-mode` absent.

## Plan Drift

- None yet.

## Verification

Final verification should include:

- `python scripts/validate_plugin.py`
- changelog extraction for the intended release version
- targeted searches for stale `mpi-project-setup`, `mpi-project-mode`,
  `kanban.md` live-board, plugin packaging, and checklist event wording
- local skill-pack install/list smoke test if network/install permissions allow

## Preservation Notes

- The public release is still pre-release enough to allow breaking workflow
  changes, but old installed users need clear migration wording.
- Preserve the npx-only distribution decision.
- Keep the JSON task board contract compatible with the VS Code extension.
