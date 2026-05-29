# Extension Smoke Tests

## Current State

Project mode: scalable-foundation.

The companion VS Code extension lives at
`C:\AI\Mpi\Plugins\mpi-kanban-vscode`. It already declares `@vscode/test-cli`
and `@vscode/test-electron` in `package.json`, with `npm test` mapped to
`vscode-test`. The current extension renders `.agents/mpi-kanban/kanban.md` in a
webview, but the planned JSON task-board redesign will need much stronger local
verification before UI and state changes are made.

Official VS Code extension testing guidance supports local extension-host tests
with `@vscode/test-cli` / `@vscode/test-electron`, workspace fixtures, launch
arguments, and Mocha tests that can access the VS Code API. That is the right
foundation for smoke testing without publishing VSIX builds.

This work should happen before the JSON task-board redesign. The goal is not to
redesign the board yet; the goal is to create a repeatable way to prove the
extension opens, renders, responds to basic UI actions, and persists expected
workspace files locally.

## Implementation

- [ ] Establish a local VS Code extension smoke-test workflow in
  `C:\AI\Mpi\Plugins\mpi-kanban-vscode` using the existing VS Code test tooling:
  inspect the current test harness, add or update fixture workspace data,
  define the minimum smoke scenarios for opening the board webview, rendering
  cards, dragging/mutating entries where feasible, and verifying file writes,
  then document the exact local command agents should run before extension UI
  changes. **Verify:** the smoke workflow runs locally without publishing an
  extension build and clearly reports pass/fail for the extension board surface.

## Completed

- [ ] Nothing yet.

## Remaining Work

- Establish the local extension smoke-test workflow and document how agents
  should use it before changing the companion extension UI.

## Plan Drift

- None yet.

## Verification

Run the new or updated extension smoke-test command from
`C:\AI\Mpi\Plugins\mpi-kanban-vscode` and confirm it can validate the board UI
against a local fixture workspace without publishing a VSIX.

## Preservation Notes

- Preserve the current MPI skill-pack repository as the source for workflow
  behavior; extension test implementation belongs in the companion extension
  checkout.
- Keep the test workflow compatible with future JSON task-board work, but do not
  implement the JSON board architecture in this plan.
- If the final command requires network on first run because VS Code must be
  downloaded by `@vscode/test-electron`, document that clearly.
