# Mpi-Kanban — Plugin Specification

> **Status:** Design spec, not yet built.
> **Build instructions:** See [PLAN.md](./PLAN.md) — phased to-do list. Agent should evaluate the plan against current Claude Code plugin authoring best practices and revise if needed before executing.

---

## 1. Purpose

Bundle the MPI workflow skills (`brainstorm`, `write-plan`, `execute-next`, `end-session`, `handoff`, `brief-rule`) into a single Claude Code plugin that drives a per-project Kanban board (`kanban.md`).

Each skill is responsible for moving a Kanban entry from one column to the next, so the board always reflects the live state of work across the project.

The plugin is shareable (Patreon, Claude Code marketplace) and project-agnostic — all project-specific configuration lives in a per-project config file, never inside the plugin.

---

## 2. External dependency — VS Code extension

The plugin is designed to work alongside this VS Code extension, which renders the Markdown Kanban file as an interactive board:

- **Name:** Markdown Kanban
- **Id:** `holooooo.markdown-kanban`
- **Version:** 1.3.2 or later
- **Marketplace:** https://marketplace.visualstudio.com/items?itemName=holooooo.markdown-kanban

The extension parses a fixed Markdown structure. The plugin's skills MUST emit markdown that conforms to that structure exactly — see Section 4.

The plugin works without the extension (skills still operate on the file), but the user-facing visual board only exists when the extension is installed.

The README, the initial `kanban.md` template, and any "kanban not found" notice from a skill MUST link to the marketplace page so the user can install the extension on first use.

---

## 3. Plugin file structure

The plugin follows the canonical Claude Code plugin layout: manifest under
`.claude-plugin/`, component dir `skills/` at plugin root, custom `lib/` and
`templates/` folders alongside.

```
Mpi-Kanban/                  ← folder name on disk (PascalCase by convention)
├── .claude-plugin/
│   └── plugin.json          ← plugin manifest (name field: "mpi-kanban", kebab-case)
├── README.md                ← user-facing install + usage docs
├── SPEC.md                  ← this file
├── PLAN.md                  ← build to-dos (phased)
├── CLAUDE.md                ← build-agent guidance
├── LICENSE                  ← MIT
├── skills/
│   ├── mpi-brainstorm/SKILL.md
│   ├── mpi-write-plan/SKILL.md
│   ├── mpi-execute-next/SKILL.md
│   ├── mpi-end-session/SKILL.md
│   ├── mpi-handoff/SKILL.md
│   └── mpi-brief-rule/SKILL.md
├── lib/
│   ├── kanban-ops/          ← board operations split by concern
│   │   ├── _schema.md       ← columns, entry shape, locked metadata, regexes
│   │   ├── find.md          ← findKanban, ensureKanban, listEntries, findEntry
│   │   ├── mutate.md        ← createEntry, moveEntry, updateEntry
│   │   ├── steps.md         ← addSteps, markStep, allStepsDone
│   │   └── errors.md        ← error cases table
│   ├── plan-ops/            ← plan file operations split by concern
│   │   ├── _shape.md        ← flat vs phased detection
│   │   ├── read.md          ← readTodos, readPhases
│   │   ├── mutate.md        ← markTodoDone, phaseAllDone
│   │   └── derive.md        ← derive kanban steps from plan
│   └── config-ops.md        ← read .claude/mpi-kanban.local.md (single consumer)
└── templates/
    ├── kanban.md            ← initial 4-column scaffold + extension notice
    └── mpi-kanban.local.md  ← config template (frontmatter + body)
```

### `plugin.json` shape

```json
{
  "name": "mpi-kanban",
  "version": "0.1.0",
  "description": "MPI workflow skills (brainstorm, write-plan, execute-next, end-session, handoff, brief-rule) bundled as a plugin that drives a per-project Kanban board.",
  "author": { "name": "Fabio Goncalves", "email": "fabioargoncalves1981@gmail.com" },
  "license": "MIT",
  "keywords": ["mpi", "kanban", "workflow", "planning"]
}
```

### Skill invocation

No `commands/` wrappers. Skills auto-trigger via frontmatter `description`
keywords (natural language). Direct invocation uses plugin-namespaced slug:
`/mpi-kanban:mpi-end-session`. Removed flat-markdown command files because
each one only said "Invoke the X skill" — Claude Code already does that
automatically when slash command name matches a skill name, so the wrappers
caused redundant file loads per invocation. Per Claude Code plugin docs:
"if a skill and a command share the same name, the skill takes precedence."

### `lib/` is a reference library, not executable code

Skills are pure markdown prose. The `lib/**/*.md` files document the
procedures (parse rules, regex patterns, edit sequences) that skills follow
when mutating board or plan files.

Skills use **deferred pointers**: instead of reading every lib file upfront,
each skill lists the relevant lib paths and reads them inline at the
procedure-call site. This keeps per-invocation context lean — a skill that
only needs `findEntry` reads `lib/kanban-ops/find.md`, not the full
mutation/steps/errors recipes.

A skill that needs to move an entry, for example, reads
`lib/kanban-ops/mutate.md` on demand using the `Read` tool, then performs
the edit using the `Edit`/`Write` tools.

No JS, Node, or Python runtime is required. The author may revise this
decision (Section 7 calls it out as a known trade-off) if reliability proves
insufficient — at which point a JS layer would be added behind the same
`lib/` API surface.

### Path references

Any path the plugin needs to point at inside its own directory (script paths in
hooks, MCP server commands, etc.) MUST use `${CLAUDE_PLUGIN_ROOT}` so the plugin
remains portable across install methods. Plain skills referencing `lib/*.md`
read them using the `Read` tool with a path relative to the plugin root, which
Claude Code resolves automatically.

---

## 4. `kanban.md` contract

### 4.1 Location

`<project-root>/.claude/mpi-kanban/kanban.md`

NOT at the project root. Per-project plugin config lives separately at
`.claude/mpi-kanban.local.md` (see Section 5) — the kanban file is the working
board, the config file is user settings; they're kept apart so the gitignore
convention (`.claude/*.local.md`) covers config without ignoring the board.

### 4.2 Columns (fixed — do not add, rename, or remove)

```markdown
## BACKLOG
## PLANNING
## IMPLEMENTING
## COMPLETED
```

### 4.3 Entry shape

```markdown
### Entry Title

  - due: 2026-05-03
  - tags: [bug]
  - priority: high
  - workload: Easy
  - defaultExpanded: true
  - steps:
      - [ ] step text
      - [x] another step
    ```md
    Free-form body. Plan file ref lives here when present:
    Plan file: docs/plans/YYYY-MM-DD-<slug>.md
    ```
```

### 4.4 Metadata fields (locked — do not invent new fields)

| Field | Type | Required | Values |
|---|---|---|---|
| `due` | date | No | `YYYY-MM-DD` |
| `tags` | list | Yes | e.g. `[bug]`, `[feature]`, `[Idea]`, `[PLAN]`, `[refactor]` |
| `priority` | enum | Yes | `high` \| `medium` \| `low` |
| `workload` | enum | No | `Easy` \| `Medium` \| `Hard` |
| `defaultExpanded` | bool | Yes | `true` \| `false` |
| `steps` | nested checklist | Only on IMPLEMENTING entries | `- [ ] text` / `- [x] text` |

### 4.5 Body (fenced ` ```md ` block)

- Free-form markdown.
- For PLANNING and IMPLEMENTING entries, the body MUST contain a line matching `Plan file: <path>` (case-insensitive on `file`).
- Skills locate the plan via regex `/^Plan [Ff]ile:\s*(.+)$/m` in the fence.

### 4.6 Mutation rules

1. **Never delete an entry.** Skills only move entries between columns.
2. **Move = cut whole block (H3 + bullets + fence) + paste at top of target column.**
3. **Title is the entry's identity.** Duplicate titles within the same `kanban.md` are an error.
4. **Empty column = the H2 header followed by a blank line and the next H2.**
5. **Skills MUST NOT add metadata fields outside the locked schema in 4.4** — the VS Code extension breaks on unknown fields.

### 4.7 Bootstrap (file missing)

When any skill is invoked and `kanban.md` does not exist:

1. Auto-create `.claude/mpi-kanban/kanban.md` from `templates/kanban.md`.
2. Emit a one-time setup notice in chat:
   - Clickable link to the new file: `[kanban.md](.claude/mpi-kanban/kanban.md)`
   - Marketplace link to the VS Code extension `holooooo.markdown-kanban`
   - One-line note: "Install the extension to see this file as an interactive board."

Auto-creation does NOT trigger if the user invoked `mpi-brief-rule` (board-independent skill).

---

## 5. Per-project config

### 5.1 Location

`<project-root>/.claude/mpi-kanban.local.md`

This follows the standard Claude Code "plugin settings" idiom: a `.local.md`
file in `.claude/` with YAML frontmatter for structured fields and a markdown
body for free-form context. The `.local.md` suffix makes it gitignorable via
the conventional `.claude/*.local.md` pattern.

### 5.2 Schema

```markdown
---
rules_dir: .claude/rules
rules:
  - name: components
    file: components.md
  - name: events
    file: events.md
critical_snapshot_file: CLAUDE.md
critical_snapshot_anchor: critical-rules-snapshot
---

# Mpi-Kanban project notes

(Optional free-form body. Currently unused by the plugin — reserved for
future skills that may want a project-level prose note. Safe to leave empty.)
```

| Frontmatter field | Purpose |
|---|---|
| `rules_dir` | Folder where rule files live, relative to project root. |
| `rules` | List of rules `mpi-brief-rule` can extract briefings from. `name` is the user-facing key (`/mpi-kanban:mpi-brief-rule components`); `file` resolves to `<rules_dir>/<file>`. |
| `critical_snapshot_file` | File holding the universal "Critical Rules Snapshot" that ALL sub-agents must receive. |
| `critical_snapshot_anchor` | Heading id within that file. |

### 5.3 Bootstrap (config missing)

When `mpi-brief-rule` is invoked and config does not exist:

1. Do NOT auto-create — config is project-specific and the user must opt in to a rule list.
2. Emit a setup notice with:
   - Clickable link to where the config should go (`.claude/mpi-kanban.local.md`).
   - Sample contents (copy from `templates/mpi-kanban.local.md`).
   - One-line note: "Add the rules you want sub-agents to receive briefings for."
   - One-line note: ".local.md is gitignored by convention — add `.claude/*.local.md` to your `.gitignore` if not already present."

---

## 6. Skills

All six skills follow the existing MPI skill conventions, with one universal rule:

- **All references to `kanban.md` in chat** must be a clickable markdown link: `[kanban.md](.claude/mpi-kanban/kanban.md)`.

### 6.0 `mpi-init`

- Trigger words: "set up the kanban", "set up kanban based on this file",
  "initialize kanban", "import backlog", "convert this to kanban", or any
  hand-off of a freeform to-do / backlog / ideas markdown file with a request
  to populate the board.
- Two modes:
  1. **Empty board** — no source file given: call `ensureKanban()` to create
     the board from `templates/kanban.md` and emit the marketplace notice.
     Stop.
  2. **Import** — source file given: parse it per the skill's "Parsing rules"
     (sections → tags, `[x]` → COMPLETED, `[ ]` / unmarked → BACKLOG, infer
     priority from keywords, default `medium`). Show the user the planned
     entry list, wait for approval, then write via `createEntry`.
- Hard gate: never write entries to `kanban.md` before the user approves the
  parsed list. The empty-board mode only writes the template, which is safe.
- This is the on-ramp skill — it exists so a user can bootstrap a project
  without forcing the agent to derive entry shape from
  `lib/kanban-ops/_schema.md`.

### 6.1 `mpi-brainstorm`

- Trigger words: same as today.
- After the user approves the design, BEFORE asking "Want a plan?":
  1. Create a new BACKLOG entry on `kanban.md`.
  2. Title: 2-4 word slug from the idea.
  3. Tags: inferred (`[bug]`, `[feature]`, `[Idea]`, `[refactor]`).
  4. Priority: ask the user (default `medium`).
  5. `defaultExpanded: true`.
  6. Body fence: 2-3 line idea summary.
  7. NO steps. NO plan file ref.
- Then ask "Do you want to write a plan for this?". If yes → invoke `mpi-write-plan` with the entry title.

### 6.2 `mpi-write-plan`

- Trigger words: same as today.
- If a BACKLOG entry exists for this work (passed in by `mpi-brainstorm` or matched by user-provided title):
  1. Move BACKLOG → PLANNING.
  2. Replace tags with `[PLAN]`.
  3. Body fence becomes `Plan file: docs/plans/YYYY-MM-DD-<slug>.md`.
- If no entry exists (user invoked write-plan directly):
  1. Create a new PLANNING entry directly with `[PLAN]` tag.
- Plan file is written to `docs/plans/`. Plan to-dos are NOT mirrored as kanban steps yet — that happens at IMPLEMENTING transition.

### 6.3 `mpi-execute-next`

- Trigger words: same as today.
- First call against a plan:
  1. Locate the kanban entry (match by `Plan file:` reference in body).
  2. Move PLANNING → IMPLEMENTING.
  3. Add `- steps:` to the entry. See Section 6.3.1 for derivation rules.
- Per to-do completion (Option 1 / "verified"):
  1. Mark plan to-do `[x]`.
  2. Flip the matching kanban step `[x]`. See Section 6.3.1 for matching rules.
- Gate behavior (brief gate before code, post-impl gate after code) unchanged.

#### 6.3.1 Step derivation — phases vs flat to-dos

When transitioning PLANNING → IMPLEMENTING, the skill reads the plan file and decides:

- **Phased plan** — if the plan contains any heading matching `^## Phase \d+` (or `^## \w+ Phase`):
  - Steps = phase titles, stripped of `Phase N:` prefix and shortened to 3-6 words.
  - A step flips to `[x]` when ALL to-dos under that phase are `[x]` in the plan file.
- **Flat plan** — no phase headings:
  - Steps = each plan to-do, summarized to 3-6 words.
  - A step flips to `[x]` when its corresponding plan to-do is `[x]`.

Mixed plans (some phases + stray flat to-dos at the end): treated as phased. Stray to-dos belong to the last phase.

### 6.4 `mpi-end-session` (rewritten as a proper skill)

Currently shipped as `mpi-end-session.md.md` (broken double extension) using the old `<objective>` slash-command format.

Replace with a proper skill:

```yaml
---
name: mpi-end-session
description: Close session — sync rules/docs, commit touched files, move kanban entry to COMPLETED if all steps done. Use when user says "end session", "wrap up", "commit and close", "/mpi-kanban:mpi-end-session".
---
```

Process:

1. `git status` (small) and `git diff --stat HEAD` (file list, NOT full diff — protects context on big sessions).
2. List changed files.
3. Identify rule/doc impact. Per project CLAUDE.md cardinal rule, ASK the user before modifying any architectural rule file.
4. Memory pass per `~/.claude/CLAUDE.md` (write learnings, update MEMORY.md index).
5. Stage files BY NAME (never `-A`) and commit with a descriptive message.
6. Read kanban. Locate the active IMPLEMENTING entry by matching its `Plan file:` against the most recently touched plan file.
7. Check `allStepsDone()` (defined in `lib/kanban-ops/steps.md`):
   - True → move IMPLEMENTING → COMPLETED.
   - False → leave entry in IMPLEMENTING; append "session ended mid-implementation" to the commit message body.
8. Output a clickable kanban link so the user can verify visually.

### 6.5 `mpi-handoff`

- Same flow as today.
- Add a `kanban_entry` field to the handoff JSON containing the title of the active IMPLEMENTING entry (entry whose `Plan file:` matches the active plan).

### 6.6 `mpi-brief-rule`

- Same purpose: extract `## Sub-Agent Briefing` from a named rule file and return verbatim.
- Generalize: read `.claude/mpi-kanban.local.md` (frontmatter) for the rule list, instead of hardcoding CubricStudio's rules.
- If config missing → emit setup notice (Section 5.3), do not error out beyond that.
- If named rule not in config → list available rule names from config.
- If named rule has no `## Sub-Agent Briefing` section → return the critical snapshot (resolved from `critical_snapshot_file` + `critical_snapshot_anchor`) as a fallback.

---

## 7. Lib reference docs

`lib/kanban-ops/`, `lib/plan-ops/`, and `lib/config-ops.md` are markdown
reference documents. Skills load them on demand with `Read` (deferred
pointers — read the specific file at the procedure-call site, not upfront)
and follow the procedures inside.

### 7.1 `lib/kanban-ops/`

Split by concern so a skill reads only what it needs:

- `_schema.md` — file location, columns, entry shape, locked metadata
  fields, parser regexes.
- `find.md` — `findKanban`, `ensureKanban`, `kanbanLink`, `listEntries`,
  `findEntry`.
- `mutate.md` — `createEntry`, `moveEntry`, `updateEntry` (with worked
  example).
- `steps.md` — `addSteps`, `markStep`, `allStepsDone`.
- `errors.md` — error cases (duplicate title, malformed entry, missing
  column, unknown metadata field, missing `Plan file:` ref).

### 7.2 `lib/plan-ops/`

Split by concern:

- `_shape.md` — flat vs phased plan structure, phase detection regex,
  decision tree.
- `read.md` — `readTodos`, `readPhases`.
- `mutate.md` — `markTodoDone`, `phaseAllDone`.
- `derive.md` — derive kanban steps from plan (with worked examples for
  both shapes).

### 7.3 `lib/config-ops.md`

Single file (only one consumer skill, `mpi-brief-rule`). Documents:

- Config file location and schema (Section 5) — `.claude/mpi-kanban.local.md`
  with YAML frontmatter.
- Frontmatter parsing pattern (extract everything between `---` markers;
  read individual fields).
- `loadConfig`, `getRuleList`, `resolveRulePath`, `loadCriticalSnapshot`.
- Bootstrap snippet for missing config (the markdown the skill emits).

### 7.4 Trade-off — markdown lib vs JS lib

This spec ships markdown reference docs only. Pros: no runtime dependency, cross-platform, easy to read and audit. Cons: every mutation is LLM-driven, so reliability depends on prompt quality.

If reliability proves insufficient after some real use, the same `lib/` API surface can be re-implemented as JS files invoked by skills via Bash, without changing the skill prose much. PLAN.md notes this as a deferred decision.

---

## 8. Extensibility contract

The plugin is designed to grow. Future skills MAY be added that:

- Operate on the same `kanban.md` board, using shared `lib/kanban-ops/*.md`.
- Read the same `.claude/mpi-kanban.local.md` for project context.
- Hook lifecycle phases not yet covered (e.g. PR review skill that reads COMPLETED).
- Introduce new tags or new step semantics.

Future skills MUST NOT:

- Add new columns. The 4 columns are locked by the VS Code extension contract.
- Add new metadata fields beyond the schema in Section 4.4.
- Bypass `lib/` and inline kanban parsing logic.

When adding a new skill, update `lib/*.md` first if a new shared procedure is needed; only then update the skill prose.

---

## 9. Migration from existing user skills

The existing `~/.claude/skills/mpi-*` skills (in CubricStudio user scope) are the source material for this plugin. Migration steps:

1. Fix `mpi-end-session.md.md` (double extension, old `<objective>` format) — rewrite as proper skill per Section 6.4.
2. Generalize `mpi-brief-rule` per Section 6.6 — replace hardcoded CubricStudio rule list with config-driven lookup.
3. Add the kanban-move logic to each skill (Section 6).
4. Add `lib/*.md` reference docs and replace inlined procedures in skills with references to those docs.
5. Drop `mpi-quick-plan` from the plugin scope (stays as a separate user skill if the user wants it).

After install, the user's old `~/.claude/skills/mpi-*` folder should be removed (or the skills will conflict with the plugin's bundled versions).

---

## 10. Local development + install

Plugins can be installed from a local path during development.

1. Clone / open `C:\AI\Mpi\Plugins\Mpi-Kanban`.
2. Install locally (exact mechanism per Claude Code plugin docs at build time — see PLAN.md, the build agent should verify the current install command).
3. Reload skills (`/reload-plugins` or restart Claude Code).
4. Verify all six skills appear in the skill list.
5. Test in CubricStudio (or any project) — board ops should work without errors.

---

## 11. Distribution

Target audiences:

- **Patreon subscribers** — direct zip / git URL.
- **Claude Code marketplace** — when the plugin is stable.

Both audiences need the README to:

- Explain the workflow (brainstorm → write-plan → execute-next → end-session).
- Link to the VS Code extension marketplace page (Section 2).
- Show the per-project setup steps (`.claude/mpi-kanban.local.md` config, optional kanban.md auto-creation, gitignore guidance for `.claude/*.local.md`).
- Show install instructions for both local-zip and marketplace install paths.

The README is user-facing. SPEC.md and PLAN.md are dev-facing and may be excluded from the published bundle (or included in a `dev/` subfolder) — the build agent decides.

---

## 12. Open trade-offs the build agent may revisit

Listed here so the build agent in a fresh session can challenge them:

1. **Markdown-only lib (Section 7.4)** — reconsider if a JS layer is warranted from day one. Decision for v0.1.0: stay markdown-only, revisit after real use.
2. **`mpi-brainstorm` creates the BACKLOG entry, not the user** — if this proves intrusive, gate it behind a confirmation prompt.
3. **Kanban location `.claude/mpi-kanban/` vs `.claude/`** — confirm the VS Code extension picks up files inside subfolders. (It should — extension watches workspace `.md`.) If not, fall back to `.claude/kanban.md`.
4. **`mpi-quick-plan`** — currently excluded. If users miss it, port it later as a thin wrapper.

---

## 13. Acceptance criteria

The plugin is "done" when:

- `Mpi-Kanban` installs locally and registers all six skills.
- A fresh project with no `.claude/mpi-kanban/` folder is bootstrapped on first skill invocation (kanban auto-create + extension link notice).
- A full workflow run (`brainstorm` → `write-plan` → `execute-next` × N → `end-session`) moves a single entry through all four columns correctly.
- Phased plans produce phase-titled steps; flat plans produce summarized to-do steps.
- `mpi-brief-rule` works in CubricStudio with a config-driven rule list (parity with current hardcoded behavior).
- `mpi-handoff` records the active IMPLEMENTING entry in its JSON output.
- README explains install + usage and links to the VS Code extension.
