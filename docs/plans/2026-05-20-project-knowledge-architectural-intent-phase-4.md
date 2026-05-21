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

## Completed

- [ ] Nothing yet.

## Remaining Work

## Phase 1: Project Intent Reference Model

- [ ] Add `lib/project-intent/modes.md` defining `prototype`, `mvp`, and
  `scalable-foundation` as explicit behavior contracts. **Verify:** each mode
  defines planning depth, acceptable shortcuts, hardcoding/duplication stance,
  reuse expectations, file/module structure expectations, clarification
  behavior, and preservation requirements.
- [ ] Define the default mode rule: new projects ask the user for mode, and
  unanswered/unclear mode defaults to scalable foundation; existing projects
  announce the mode being evaluated and default to scalable foundation unless
  project evidence or user instruction says otherwise. **Verify:** the default
  is documented in one shared reference and skills point to it instead of
  restating conflicting rules.
- [ ] Define "intentional engineering" guardrails for scalable foundation:
  reusable utilities/services/components when justified, small cohesive files,
  clean separation of concerns, clear project conventions, no silent
  hardcoding, and no design pattern/OOP ceremony unless it reduces real
  complexity. **Verify:** the reference rejects both silent prototype shortcuts
  and unnecessary overengineering.

## Phase 2: Project Knowledge Profile and Index

- [ ] Add a Markdown project profile schema for
  `.agents/mpi-kanban/project-profile.md`. **Verify:** the profile includes
  project mode, mode rationale/source, project summary, architecture summary,
  conventions, important commands, files future agents should read first,
  knowledge index path, setup/refresh dates, and open knowledge gaps.
- [ ] Add a Markdown knowledge index schema for
  `.agents/mpi-kanban/project-knowledge-index.md`. **Verify:** the index maps
  task topics to specific docs/rules/memory files so future agents can load
  only relevant context.
- [ ] Add templates for the project profile and knowledge index. **Verify:**
  templates are compact pointer files, not duplicated project encyclopedias.
- [ ] Document update rules for profile/index maintenance. **Verify:** updates
  preserve existing user-owned content, ask before modifying existing memory
  entries, and prefer pointer edits over copying long docs into the profile.

## Phase 3: Existing Knowledge Adoption Procedures

- [ ] Add `lib/project-knowledge/adoption.md` for importing existing project
  knowledge. **Verify:** it covers `AGENTS.md`, `CLAUDE.md`, `.claude/rules/*`,
  README, architecture docs, contribution docs, existing memory indexes,
  backlog/process files, and user-specified custom docs.
- [ ] Define adoption classifications: usable as-is, small update, index
  pointer, convert to MPI-managed profile/rule/memory, superseded historical
  reference, or conflict/uncertain. **Verify:** setup and refresh produce an
  adoption map before writing.
- [ ] Add `lib/project-knowledge/indexing.md` for context-budget behavior.
  **Verify:** agents read entrypoint/pointer files first and only load
  task-specific docs/rules/memory when relevant.
- [ ] Define conflict handling when existing docs disagree. **Verify:** agents
  ask the user instead of silently choosing between conflicting project rules.

## Phase 4: New Project Setup Skill

- [ ] Add `skills/mpi-project-setup/SKILL.md`. **Verify:** plugin metadata,
  README command list, and validation include the new skill.
- [ ] Support new-project setup after `mpi-brainstorm`: ask for project mode,
  default to scalable foundation if unanswered, ask a small set of setup
  questions, and propose initial knowledge artifacts. **Verify:** no project
  files are written before the user approves the setup proposal.
- [ ] Support existing-project setup: ask whether the user has existing
  backlog/docs/rules/memory/process files, inspect conventional entrypoints,
  identify current architecture, and propose an adoption map. **Verify:** the
  skill improves or indexes existing sources before proposing new files.
- [ ] Include a clarification loop before approval. **Verify:** the user can
  ask why a file should be created/updated, skip an artifact, change project
  mode, or redirect adoption before writes happen.
- [ ] Create or update approved artifacts: kanban board via existing board
  procedures, project profile, knowledge index, agent entrypoint pointers, rule
  docs, memory pointers, and initial backlog/plan pointers as appropriate.
  **Verify:** generated files are concise, pointer-driven, and model-neutral.

## Phase 5: Project Mode Skill

- [ ] Add `skills/mpi-project-mode/SKILL.md`. **Verify:** users can review,
  reaffirm, or change the current project mode without rerunning setup.
- [ ] Support mode transitions such as prototype -> MVP and MVP -> scalable
  foundation. **Verify:** the skill explains behavior changes and records mode
  rationale in the project profile.
- [ ] Record migration notes when a mode change exposes known shortcuts or
  technical debt from the prior mode. **Verify:** changing mode does not force
  an immediate rewrite; it updates future work behavior and preservation notes.

## Phase 6: Project Refresh Skill

- [ ] Add `skills/mpi-project-refresh/SKILL.md`. **Verify:** users can
  re-evaluate project knowledge later without starting a new task.
- [ ] Detect drift between profile/index/rules/memory and current repository
  reality. **Verify:** refresh proposes updates for stale architecture,
  commands, conventions, task-topic pointers, rules, and memory.
- [ ] Use the same adoption and approval model as setup. **Verify:** refresh
  does not overwrite user-owned docs or memory without explicit approval.
- [ ] Include lightweight mode reassessment. **Verify:** refresh announces the
  current mode, notes evidence for or against it, and suggests `mpi-project-mode`
  when a deliberate change is needed.

## Phase 7: Existing Skill Integration

- [ ] Update `mpi-brainstorm` to route new-project ideas into
  `mpi-project-setup` after design approval. **Verify:** brainstorming remains
  conversational and does not write setup artifacts directly.
- [ ] Update `mpi-create-plan` and `mpi-create-large-plan` to read the project
  profile/knowledge index when present and include architectural intent in
  plan current state. **Verify:** planning uses project mode without loading
  unrelated docs.
- [ ] Update `mpi-continue` to read project profile/index before the Continue
  Brief and include mode, relevant conventions, and task-specific context
  pointers. **Verify:** implementation does not start from a blank
  rediscovery pass when project knowledge exists.
- [ ] Update `mpi-handoff` to include project profile and knowledge-index
  pointers in canonical handoff JSON. **Verify:** fresh sessions know which
  context files to read first.
- [ ] Update `mpi-end-session` to refresh profile/index/rules/memory when
  implementation changes architecture, conventions, commands, or agent
  guidance. **Verify:** end-session preserves knowledge and prevents drift
  without bloating context files.
- [ ] Update `mpi-cleanup` if new stale profile/index/setup artifacts need
  conservative cleanup classification. **Verify:** cleanup never deletes active
  project knowledge by default.

## Phase 8: Documentation, Validation, and Future Compatibility

- [ ] Update `SPEC.md`, `README.md`, `AGENTS.md`, and `PLAN.md` for the new
  skills and project knowledge contract. **Verify:** public docs describe the
  same setup, mode, refresh, profile, and index behavior.
- [ ] Update `.claude-plugin/plugin.json` description/keywords if needed.
  **Verify:** the plugin presents the expanded skill set accurately.
- [ ] Update `update_live.py` or `.gitignore` only if new files require copy or
  exclusion changes. **Verify:** live-copy behavior includes shipped skills,
  libs, docs, and templates without copying development-only state.
- [ ] Run `python scripts/validate_plugin.py` and targeted contradiction
  searches. **Verify:** skill names/frontmatter match folders and old init-only
  setup language is gone or explicitly marked as superseded.
- [ ] Do not run `update_live.py` until Phase 4 implementation is complete and
  the user explicitly asks for the live cache update. **Verify:** validation
  can run without mutating the installed plugin.

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
