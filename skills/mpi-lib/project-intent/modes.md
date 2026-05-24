# Project Modes

Defines the three project modes Mpi-Kanban skills use to set planning depth,
acceptable shortcuts, and engineering intent. The mode is a behavior contract,
not a label. Skills read this file when proposing or evaluating project mode.

The active mode for a project is recorded in
`.agents/mpi-kanban/project-profile.md` under `mode:` with a short
`mode_rationale:` line. `mpi-project-mode` is the only skill that changes mode.

## Default mode rule

- **New project, mode not yet asked or unclear:** `mpi-project-setup` asks the
  user explicitly. If the user declines to answer, defaults to
  `scalable-foundation`.
- **Existing project, no recorded mode:** `mpi-project-setup` and
  `mpi-project-refresh` announce which mode is being evaluated. Default is
  `scalable-foundation` unless repo evidence or user instruction says
  otherwise (for example, "this is a throwaway prototype" or a clear MVP
  README/CHANGELOG framing).
- **Mode change without rerunning setup:** use `mpi-project-mode`.

This rule is the single source. Other skills must point here instead of
restating their own defaults.

## Mode contracts

### prototype

Throwaway, exploratory, demo, spike, or research code with no production users.

- **Planning depth:** compact plans by default. Skip multi-phase plans unless
  the user explicitly asks.
- **Acceptable shortcuts:** inline values, hardcoded paths, duplicated logic,
  stub error handling, minimal tests are acceptable when they make the spike
  ship faster.
- **Hardcoding/duplication stance:** allowed silently.
- **Reuse expectations:** none. Copy-paste is fine; do not invent shared
  utilities just to avoid two similar snippets.
- **File/module structure:** flat is fine. Do not enforce package boundaries
  or layered architecture.
- **Clarification behavior:** prefer running fast. Ask the user only when a
  decision is plainly destructive or genuinely ambiguous.
- **Preservation requirements:** record only the design intent and the
  shortcuts taken so a later mode transition has context. No formal
  architecture docs.

### mvp

First real version with users or stakeholders. Correctness over polish.

- **Planning depth:** compact plans for normal work; large plans when the
  change affects multiple subsystems or has real risk.
- **Acceptable shortcuts:** time-boxed shortcuts are OK if explicitly noted as
  technical debt in plan `## Preservation Notes` or
  `.agents/mpi-kanban/project-profile.md` `open_gaps`.
- **Hardcoding/duplication stance:** flag with a one-line "intentional for
  MVP" note when used; do not silently bake in. Three obvious duplicates is
  better than a premature abstraction; six is a refactor candidate.
- **Reuse expectations:** introduce shared utilities only when the same logic
  appears in 3+ places or when correctness depends on a single source of
  truth.
- **File/module structure:** small, cohesive files with clear separation of
  concerns at module boundaries. Avoid deep layered abstractions.
- **Clarification behavior:** ask the user when a decision sets a public
  contract (API shape, data model, user-visible flow) or when two reasonable
  interpretations exist.
- **Preservation requirements:** keep the project profile, knowledge index,
  and active plan honest. Record real architecture changes; do not log every
  edit.

### scalable-foundation

The default mode. Code is intended to grow: more features, more contributors,
more surface area. Engineering intent matters from the first commit.

- **Planning depth:** prefer large plans for non-trivial work. Use parallel
  batches whenever ownership is disjoint and verification is batch-safe.
- **Acceptable shortcuts:** none silent. Any shortcut must be named in the
  plan `## Preservation Notes` with a recovery path.
- **Hardcoding/duplication stance:** no silent hardcoding. Configuration,
  environment values, and magic constants belong in declared, named locations.
  Duplication is fine for genuinely independent code paths; suspicious when
  changes have to be mirrored across files.
- **Reuse expectations:** reusable utilities, services, and components when
  they remove real complexity. Do not invent abstractions for a single
  caller, do not add OOP/design-pattern ceremony that does not pay off.
- **File/module structure:** small cohesive files, clean separation of
  concerns, clear conventions for where new code goes. Document those
  conventions in the project profile or a referenced rule.
- **Clarification behavior:** surface tradeoffs explicitly. When two
  approaches are both defensible, present both with the recommended choice
  and the reason. Ask before introducing a new abstraction layer.
- **Preservation requirements:** keep architecture summary, conventions,
  knowledge index, and rules current. `mpi-end-session` proposes profile and
  index updates when implementation changes architecture, conventions,
  commands, or agent guidance.

## Intentional engineering guardrails (scalable-foundation)

`scalable-foundation` rejects both ends of the spectrum:

- Reject silent prototype shortcuts: inline secrets/paths/magic numbers,
  copy-pasted logic that must stay in sync, unwritten conventions, missing
  error boundaries at system edges.
- Reject unnecessary overengineering: abstract base classes for a single
  caller, dependency injection containers for a flat module, plugin systems
  with no second plugin, feature flags for code that has no rollback path,
  configurability the user did not ask for.

The guardrail is the same rule, stated two ways: every abstraction must
remove more complexity than it adds, and every shortcut must be named.

## Mode transitions

`mpi-project-mode` handles transitions. The transition does not force a
rewrite. It updates future work behavior and records migration notes in the
project profile so later sessions know which areas still carry prior-mode
shortcuts.

Typical transitions:

- `prototype` -> `mvp`: list known prototype shortcuts as `open_gaps` in the
  project profile. New work follows mvp rules; old shortcuts are recovered
  opportunistically as their files are touched.
- `mvp` -> `scalable-foundation`: same pattern. Record the conventions the
  project is adopting and the areas that predate them.
- Downgrades (`scalable-foundation` -> `mvp`, `mvp` -> `prototype`) are
  unusual. When requested, the skill confirms the intent and notes the
  reason in the profile.
