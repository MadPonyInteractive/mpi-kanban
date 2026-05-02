# Mpi-Kanban — Build Plan

> **Source spec:** [SPEC.md](./SPEC.md). Read it in full first — it is the source of truth.
>
> This plan is a flat to-do list, executed top to bottom in one pass. The plugin is
> markdown-only (no compile, no runtime), so per-step verification is unnecessary.
> One integration smoke test at the end covers all of SPEC §13 acceptance criteria.
>
> **Stop conditions** — if any of these come up, halt and ask the user:
> - SPEC and the Plugin Structure / Plugin Settings reference skills disagree on layout.
> - SPEC.md has an internal contradiction.
> - A migrated skill has Nimbalyst behavior that does not have a clean replacement in
>   the kanban / lib model.
>
> Otherwise: do not modify SPEC.md without asking; commit when done (one commit, or two
> if the work splits naturally — your call).

---

## To-do list

### Scaffold

- [ ] Create `.claude-plugin/plugin.json` (manifest under `.claude-plugin/`, NOT plugin root) with: `name: "mpi-kanban"` (kebab-case), `version: "0.1.0"`, description from SPEC §1, author `{ name: "Fabio Goncalves", email: "fabioargoncalves1981@gmail.com" }`, `license: "MIT"`, `keywords: ["mpi", "kanban", "workflow", "planning"]`.
- [ ] Create `LICENSE` (MIT, copyright Fabio Goncalves, current year).
- [ ] Create empty folders: `commands/`, `skills/`, `lib/`, `templates/`.

### Templates

- [ ] Write `templates/kanban.md`: 4 H2 columns in order (BACKLOG, PLANNING, IMPLEMENTING, COMPLETED), empty between columns, HTML comment at top with the marketplace link `https://marketplace.visualstudio.com/items?itemName=holooooo.markdown-kanban`.
- [ ] Write `templates/mpi-kanban.local.md` per SPEC §5.2: YAML frontmatter with `rules_dir`, empty `rules: []`, placeholders for `critical_snapshot_file` and `critical_snapshot_anchor`. Use `#` comments inside the frontmatter to document each field. Body includes the gitignore reminder.

### Lib reference docs

- [ ] Write `lib/kanban-ops.md`: parser regexes (column heading, entry heading, metadata bullet, body fence); procedures `findKanban`, `ensureKanban`, `listEntries`, `findEntry`, `moveEntry`, `createEntry`, `updateEntry`, `addSteps`, `markStep`, `allStepsDone`, `kanbanLink`; exact `Edit` tool sequence for each mutation; error cases (duplicate title, missing column, malformed entry, unknown metadata field); a worked before/after example for `moveEntry`. Self-contained — a skill author should not need SPEC.md to implement a mutation.
- [ ] Write `lib/plan-ops.md`: phase detection regex per SPEC §6.3.1; procedures `readTodos`, `readPhases`, `markTodoDone`, `phaseAllDone`; decision tree for "is this plan phased?"; worked example for both phased and flat plans.
- [ ] Write `lib/config-ops.md`: config location `.claude/mpi-kanban.local.md`; YAML frontmatter parsing pattern (`sed`/`awk` extraction between `---` markers, reading scalars and the `rules:` list); procedures `loadConfig`, `getRuleList`, `resolveRulePath`, `loadCriticalSnapshot`; bootstrap snippet text the skill emits when config is missing (with link to template + gitignore reminder).

### Skill migrations

> Source skills live at `C:\Users\Fabio\.claude\skills\mpi-*` — copy from there.
> Universal stripping (every skill): remove all `mcp__nimbalyst-*` calls; remove
> `<!-- trackers ... -->` block logic; remove session-meta calls. Each migrated
> skill gets a thin `commands/mpi-<skill>.md` slash-command wrapper that invokes
> the skill explicitly.

#### `mpi-end-session` (rewrite — this one is structurally broken)

- [ ] Read source `~/.claude/skills/mpi-end-session/SKILL.md.md` (note the double extension).
- [ ] Create `skills/mpi-end-session/SKILL.md` (single extension) with proper frontmatter (`name`, `description` only) per SPEC §6.4.
- [ ] Translate the existing `<objective>` / `<context>` / `<process>` blocks into prose-style instructions.
- [ ] Replace `git diff HEAD` (full diff) with `git diff --stat HEAD` (file list only).
- [ ] Strip Nimbalyst session-meta call and `mcp__nimbalyst-mcp__get_session_edited_files`.
- [ ] Add kanban close-out per SPEC §6.4 step 6-7: locate active IMPLEMENTING entry by matching `Plan file:` against the most recently touched plan; use `lib/kanban-ops.md` `allStepsDone`; if true → move IMPLEMENTING → COMPLETED; if false → leave + append "session ended mid-implementation" to commit body.
- [ ] Final report includes a clickable kanban link.
- [ ] Keep the "ask before changing architectural rule files" cardinal-rule check intact.
- [ ] Create `commands/mpi-end-session.md`.

#### `mpi-brief-rule`

- [ ] Copy source SKILL.md, strip the hardcoded "Supported Rules" list (CubricStudio-specific).
- [ ] Replace with a flow that reads `.claude/mpi-kanban.local.md` (frontmatter) via `lib/config-ops.md`.
- [ ] Config missing → emit setup notice per SPEC §5.3, stop.
- [ ] Named rule not in config → list available rule names, stop.
- [ ] Rule has no `## Sub-Agent Briefing` section → fall back to critical snapshot per SPEC §6.6.
- [ ] Update frontmatter description to match new behavior (still triggers on `/mpi-brief-rule <name>`).
- [ ] Create `commands/mpi-brief-rule.md`.

#### `mpi-handoff`

- [ ] Copy source SKILL.md, strip all `mcp__nimbalyst-*` calls and references.
- [ ] Add step to read `kanban.md` and locate active IMPLEMENTING entry (entry whose `Plan file:` matches the active plan).
- [ ] Add `kanban_entry: "<title>"` field to the JSON schema; `null` if no IMPLEMENTING entry matches.
- [ ] Update the resume prompt block to mention the kanban entry by title.
- [ ] Create `commands/mpi-handoff.md`.

#### `mpi-brainstorm`

- [ ] Copy source SKILL.md, strip the `mcp__nimbalyst-session-naming__update_session_meta` call.
- [ ] After "design approved" gate and BEFORE the "Want a plan?" prompt, add BACKLOG entry creation per SPEC §6.1: auto-create `kanban.md` if missing per §4.7; use `lib/kanban-ops.md` `createEntry`; ask the user once for `priority` (default `medium`); infer tags from idea content (`[bug] | [feature] | [Idea] | [refactor]`).
- [ ] In the "yes, write a plan" branch, invoke `mpi-write-plan` and pass the BACKLOG entry title forward via prompt context (skills don't pass arguments natively).
- [ ] Create `commands/mpi-brainstorm.md`.

#### `mpi-write-plan`

- [ ] Copy source SKILL.md.
- [ ] Remove `mcp__nimbalyst-session-naming__update_session_meta` call (current step 2).
- [ ] Remove steps 8 and 9 (Nimbalyst tracker creation + tracker metadata block).
- [ ] Update step 7 (write plan file): no `<!-- trackers -->` block.
- [ ] After plan file is written, add a kanban update step:
  - If a BACKLOG entry matches (passed in by brainstorm or by user-provided title) → move BACKLOG → PLANNING, replace tags with `[PLAN]`, set body fence to `Plan file: <plan-path>`.
  - If no entry matches → create new PLANNING entry directly with `[PLAN]` tag.
  - Use `lib/kanban-ops.md` procedures.
- [ ] Drop `/mpi-quick-plan` from "Related commands" (out of plugin scope).
- [ ] Keep the "self-audit" step (current step 6); drop the Nimbalyst guidance from it.
- [ ] Create `commands/mpi-write-plan.md`.

#### `mpi-execute-next`

- [ ] Copy source SKILL.md, strip all Nimbalyst calls (session-meta + tracker-status updates throughout) and the tracker-id metadata-block lookup logic in "Session setup".
- [ ] On first invocation against a plan: locate kanban entry via `lib/kanban-ops.md` `findEntry` matching the plan's `Plan file:`; move PLANNING → IMPLEMENTING; read plan file via `lib/plan-ops.md`; determine phased vs flat per SPEC §6.3.1; build steps array (3-6 word summaries OR phase titles) and add via `addSteps`.
- [ ] On Option 1 ("verified") per to-do: after marking plan to-do `[x]`, look up matching kanban step — phased plan flips when all to-dos in the current phase are `[x]`; flat plan flips the kanban step at the matching index.
- [ ] Keep both gates (brief gate before code, post-impl gate after code) intact — do not weaken these.
- [ ] Drop `/mpi-component-audit` from "Related commands" if not in plugin scope.
- [ ] Copy `~/.claude/skills/mpi-execute-next/brief-template.md` into `skills/mpi-execute-next/brief-template.md` and update the reference path inside the skill.
- [ ] Create `commands/mpi-execute-next.md`.

### Documentation

- [ ] Write `README.md` per SPEC §11: install steps, workflow overview (brainstorm → write-plan → execute-next → end-session), VS Code extension marketplace link, per-project setup (`.claude/mpi-kanban.local.md` config + auto-creation of `kanban.md`), gitignore guidance for `.claude/*.local.md`. Troubleshooting section: kanban not auto-creating, extension not rendering, bootstrap notice loops. Keep under ~150 lines.

### Final smoke test (one pass, end-to-end)

- [ ] Install plugin locally per current Claude Code plugin docs.
- [ ] `/plugin list` (or current equivalent) — `mpi-kanban` appears with description.
- [ ] All six skills + six slash commands are registered.
- [ ] In a scratch project (NOT CubricStudio yet — that's a separate user step):
  - [ ] Invoke `/mpi-brainstorm` with a tiny idea → BACKLOG entry created with correct shape.
  - [ ] Continue to `/mpi-write-plan` → entry moves to PLANNING with `[PLAN]` tag and `Plan file:` body.
  - [ ] Run `/mpi-execute-next` once → entry moves to IMPLEMENTING and gains steps.
  - [ ] Mark all to-dos done → kanban steps flip correctly.
  - [ ] `/mpi-end-session` → entry moves to COMPLETED + clean commit.
  - [ ] No `mcp__nimbalyst-*` errors anywhere.
  - [ ] No `<!-- trackers -->` blocks in the plan file.
  - [ ] Kanban file was auto-created on first call.
- [ ] `/mpi-brief-rule <name>` against a config with one rule that has a `## Sub-Agent Briefing` section → returns the briefing verbatim.
- [ ] `/mpi-handoff` mid-flight → JSON contains `kanban_entry`.

If all of the above pass, the plugin meets SPEC §13 acceptance criteria. Commit and report.

---

## Out of scope

- Porting `mpi-quick-plan` into the plugin (SPEC §12, item 4).
- JS-backed `lib/` re-implementation (SPEC §7.4).
- Marketplace publish.
- CubricStudio integration test (separate manual step the user runs after this plugin builds).
- Auto-removing the user's old `~/.claude/skills/mpi-*` folder — README documents the manual step.

---

## Notes for the executing agent

- Source skills are at `C:\Users\Fabio\.claude\skills\mpi-*`. The user has backed them up. Do not delete them; they will be removed manually before CubricStudio integration testing.
- Reference skills `.agents/skills/plugin-structure/SKILL.md` and `.agents/skills/plugin-settings/SKILL.md` are gitignored but present on disk — read them directly.
- Plugin lives at `C:\AI\Mpi\Plugins\Mpi-Kanban`. Do NOT commit anything to other projects from this build.
