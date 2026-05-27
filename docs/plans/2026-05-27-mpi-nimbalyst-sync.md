# MPI Nimbalyst Sync

## Current State

Project mode: scalable-foundation.

MPI Kanban currently has a locked four-column board contract:
`BACKLOG`, `PLANNING`, `IMPLEMENTING`, and `COMPLETED`. The contract is
declared in `SPEC.md`, shared kanban references under `skills/mpi-lib/`, board
templates, workflow skills, validation tooling, and the companion VS Code
extension at `C:\AI\Mpi\Plugins\mpi-kanban-vscode`.

Nimbalyst already has a native session kanban with phases:
`backlog`, `planning`, `implementing`, `validating`, and `complete`.
It also has tracker MCP tools and project instructions that tell agents to
update session phase and tracker items directly. The interop design must avoid
dual-writing both Nimbalyst trackers and `.agents/mpi-kanban/kanban.md` during
normal work.

Reference repository: `https://github.com/nimbalyst/nimbalyst`

## Completed

- [ ] Nothing yet.

## Remaining Work

## Phase 1: Add VALIDATING To MPI Kanban

- [ ] Define `## VALIDATING` as a first-class board column between
  `IMPLEMENTING` and `COMPLETED` in the MPI board contract. **Verify:** `SPEC.md`
  and shared schema docs show exactly five columns in the order
  `BACKLOG -> PLANNING -> IMPLEMENTING -> VALIDATING -> COMPLETED`.
- [ ] Update board templates and parser/reference docs so new boards bootstrap
  with `VALIDATING`, while existing four-column boards get a deliberate
  migration path. **Verify:** templates under `skills/mpi-lib/` and
  `skills/mpi-init/` contain `## VALIDATING`, and kanban ops docs describe how
  legacy boards are handled.
- [ ] Update workflow semantics so completed implementation moves to
  `VALIDATING`, and only explicit user approval promotes work to `COMPLETED`.
  **Verify:** `mpi-continue`, `mpi-end-session`, and shared step/plan references
  describe the new validation gate consistently.
- [ ] Coordinate the companion VS Code extension schema change before treating
  five-column boards as the only supported format. **Verify:**
  `C:\AI\Mpi\Plugins\mpi-kanban-vscode` can parse, render, drag, and persist the
  `VALIDATING` column without losing entries.

## Phase 2: Define Source-Of-Truth Modes

- [ ] Add a small durable interop/mode state contract under
  `.agents/mpi-kanban/state/interop.json`. **Verify:** the contract records the
  active source of truth, last detected environment, last sync/export time, and
  ID mappings without adding metadata fields to board entries.
- [ ] Define `file` mode as the default portable mode where agents mutate
  `.agents/mpi-kanban/kanban.md`. **Verify:** non-Nimbalyst environments keep
  the existing workflow behavior, aside from the new `VALIDATING` lifecycle.
- [ ] Define `nimbalyst` mode as the mode where Nimbalyst sessions/trackers are
  canonical and the Markdown board is only imported/exported on explicit
  boundaries. **Verify:** the skill instructions clearly tell agents not to
  update both systems during normal Nimbalyst work.

## Parallel Batch: Nimbalyst Interop Skill Design

- [ ] Create the `mpi-nimbalyst-sync` skill contract and command vocabulary.
  Ownership: `skills/mpi-nimbalyst-sync/`, `skills.sh.json`, `README.md`.
  Briefings: kanban-board-contract, skill-runtime-references. **Verify:** the
  skill is listed by validation and explains detect/import/export/mode-switch
  flows without implementation ambiguity.
- [ ] Design environment detection for Nimbalyst availability through MCP tool
  presence and session phase support. Ownership: `skills/mpi-nimbalyst-sync/`.
  Briefings: skill-runtime-references. **Verify:** the design distinguishes
  Nimbalyst from generic agent environments and has a safe fallback to file
  mode.
- [ ] Define the Nimbalyst tracker schema and mapping fields for MPI entries.
  Ownership: `skills/mpi-nimbalyst-sync/`, `docs/`. Briefings:
  kanban-board-contract. **Verify:** mappings cover title, column/phase,
  priority, tags, plan file, board path, tracker ID, and session references.

## Phase 3: Import And Export Flows

- [ ] Implement file-mode to Nimbalyst import with a dry run first. **Verify:**
  a board with BACKLOG, PLANNING, IMPLEMENTING, VALIDATING, and COMPLETED
  entries can be converted into Nimbalyst tracker items without mutating the
  source board unless the user approves.
- [ ] Implement Nimbalyst to file-mode export/snapshot. **Verify:** Nimbalyst
  trackers/sessions can produce a schema-valid `.agents/mpi-kanban/kanban.md`
  with stable plan file references and no unsupported metadata fields.
- [ ] Add conflict detection for changed items on both sides since the last
  sync boundary. **Verify:** conflicts produce a clear refusal/proposal instead
  of silent overwrites.

## Phase 4: Workflow Integration

- [ ] Update planning/continue/end-session skills to consult interop mode before
  mutating work state. **Verify:** in `nimbalyst` mode, workflow skills defer to
  Nimbalyst tracker/session instructions; in `file` mode, they mutate the MPI
  board.
- [ ] Add mode-switch prompts for entering or leaving Nimbalyst. **Verify:** the
  user is prompted when the detected environment differs from the last active
  source-of-truth mode.
- [ ] Document the expected user experience for VS Code, generic agents, and
  Nimbalyst. **Verify:** README/install docs explain which system agents update
  in each mode.

## Plan Drift

- None yet.

## Verification

- `python scripts/validate_plugin.py`
- Targeted contradiction sweep for old four-column-only language.
- Local board migration smoke test from a four-column board to a five-column
  board.
- VS Code extension smoke test against a five-column board.
- Nimbalyst import/export dry-run test using the tracker MCP tool contract from
  `https://github.com/nimbalyst/nimbalyst`.

## Preservation Notes

- This plan intentionally makes `VALIDATING` the first implementation phase.
- Do not add new entry metadata fields; use body references or
  `.agents/mpi-kanban/state/interop.json` for interop state.
- Nimbalyst already instructs agents to update sessions and trackers. In
  `nimbalyst` mode, MPI must not create a competing live board write path.
