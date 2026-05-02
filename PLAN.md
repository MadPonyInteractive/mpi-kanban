# Mpi-Kanban — Build Plan

> **Source spec:** [SPEC.md](./SPEC.md)
>
> **Instructions for the executing agent:**
>
> 1. Read SPEC.md in full before starting. It is the source of truth.
> 2. This plan is phased. Each phase's to-dos are checkable items.
> 3. Before executing, evaluate each phase against current Claude Code plugin authoring docs (the spec was written without verifying the latest plugin docs in detail). Revise phases or to-do ordering if the docs prescribe a different structure — e.g. if `plugin.json` is renamed, if SKILL.md frontmatter changed, or if local-install commands differ.
> 4. Use any plugin-creation skills the user gives you (skill-creator, plugin scaffolders, etc.) to bootstrap structure. Cross-check the result against SPEC.md Section 3.
> 5. Execute one phase at a time. Verify the phase's success criteria before moving on. Phases are independently verifiable.
> 6. Do NOT modify SPEC.md without asking the user. If the spec is wrong, surface it and propose a change.

---

## Phase 1: Plugin scaffold + metadata

Goal: `Mpi-Kanban/` has a valid plugin shell that Claude Code can load (even with empty skills).

- [ ] Create `plugin.json` with name `Mpi-Kanban`, version `0.1.0`, description matching SPEC Section 1, author info, and any required marketplace fields per current Claude Code plugin docs.
- [ ] Create `LICENSE` (MIT or whatever the user prefers — ask if unclear).
- [ ] Create `README.md` per SPEC Section 11 (user-facing): install steps, workflow overview, VS Code extension link, per-project setup. Keep it under ~150 lines.
- [ ] Create empty folder structure per SPEC Section 3: `skills/`, `lib/`, `templates/`.
- [ ] Verify the plugin can be installed locally (per Claude Code plugin docs — confirm exact command at build time).
- [ ] Verify Claude Code recognizes the plugin (lists in plugin list, even with no skills yet).

**Verify:** Run the local-install command, then `/plugin list` (or current equivalent). `Mpi-Kanban` appears with description.

---

## Phase 2: Templates

Goal: `templates/kanban.md` and `templates/config.json` exist and are correct.

- [ ] Write `templates/kanban.md`:
  - 4 H2 columns in order (BACKLOG, PLANNING, IMPLEMENTING, COMPLETED).
  - Empty between columns.
  - HTML comment at top with one-line note about the VS Code extension and the marketplace link `https://marketplace.visualstudio.com/items?itemName=holooooo.markdown-kanban`.
- [ ] Write `templates/config.json` per SPEC Section 5.2 — empty `rules` array, sensible defaults for `rules_dir`, placeholder for `critical_snapshot_file` and `critical_snapshot_anchor`.
- [ ] Add one short comment line in `templates/config.json` (or a sibling `templates/config.example.json`) explaining each field. JSON does not allow comments, so use a parallel `.example.json` with a comment block above each key, or a `templates/config.README.md`.

**Verify:** Open both templates manually. The kanban template renders cleanly in the VS Code extension as 4 empty columns. The config template parses as valid JSON.

---

## Phase 3: Lib reference docs

Goal: All three `lib/*.md` reference docs exist and document the procedures listed in SPEC Section 7.

- [ ] Write `lib/kanban-ops.md`:
  - Parser regexes (column heading, entry heading, metadata bullet, body fence).
  - Procedure for each operation listed in SPEC 7.1.
  - For each mutation, state the exact `Edit` tool sequence the calling skill should run.
  - Document error cases (duplicate title, missing column, malformed entry, unknown metadata field).
  - Include a small example showing the before/after for a `moveEntry` call.
- [ ] Write `lib/plan-ops.md`:
  - Phase detection regex (per SPEC 6.3.1).
  - Procedures from SPEC 7.2.
  - Decision tree for "is this plan phased?".
  - Worked example for both phased and flat plans.
- [ ] Write `lib/config-ops.md`:
  - Config schema (mirror SPEC Section 5.2 — do not duplicate the spec, link to it).
  - Procedures from SPEC 7.3.
  - Bootstrap snippet text the skill emits when config is missing.

**Verify:** Each file is self-contained — a fresh skill author can implement a kanban mutation by reading only `lib/kanban-ops.md` (no need to also read SPEC.md).

---

## Phase 4: Migrate `mpi-brief-rule`

Goal: `mpi-brief-rule` is generalized and works against `.claude/mpi-kanban/config.json` instead of a hardcoded rule list.

- [ ] Copy current `~/.claude/skills/mpi-brief-rule/SKILL.md` into `skills/mpi-brief-rule/SKILL.md`.
- [ ] Strip the hardcoded "Supported Rules" list (CubricStudio-specific).
- [ ] Replace with a flow that reads `.claude/mpi-kanban/config.json` via `lib/config-ops.md`.
- [ ] If config missing → emit setup notice per SPEC Section 5.3, then stop.
- [ ] If named rule not in config → list available rule names and stop.
- [ ] If rule has no `## Sub-Agent Briefing` section → fall back to the critical snapshot per SPEC Section 6.6.
- [ ] Update the skill description in frontmatter to match the new behavior (still triggers on `/mpi-brief-rule <name>`).

**Verify:** In a project with no config → invoking the skill prints the bootstrap snippet and stops. With a valid config and a rule that has a briefing → returns the briefing verbatim. With a rule missing the briefing section → returns the critical snapshot.

---

## Phase 5: Migrate `mpi-handoff`

Goal: `mpi-handoff` writes a JSON handoff with the active kanban entry, no Nimbalyst calls.

- [ ] Copy `~/.claude/skills/mpi-handoff/SKILL.md` into `skills/mpi-handoff/SKILL.md`.
- [ ] Remove all `mcp__nimbalyst-*` calls and any references to Nimbalyst.
- [ ] Add a step to read `kanban.md` and locate the active IMPLEMENTING entry (entry whose `Plan file:` matches the active plan).
- [ ] Add a `kanban_entry: "<title>"` field to the JSON schema. If no IMPLEMENTING entry matches → set `kanban_entry: null`.
- [ ] Update the resume prompt block to mention the kanban entry by title, so a fresh session can re-orient quickly.

**Verify:** Run the skill mid-task in a project with one IMPLEMENTING entry. The output JSON contains the entry title in `kanban_entry`. The resume prompt mentions it.

---

## Phase 6: Migrate `mpi-brainstorm`

Goal: After design approval, the skill creates a BACKLOG entry on `kanban.md`.

- [ ] Copy current `mpi-brainstorm/SKILL.md` into `skills/mpi-brainstorm/SKILL.md`.
- [ ] Strip the `mcp__nimbalyst-session-naming__update_session_meta` call.
- [ ] After "design approved" gate and BEFORE the "Want a plan?" prompt, add the BACKLOG entry creation flow per SPEC Section 6.1.
  - Auto-create kanban.md if missing per SPEC Section 4.7.
  - Use `lib/kanban-ops.md` `createEntry` procedure.
  - Ask the user once for `priority` (default `medium`).
  - Tags inferred from idea content; choose from `[bug] | [feature] | [Idea] | [refactor]`.
- [ ] In the "Want a plan?" prompt branch:
  - If yes → invoke `mpi-write-plan` AND pass the BACKLOG entry title forward (via prompt context, since skills don't pass arguments natively — write the title into the chat for the next skill to pick up).

**Verify:** Run brainstorm end-to-end. After approval, kanban.md gains a BACKLOG entry with correct shape. The "Want a plan?" prompt is shown after the entry is created, not before.

---

## Phase 7: Migrate `mpi-write-plan`

Goal: Plan creation moves an existing BACKLOG entry to PLANNING (or creates a new PLANNING entry), no Nimbalyst trackers.

- [ ] Copy current `mpi-write-plan/SKILL.md` into `skills/mpi-write-plan/SKILL.md`.
- [ ] Remove the `mcp__nimbalyst-session-naming__update_session_meta` call (current step 2).
- [ ] Remove steps 8 and 9 entirely (Nimbalyst tracker creation + tracker metadata block).
- [ ] Update step 7 (write plan file) — no `<!-- trackers -->` block.
- [ ] After plan file is written, add a kanban update step:
  - If a BACKLOG entry matches (passed in by brainstorm or matched by user-provided title) → move BACKLOG → PLANNING, replace tags with `[PLAN]`, set body fence to `Plan file: <plan-path>`.
  - If no entry matches → create a new PLANNING entry directly with `[PLAN]` tag.
  - Use `lib/kanban-ops.md` procedures.
- [ ] Update "Related commands" section to remove `/mpi-quick-plan` reference (out of plugin scope) — or keep it conditionally if the user keeps that skill separately.
- [ ] Update the "self-audit" step (current step 6) — keep it, drop the Nimbalyst guidance.

**Verify:** Two scenarios: (a) brainstorm produced a BACKLOG entry, write-plan moves it to PLANNING with correct tag swap and body update; (b) write-plan invoked directly with no prior entry, creates a fresh PLANNING entry with `[PLAN]` tag.

---

## Phase 8: Migrate `mpi-execute-next`

Goal: First execute moves PLANNING → IMPLEMENTING and adds steps; per-todo verification flips matching steps; no Nimbalyst calls.

- [ ] Copy current `mpi-execute-next/SKILL.md` into `skills/mpi-execute-next/SKILL.md`.
- [ ] Strip ALL Nimbalyst calls (session-meta + tracker-status updates throughout).
- [ ] Strip the tracker-id metadata-block lookup logic in "Session setup" (since plans no longer have it).
- [ ] On first invocation against a plan:
  - Locate kanban entry via `lib/kanban-ops.md` `findEntry` matching the plan's `Plan file:` path.
  - Move PLANNING → IMPLEMENTING.
  - Read plan file via `lib/plan-ops.md`. Determine phased vs flat (SPEC 6.3.1).
  - Build steps array (3-6 word summaries OR phase titles) and add via `addSteps`.
- [ ] On Option 1 ("verified") per to-do:
  - After marking plan to-do `[x]`, look up the matching kanban step:
    - Phased plan: if all to-dos in the current phase are `[x]`, flip the matching kanban step.
    - Flat plan: flip the kanban step at the matching index.
- [ ] Keep both gates (brief gate and post-impl gate) intact — do not weaken these.
- [ ] Update "Related commands" section to drop `/mpi-component-audit` if not in plugin scope (stay project-side).
- [ ] Replace `~/.claude/skills/mpi-execute-next/brief-template.md` reference with a brief template inside the plugin folder (`skills/mpi-execute-next/brief-template.md`).

**Verify:** Full plan run (3-5 to-dos). Phased plan: steps reflect phases, flip when phase fully `[x]`. Flat plan: each to-do flips its own step. Kanban entry moves to IMPLEMENTING on first execute call only.

---

## Phase 9: Build `mpi-end-session` (rewrite from broken file)

Goal: Proper skill format, kanban-aware close-out, no Nimbalyst.

- [ ] Read the current `~/.claude/skills/mpi-end-session/SKILL.md.md` (note the double extension — the source file).
- [ ] Create `skills/mpi-end-session/SKILL.md` (single extension) with proper skill frontmatter per SPEC Section 6.4 — `name`, `description` only.
- [ ] Translate the existing `<objective>`, `<context>`, `<process>` blocks into prose-style skill instructions.
- [ ] Replace `git diff HEAD` (full diff) with `git diff --stat HEAD` (file list only).
- [ ] Strip the Nimbalyst session-meta call (current step 6).
- [ ] Strip the `mcp__nimbalyst-mcp__get_session_edited_files` call (current context block).
- [ ] Add the kanban update step per SPEC Section 6.4 step 6-7:
  - Locate active IMPLEMENTING entry by matching `Plan file:` against the most recently touched plan.
  - Use `lib/kanban-ops.md` `allStepsDone`.
  - If true → move IMPLEMENTING → COMPLETED.
  - If false → leave; append "session ended mid-implementation" to commit body.
- [ ] Add clickable kanban link to final report.
- [ ] Keep the "ask before changing architectural rule files" cardinal-rule check intact.

**Verify:** Two scenarios: (a) all kanban steps `[x]` → entry moves to COMPLETED + clean commit; (b) mid-flight session, some steps still `[ ]` → entry stays in IMPLEMENTING + commit message has the deferred note.

---

## Phase 10: Integration test in CubricStudio

Goal: One full workflow run end-to-end against a real project.

- [ ] Install plugin locally.
- [ ] In CubricStudio, remove the existing `~/.claude/skills/mpi-*` skills (back them up first) so they don't conflict with the plugin.
- [ ] Create `.claude/mpi-kanban/config.json` for CubricStudio with its 12 rules per the existing list (components, dos_and_donts, events, state, comfy_injection, comfy_engine, workspaces, component-mounts, component-events, component-state, component-comfy, downloads).
- [ ] Run a small end-to-end: brainstorm a tiny idea → write a 2-todo plan → execute both → end session. Verify:
  - Entry moves through all 4 columns.
  - Steps are correct (phased or flat).
  - Plan file no longer contains `<!-- trackers -->` block.
  - No `mcp__nimbalyst-*` errors anywhere.
  - Kanban file is auto-created on first call (assuming pre-test state has no kanban).
  - VS Code extension renders the board correctly.
- [ ] Run `/mpi-brief-rule components` — returns the briefing from CubricStudio's components.md.
- [ ] Run `/mpi-handoff` mid-flight — JSON contains `kanban_entry`.

**Verify:** All seven sub-checks above pass. Acceptance criteria from SPEC Section 13 are all met.

---

## Phase 11: Polish + documentation

Goal: README is solid; user can install without asking the author for help.

- [ ] Tighten README based on integration-test learnings.
- [ ] Add a "Troubleshooting" section: kanban not auto-creating, VS Code extension not rendering, config.json bootstrap notice loops, etc.
- [ ] Add a "What's next" section listing the deferred decisions from SPEC Section 12, so future contributors know what's open.
- [ ] If marketplace publish is in scope: add `marketplace.json` (or current equivalent) and verify required metadata.
- [ ] Tag a `v0.1.0` git tag.

**Verify:** A second developer (or fresh session) reads only README.md and can install + use the plugin without referring to SPEC.md.

---

## Out of scope (not in this build)

- Porting `mpi-quick-plan` into the plugin (SPEC Section 12, item 5).
- JS-backed `lib/` re-implementation (SPEC Section 7.4).
- Marketplace publish (Phase 11 stops at metadata readiness, not actual publish).
- Migration tooling that auto-removes the old `~/.claude/skills/mpi-*` folder for users (the README documents the manual step).

---

## Notes for the executing agent

- The user mentioned they will provide plugin-creation skills (skill-creator etc) when they hand this plan to the build agent. Use those to bootstrap correctly. If your bootstrapping output deviates from SPEC Section 3 file structure, update the spec OR fix the structure before continuing — do not let them drift.
- If, while executing, you find that the SPEC has a contradiction or an outdated assumption (e.g. plugin manifest format changed, skill frontmatter got new required fields), STOP, ask the user, propose a SPEC update, and wait for approval before proceeding.
- Do not commit anything to the user's CubricStudio project from this plugin's build — the plugin lives in `C:\AI\Mpi\Plugins\Mpi-Kanban`. CubricStudio is a separate target for integration testing only (Phase 10).
