# Project Knowledge and Architectural Intent - Phase 4

## Current State

The plugin currently focuses on workflow state:

- Human-visible work lives in `.claude/mpi-kanban/kanban.md`.
- Runtime multi-agent coordination lives in `.agents/mpi-kanban/state/`.
- Plans and handoffs preserve active work state.
- `mpi-init` can bootstrap or import a kanban board.
- `mpi-brainstorm`, `mpi-create-plan`, `mpi-create-large-plan`, and
  `mpi-continue` guide work once a task exists.

What is still missing is durable project knowledge. A fresh agent session can
coordinate with other sessions, but it may still have to rediscover the same
project architecture, conventions, documentation, rules, memory pointers, and
engineering intent repeatedly.

Phase 4 adds a model-neutral project knowledge layer and architectural intent
system. The goal is not to make every project heavy or overengineered. The goal
is to stop agents from silently assuming prototype-style coding, while also
giving future sessions a compact map of what to read instead of scanning the
whole project every time.

This phase must remain after Phase 3. Phase 3 makes Codex discovery and
invocation official; Phase 4 builds on that broader agent compatibility.

Hard constraints:

- Do not change kanban columns or metadata fields.
- Keep `mpi-init` narrowly focused on board bootstrap/import. Add project
  establishment behavior as new skills instead of turning init into a large
  catch-all skill.
- Prefer adopting or improving existing project docs, rules, memory, and
  backlog/process files over creating parallel systems.
- Use pointer/index files so agents load task-relevant context, not every rule
  and document on every session.
- Keep the system model-neutral. Documentation should be explicit enough for
  Claude Code, Codex, OpenAI API agents, Anthropic API agents, or other capable
  agent runtimes to follow.
- Setup and refresh may inspect the repository, but must show a proposal and
  wait for user approval before creating or modifying project docs, rules,
  memory, profile, or agent instruction files.
- Project setup may create or update `AGENTS.md` directly after the user
  approves the setup proposal. The default strategy is pointer-first: keep
  existing agent entrypoints concise and point them at MPI profile/index files
  instead of duplicating project knowledge.

Approved planning decisions:

- Project modes are `prototype`, `mvp`, and `scalable-foundation`.
- `scalable-foundation` is the default when project mode is unclear.
- New skill names are `mpi-project-setup`, `mpi-project-mode`, and
  `mpi-project-refresh`.
- Profile and knowledge index files live at
  `.agents/mpi-kanban/project-profile.md` and
  `.agents/mpi-kanban/project-knowledge-index.md`, outside
  `.agents/mpi-kanban/state/`.
- `mpi-project-refresh` audits and proposes updates when repository reality
  drifts from the project profile, knowledge index, rules, memory pointers,
  commands, architecture summary, or conventions.
- `mpi-end-session` performs a lightweight refresh proposal when work changes
  architecture, conventions, commands, or agent guidance.
- Memory writes require explicit approval. Prefer pointing to existing Claude
  memory before proposing new or changed memory entries.

## Completed

- [x] `lib/project-intent/modes.md` — mode contracts, default-mode rule,
  intentional engineering guardrails.
- [x] `lib/project-knowledge/` — profile schema, index schema, adoption,
  indexing, updates.
- [x] `templates/project-profile.md`, `templates/project-knowledge-index.md`.
- [x] `skills/mpi-project-setup/SKILL.md` — establish project knowledge with
  approval gate and clarification loop.
- [x] `skills/mpi-project-mode/SKILL.md` — review/reaffirm/change mode with
  migration notes.
- [x] `skills/mpi-project-refresh/SKILL.md` — drift audit and lightweight mode
  reassessment.
- [x] Wire `mpi-brainstorm` (new-project routing), `mpi-create-plan` and
  `mpi-create-large-plan` (profile/index read), `mpi-continue`
  (profile/index read + Continue Brief fields), `mpi-handoff`
  (`project_knowledge` JSON), `mpi-end-session` (lightweight refresh and
  report line), `mpi-cleanup` (profile/index as active by default).
- [x] Update `SPEC.md` (skill set, §10b project knowledge, acceptance
  criteria), `README.md` (skill list, invocation surface, NL phrases,
  project-knowledge section, planning model line), `AGENTS.md` (skill list
  and project-knowledge section), `PLAN.md` (Phase 4 status), plugin
  manifests, and `.claude-plugin/marketplace.json` description.
- [x] `python scripts/validate_plugin.py` — passed.

## Remaining Work

- [ ] Live-copy update: run `update_live.py` only when the user explicitly
  asks. Phase 4 implementation lands separately from the live cache push.
- [ ] Smoke test the new skills end-to-end in a real project (setup -> mode
  switch -> brainstorm -> plan -> continue -> handoff -> end-session ->
  refresh).

## Plan Drift

- None yet.

## Verification

Before Phase 4 is considered complete:

1. A new project setup flow asks for mode, defaults to scalable foundation when
   unclear, and writes approved profile/index/rule/memory artifacts.
2. An existing project setup flow adopts or improves existing docs/rules/memory
   before creating new MPI-specific artifacts.
3. Future sessions can read project profile and knowledge index first, then
   load task-relevant files instead of rediscovering the whole project.
4. Users can change project mode later and preserve the rationale.
5. Users can refresh stale project knowledge and prevent drift.
6. Planning, continue, handoff, and end-session skills consume and maintain
   project knowledge without bloating context.
7. The kanban schema remains unchanged.
8. Plugin docs, metadata, validation, and live-copy rules agree on the new
   skill set.

## Preservation Notes

- The former backlog idea "Improve init skill" is superseded by this Phase 4
  plan. `mpi-init` should stay focused on board bootstrap/import.
- This phase should not start until Phase 3 is complete.
- Keep all project knowledge files pointer-driven. The profile and index should
  help agents know what to read, not duplicate every project rule or document.
