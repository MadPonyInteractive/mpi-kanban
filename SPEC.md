# Mpi-Kanban Specification

> Status: active development. Breaking workflow and packaging changes are
> allowed before the next release.

## 1. Purpose

Mpi-Kanban is an all-or-nothing Agent Skills pack for planning, kanban
coordination, handoffs, cleanup, and multi-agent file ownership.

The workflow is:

```text
brainstorm -> create-plan/create-large-plan -> continue -> handoff/continue -> end-session -> cleanup
```

The human board lives at `.agents/mpi-kanban/kanban.md`. Machine-readable
coordination state lives separately under `.agents/mpi-kanban/state/`.

## 2. Distribution

The only supported install and update channel is skills.sh / `npx skills`:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

The `--all` flag is required. Partial installs are unsupported because the
workflow skills depend on the sibling support skill `mpi-lib`.

Claude Code plugin packaging, Codex plugin packaging, Codex marketplace bundles,
Kilo-specific generated skills, and live-copy plugin cache bridges are removed.
Old users must reinstall through the npx command above.

## 3. Skill Set

- `mpi-init` - bootstrap/import a board.
- `mpi-project-setup` - establish project mode and durable project knowledge.
- `mpi-project-mode` - review, reaffirm, or change project mode.
- `mpi-project-refresh` - audit drift between project knowledge and repo
  reality.
- `mpi-brainstorm` - explore an idea and capture a BACKLOG entry.
- `mpi-create-plan` - create a compact/default plan.
- `mpi-create-large-plan` - create an adaptive, investigation-backed large
  plan.
- `mpi-continue` - resume/implement from the active plan, handoff, kanban
  entry, and current repo state.
- `mpi-execute-parallel` - execute explicit safe `## Parallel Batch` sections.
- `mpi-nimbalyst-sync` - coordinate Nimbalyst detection, source-of-truth mode,
  dry-run import/export boundaries, and tracker mappings.
- `mpi-handoff` - preserve current state in canonical JSON.
- `mpi-end-session` - sync docs/rules/memory, commit when appropriate, and
  close the active kanban entry when complete.
- `mpi-cleanup` - propose conservative cleanup for stale workflow artifacts.
- `mpi-archive` - archive kanban entries out of the active board.
- `mpi-brief-rule` - return configured rule briefings or rule bundles.
- `mpi-lib` - shared reference library support skill; not a user workflow.

`mpi-write-plan` and `mpi-execute-next` are removed.

## 4. Shared Reference Model

Shared reference docs live under `skills/mpi-lib/`.

Consuming skills locate `mpi-lib` at first use by checking:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

After resolving the first existing path, the agent caches it as
`<mpi-lib-root>` for the session and reads individual files on demand.

If no candidate exists, the skill must stop and tell the user to reinstall:

```text
npx skills add MadPonyInteractive/mpi-kanban --all -y -g
```

Workflow skills must not rely on `${CLAUDE_PLUGIN_ROOT}`, Claude `!` injection,
Codex plugin roots, or any runtime-specific plugin packaging feature.

## 5. Kanban Contract

The board lives at:

```text
<project-root>/.agents/mpi-kanban/kanban.md
```

Legacy projects may still contain:

```text
<project-root>/.claude/mpi-kanban/kanban.md
```

`mpi-project-setup` is responsible for proposing migration of legacy board
files from `.claude/mpi-kanban/` to `.agents/mpi-kanban/`. It must list the
files to move, preserve unknown files, and ask before overwriting an existing
target or deleting the legacy directory.

Fixed columns:

```markdown
## BACKLOG
## PLANNING
## IMPLEMENTING
## VALIDATING
## COMPLETED
```

Entry metadata fields are locked for VS Code extension compatibility:

- `due`
- `tags`
- `priority`
- `workload`
- `defaultExpanded`
- `steps`

For PLANNING, IMPLEMENTING, and VALIDATING entries, the body fence must contain:

```text
Plan file: docs/plans/YYYY-MM-DD-<slug>.md
```

Skills must not add columns outside this locked contract or add metadata
fields. Legacy four-column boards that omit `VALIDATING` may be read, but any
workflow that needs to mutate lifecycle state must ask before inserting
`## VALIDATING` between `## IMPLEMENTING` and `## COMPLETED`.

## 6. Coordination State

Canonical machine-readable coordination state lives at:

```text
<project-root>/.agents/mpi-kanban/state/
```

The state root contains:

- `index.json`
- `sessions/<uuid>.json`
- `tasks/<uuid>.json`
- `files/<uuid>.json`
- `handoffs/<uuid>.json`
- `archive/`

Agents read `state/index.json` first when it exists. File claims with status
`claimed` are active write locks. Completed or released file ownership does not
grant commit ownership; the closing or integrating session must reread current
state and Git state before committing.

Lifecycle references live in `skills/mpi-lib/coordination-ops/`.

### 6.1 Interop Mode State

Durable source-of-truth mode state lives at:

```text
<project-root>/.agents/mpi-kanban/state/interop.json
```

When the file is absent, skills must treat the project as `file` mode.

Supported `source_of_truth` values:

- `file` - default portable mode. MPI workflow skills mutate
  `.agents/mpi-kanban/kanban.md` and coordination state directly.
- `nimbalyst` - Nimbalyst sessions and trackers are canonical. MPI workflow
  skills must not live-update both Nimbalyst and `.agents/mpi-kanban/kanban.md`
  during normal work. Markdown import/export happens only through explicit sync
  boundaries.

The interop state records last environment detection, last sync/export times,
and ID mappings between MPI entries and Nimbalyst trackers. Skills must not add
Nimbalyst IDs or sync metadata to kanban entry fields.

## 7. Project Knowledge

Durable project knowledge lives outside coordination state:

```text
<project-root>/.agents/mpi-kanban/project-profile.md
<project-root>/.agents/mpi-kanban/project-knowledge-index.md
```

The profile records project mode, summary, architecture, conventions, important
commands, files to read first, setup/refresh dates, and open gaps. The index
maps task topics to specific docs/rules/memory pointers.

Mode contracts and schemas live under `skills/mpi-lib/project-intent/` and
`skills/mpi-lib/project-knowledge/`.

`mpi-project-setup`, `mpi-project-mode`, and `mpi-project-refresh` own this
layer. Other skills consume it without duplicating content.

## 8. Plan Model

Compact plans are created by `mpi-create-plan` and use one coherent
implementation flow with final verification.

Large plans are created by `mpi-create-large-plan` and may include:

- `## Current State`
- `## Phase N: ...`
- `## Parallel Batch: ...`
- `## Completed`
- `## Remaining Work`
- `## Plan Drift`
- `## Verification`
- `## Preservation Notes`

Parallelism is the default for eligible large-plan work. Parallel batches still
require disjoint `Ownership:`, per-task `**Verify:**`, no intra-batch
dependencies, and no active write claim conflict.

Plans are living documents. `mpi-continue` may update current state, drift,
completed work, and remaining work before implementation when reality no longer
matches the written plan.

## 9. Continue Model

`mpi-continue` is the normal implementation skill. It:

1. Finds active work from a handoff, plan path, IMPLEMENTING entry, VALIDATING
   entry, or PLANNING entry.
2. Reads project profile/index when present.
3. Reads coordination state when present.
4. Locates the kanban entry by `Plan file:`.
5. Moves PLANNING to IMPLEMENTING when needed.
6. Adds stable kanban steps.
7. Inspects current repo state.
8. Updates/annotates plan drift when needed.
9. Presents a continue brief before implementation.
10. Presents a post-implementation verification gate before marking work done.
11. Moves fully implemented work to VALIDATING instead of COMPLETED.

`mpi-continue` does not commit or push.

## 10. Parallel Execution

`mpi-execute-parallel` only runs explicit `## Parallel Batch` sections.
Each batch task must include:

- unchecked task text;
- `Ownership:` with files/modules;
- disjoint ownership from every other task;
- `Briefings:` rule names or bundle names when relevant;
- `**Verify:**`.

The main agent spawns workers, integrates results, verifies the batch, and
updates plan/kanban state. Workers must not edit plan, kanban, handoff, rules,
or memory files unless explicitly owned.

## 11. Handoff

`mpi-handoff` writes:

```text
.agents/mpi-kanban/state/handoffs/<uuid>.json
```

`docs/handoffs/` is legacy compatibility during migration. New canonical
handoffs live in `.agents/mpi-kanban/state/handoffs/`.

The final chat output must include a pasteable resume block pointing the next
session to `mpi-continue`.

## 12. Brief Rule Bundles

Project config lives at:

```text
<project-root>/.agents/mpi-kanban.local.md
```

It may define `rules:` and optional `bundles:`. `mpi-brief-rule <name>` returns
either one rule's `## Sub-Agent Briefing` or all rule briefings in a named
bundle.

The pack does not hardcode project rules.

## 13. Cleanup

`mpi-cleanup` classifies workflow artifacts as active, completed, orphaned,
superseded, stale, or uncertain. It proposes cleanup and waits for approval.

It never deletes active files and never deletes archives by default.

## 14. Cross-Agent Skill Distribution

Mpi-Kanban is a 16-skill pack distributed through skills.sh. The install
command always uses `--all`; missing `mpi-lib` is a user installation error.

The pack intentionally accepts a non-standard shared support skill to avoid
duplicating the reference library into every workflow skill. This keeps context
use low because `mpi-lib` sibling files are loaded only when a workflow skill
instructs the agent to read them.

Validation must check:

- every `skills/*/SKILL.md` has valid frontmatter;
- every skill name matches its folder;
- skill names/descriptions satisfy Agent Skills limits;
- `skills/mpi-lib/SKILL.md` exists;
- consuming skills include the `mpi-lib` discovery block;
- interop mode state and references are present;
- no `${CLAUDE_PLUGIN_ROOT}` references remain;
- `skills.sh.json` lists real skills.

## 15. Acceptance Criteria

- `npx skills add MadPonyInteractive/mpi-kanban --all -y -g` installs the pack.
- `npx skills add MadPonyInteractive/mpi-kanban -l` lists all 16 skills.
- Claude, Codex, and Kilo can invoke one workflow skill after npx install.
- Workflow skills resolve `mpi-lib` and read shared references successfully.
- Kanban schema uses the five locked columns in order:
  BACKLOG, PLANNING, IMPLEMENTING, VALIDATING, COMPLETED.
- Coordination state remains under `.agents/mpi-kanban/state/`.
- Project profile/index remain under `.agents/mpi-kanban/`.
- `mpi-project-setup` can migrate legacy `.claude/mpi-kanban/` board files to
  `.agents/mpi-kanban/` with explicit approval and no silent overwrites.
- Validator passes.


