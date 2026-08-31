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

- [x] Establish a local VS Code extension preview/smoke workflow in
  `C:\AI\Mpi\Plugins\mpi-kanban-vscode`. **Verify:** the workflow runs locally
  without publishing an extension build and shows the real board UI for review.

## Completed

- [x] Added a curated fixture board at
  `test/fixtures/sample-board/.agents/mpi-kanban/kanban.md` that exercises every
  render path (5 columns, all priority/workload badges, upcoming + overdue due
  dates, single/multi tags, collapsed + expanded cards, 0/1, 2/4, 2/2 step
  bars).
- [x] Added a `Run Extension (sample board)` launch config (started via Command
  Palette -> "Debug: Select and Start Debugging") that compiles the extension
  and opens an Extension Development Host on the fixture with the board already
  open, plus an `Extension Tests` debug config.
- [x] Wrote `CONTRIBUTING.md` documenting the F5 preview (human eyeball review),
  fixture reset, and `npm test` parser regression run (with the first-run
  VS Code download note).
- [x] Verified `npm run compile` and `npm run compile-tests` both pass.

## Remaining Work

- None. Done. The harness unblocks the JSON task board plan's dependency
  ("preview locally without publishing"). User confirmed the dev host launches
  on the fixture. The fixture and UI scenarios are intentionally Markdown-shaped
  for the current extension; the JSON board plan's "VS Code Extension Update"
  batch owns rebuilding both for the `To do / Doing / Done` JSON board.

## Plan Drift

- The plan originally framed this as automated smoke scenarios (open/render/
  drag/file-write assertions). Clarified with the user: the goal is a
  human-in-the-loop preview harness — the agent changes the UI, the user
  launches the dev host and judges it. Automated coverage stays at the parser
  unit-test layer (`npm test`); no Playwright / webview-iframe automation was
  added.

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
