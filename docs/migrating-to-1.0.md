# Migrating a project to Mpi-Kanban 1.0

1.0 changes how Mpi-Kanban is installed and closes gaps that projects have been
papering over with local scaffolding. Left in place, most of that scaffolding
now duplicates or fights the plugin.

Two parts, in order:

1. **The install** - remove the pre-1.0 skills pack, install the plugin. Once,
   per machine. See [install.md](install.md).
2. **Each repo** - remove the local workarounds. Run `mpi-project-refresh` in
   the repo and it audits everything below under its **1.0 migration** drift
   category, proposing one finding at a time with its diff. Nothing is removed
   without you seeing what replaces it.

This page is the human-readable version of that audit, for when you would
rather do it by hand or want to know why.

## What changed

| Before | Now |
| --- | --- |
| `npx skills add ... --all -y -g`, 15 skill folders | `/plugin install mpi-kanban@mad-pony-interactive` |
| Skills only. Rules asked; nothing enforced. | Six hooks that block, with a printed reason |
| Four-path `mpi-lib` discovery probe per skill | `${CLAUDE_PLUGIN_ROOT}`, no probe |
| `mpi-handoff` and `mpi-end-session` | One `mpi-end-session` with two exits, resume or done |
| `mpi-nimbalyst-sync`, `state/interop.json` | Removed |
| Markdown board operations (`kanban-ops/`) | Migration only, through `task-board-ops/migrate.md` |
| Version stamp in `skills/mpi-lib/SKILL.md` | `version` in `.claude-plugin/plugin.json` |
| Orchestration when you asked for it | `mpi-continue` dispatches disjoint work without being asked |

## 1. Remove the pre-1.0 pack

Both copies carry the same trigger phrases, so with both installed every
request matches two skills and one of them runs the pre-1.0 contract.
Namespacing does not help - descriptions still load.

[install.md](install.md) leads with the exact removal commands for the 15 pack
names. **Delete nothing else**: a project-scope `mpi-end`, `mpi-release`, or
`mpi-version-bump` skill is yours, not the pack's.

`mpi-init` and `mpi-project-refresh` both block on a survivor and print the
removal commands, so a second machine cannot silently keep the old contract.

## 2. Split your close-out wrapper

Most repos running the pack grew a local close-out wrapper, usually
`.claude/skills/mpi-end/`, to dodge step-0 reads or to add project steps.

Two halves, two destinations:

- **The pack half** - the coordination scope gate and the knowledge-healing
  pass. Both now ship inside `mpi-end-session`. Delete these steps.
- **The project half** - release awareness, recipe lifecycle, propagation
  checks, anything specific to this repo. Move it to
  `.agents/mpi-kanban/close-out.md`. Close-out runs that file at a defined
  slot, so the project keeps its steps without forking the pack skill.

Delete the wrapper once it is empty.

## 3. Remove hooks the plugin now ships

```bash
ls .claude/hooks/
grep -n "hooks" .claude/settings.json
```

`guard-destructive-git.py` (or any local equivalent) is now
`hooks/guard-git.py` in the plugin. Remove the file **and** its
`settings.json` registration, or the guard fires twice.

Keep any hook whose trigger the plugin does not have. A project-specific
rebuild reminder is not a duplicate of anything.

## 4. Delete rules that hooks now enforce

These are the highest-value deletions on this page: a rule in `CLAUDE.md` or
`AGENTS.md` costs context in **every** session, and a hook does not.

| Delete this section | Because |
| --- | --- |
| Sub-agent dispatch protocol | Ownership is written at `todo -> doing` and the dispatcher fires from `mpi-continue` |
| File-claim protocol in a critical-rules snapshot | `guard-claim` blocks the write |
| `next_id` derivation rule | `createTask` claims the ID with an exclusive `mkdir` and retries |
| Board-write pre-authorization | `guard-card` blocks a code edit with no card |
| Destructive-git ban | `guard-git` blocks the command |
| "`mpi-end` must never live in `~/.claude/skills/`" | Obsolete - plugin skills are namespaced |

Remove one section at a time and name the hook that replaces it, so the removal
is auditable later.

## 5. Repoint stale references

```bash
grep -rn "mpi-lib-root\|~/.claude/skills/mpi-\|~/.agents/skills/mpi-\|npx skills" \
     --include="*.md" --include="*.json" .
```

Every hit is now either `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/<path>` or the
plugin install command. The four-path discovery probe and the symlink trap
(`~/.claude/skills/mpi-*` symlinked into `~/.agents/skills/`, which `find` will
not traverse) are both gone.

## 6. Drop local workarounds for fixed bugs

- A hand-rolled `python -c "import uuid; print(uuid.uuid4())"` standing in for
  the shipped `new_uuid.py`. The shipped script has been reachable since
  v0.10.0.
- A card tracking "delete the workaround half once the pack ships the fix".
  Those are now unblocked.
- An orphaned `.agents/mpi-kanban/state/interop.json`. Nothing reads it.
  Delete it.

## 7. Fill in the profile

`.agents/mpi-kanban/project-profile.md` frontmatter needs two fields that
pre-1.0 profiles do not have:

- `pack_version` - what stale-install detection compares against.
- `push_policy` - `auto`, `ask`, or `never`. **An absent value means `auto`**,
  so a profile written before 1.0 silently opts into close-out pushing. Set it
  explicitly.

`mpi-project-refresh` proposes both.

## What not to do

- **Do not backfill `files.json` on old cards.** Ownership is written at the
  next `todo -> doing`, where it is knowable. Backfilling means guessing.
- **Do not sweep.** These are deletions inside a repo holding live work, and
  possibly concurrent sessions. Refresh proposes; you approve.
- **Do not migrate the plugin from inside a consuming repo.** `mpi-project-refresh`
  never edits Mpi-Kanban itself.

## The one thing 1.0 still cannot do

File claims are enforced locally: `guard-claim` blocks a write to a path
another live session claimed, on every edit, whether or not a skill was
invoked. Within one session and the workers it dispatches, that is a real lock.

Across two independently launched Claude Code windows it stays advisory.
Nothing can change that - there is no native cross-session file lock on any
platform. Both windows see the same claim; neither can stop the other's
process. Prefer one session dispatching workers over N windows on one repo.
