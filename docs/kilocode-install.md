# Installing Mpi-Kanban in KiloCode

KiloCode is an open-source AI coding agent for VS Code, JetBrains, and CLI
that auto-discovers **Agent Skills** from filesystem and URL sources. Mpi-Kanban
ships its workflow as a tree of skill folders, so KiloCode users have three
ways to install it. Pick the one that matches your setup.

## Compatibility matrix

| Install path | Effort | Skill features | Marketplace UI |
|--------------|--------|----------------|----------------|
| Compatibility path (Claude plugin already installed) | None | Full | n/a |
| Direct `kilo.jsonc` `skills.paths` clone | Low | Full | n/a |
| Kilo Marketplace pull (`skills-kilo/` generated tree) | Low | Full (inlined) | Yes |

All three paths surface the same 14 skills (`mpi-init`, `mpi-brainstorm`,
`mpi-create-plan`, `mpi-create-large-plan`, `mpi-continue`,
`mpi-execute-parallel`, `mpi-handoff`, `mpi-end-session`, `mpi-cleanup`,
`mpi-archive`, `mpi-brief-rule`, `mpi-project-setup`, `mpi-project-mode`,
`mpi-project-refresh`). The skills drive the per-project board at
`.claude/mpi-kanban/kanban.md`, which the companion `MadPonyInteractive.mpi-kanban`
VS Code extension renders.

## Option 1: Compatibility path (recommended if you already use Claude Code)

KiloCode automatically loads skills from `.claude/skills/` and `.agents/skills/`
in any workspace it opens. If you already installed `mpi-kanban` as a Claude
Code plugin, KiloCode will pick up the same skill tree with **no extra setup**.

Verify by opening the workspace in KiloCode and asking the agent to
`run $mpi-init` (or any other MPI skill). The agent will detect the skill in
the compatibility path.

## Option 2: Direct `kilo.jsonc` skills path

If you do not use Claude Code, clone the plugin repo somewhere stable and
point KiloCode at it.

1. Clone the repo:

   ```bash
   git clone https://github.com/MadPonyInteractive/mpi-kanban.git ~/plugins/mpi-kanban
   ```

2. Drop `templates/kilo.jsonc` into your project root and adjust the path,
   or merge the snippet into an existing `kilo.jsonc`:

   ```jsonc
   {
     "skills": {
       "paths": [
         "~/plugins/mpi-kanban/skills"
       ]
     }
   }
   ```

   See `templates/kilo.jsonc` in this repo for the full template with comments.

3. Restart KiloCode (or start a new session). All 14 `mpi-*` skills appear in
   the active skill list.

This install path uses the canonical shared skill tree at `skills/`, including
the sibling `lib/` and `templates/` reference docs the skills read at runtime.

## Option 3: Kilo Marketplace pull

The Kilo Marketplace at `Kilo-Org/kilo-marketplace` indexes individual skills
fetched by remote URL. Because the marketplace tool sparse-checks out only a
single skill folder, the standard `skills/mpi-*` tree (which references
`${CLAUDE_PLUGIN_ROOT}/lib/...`) would lose its sibling dependencies.

To support marketplace pulls, this repo ships `scripts/build_kilo_skills.py`,
which generates a self-contained `skills-kilo/mpi-*` tree by inlining every
sibling reference. The marketplace PR points at `skills-kilo/`, not `skills/`.

If you find the MPI skills in the Kilo Marketplace, install via the standard
marketplace UI or:

```bash
npx tsx bin/add-remote-skill.ts \
  https://github.com/MadPonyInteractive/mpi-kanban/tree/main/skills-kilo/mpi-init
```

Repeat for any skill you want; KiloCode auto-discovers them after the next
session starts.

## Companion VS Code extension

Whatever install path you choose, the board lives at
`<project-root>/.claude/mpi-kanban/kanban.md` in plain Markdown. To see it as a
Kanban UI inside VS Code, install the companion extension
[`MadPonyInteractive.mpi-kanban`](https://marketplace.visualstudio.com/items?itemName=MadPonyInteractive.mpi-kanban).
KiloCode users do not need this extension; the agent reads and writes the
Markdown board directly.

## Verifying the install

In KiloCode, ask the agent to run `$mpi-init`. The skill should respond with
its standard prompt asking for a freeform to-do file to import (or create a
fresh board). If the agent says it cannot find the skill, confirm:

- `kilo.jsonc` is at the workspace root and KiloCode picked it up.
- The skills path in `kilo.jsonc` resolves to an existing directory.
- For Option 3, the skill is present under `~/.kilo/skills/<name>/SKILL.md`.

## A note on the generator

`scripts/build_kilo_skills.py` is the first runtime-native target adapter
built on the canonical `skills/mpi-*` tree. The shared `skills/` source is
authoritative; `skills-kilo/` is a generated, Kilo-specific output. The
generator's internal steps (discover, transform, resolve references, write,
validate) are factored so future Codex or OpenCode adapters can reuse the
structure. Until then, the script name and the `skills-kilo/` directory stay
Kilo-specific.

## Updating

- Option 1: update the Claude plugin via `/plugin install mpi-kanban@...`.
- Option 2: `git pull` in the clone.
- Option 3: rerun the marketplace pull command for any updated skill.

The kanban board format and `.agents/mpi-kanban/state/` coordination contract
are stable across plugin versions; updating is safe mid-session.
