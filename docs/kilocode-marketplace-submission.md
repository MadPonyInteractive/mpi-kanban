# KiloCode Marketplace Submission Runbook

Maintainer runbook for publishing Mpi-Kanban skills to
[`Kilo-Org/kilo-marketplace`](https://github.com/Kilo-Org/kilo-marketplace).
Run this end-to-end whenever you cut a new release that should reach Kilo
users via the marketplace UI.

## Prerequisites

- Up-to-date local clone of `MadPonyInteractive/mpi-kanban` on `main`.
- A clean working tree (no uncommitted edits).
- The release tag for the version you are submitting (e.g. `v0.6.0`).
- `node` and `npx tsx` installed locally (the marketplace tooling is TypeScript).
- A GitHub fork of `Kilo-Org/kilo-marketplace` under your user/org.

## 1. Regenerate `skills-kilo/`

The shared `skills/` tree references `${CLAUDE_PLUGIN_ROOT}/lib/...` siblings
that do not survive a marketplace sparse-checkout. Submit the inlined,
self-contained tree under `skills-kilo/` instead.

```bash
python scripts/build_kilo_skills.py
```

Expected output: one row per skill (14 total) with inlined-file counts and
output bytes. Sanity-check by grepping the output tree:

```bash
grep -R "\${CLAUDE_PLUGIN_ROOT}" skills-kilo/    # must return zero hits
grep -R "inline-missing\|inline-cycle\|inline-depth-exceeded" skills-kilo/    # must return zero hits
```

`skills-kilo/` is gitignored in this repo. For the marketplace submission,
commit it into a fork branch of `mpi-kanban` so the marketplace fetcher can
sparse-check it out by URL.

## 2. Push the generated tree to a tagged release branch

The marketplace fetcher resolves `tree/<ref>` URLs. Use the release tag (or a
dedicated `kilo-release-<version>` branch) as `<ref>` so the marketplace
snapshot is reproducible.

```bash
git checkout -b kilo-release-0.6.0
git add -f skills-kilo/    # force-add despite .gitignore
git commit -m "Build skills-kilo for KiloCode marketplace 0.6.0"
git push origin kilo-release-0.6.0
```

Note: this commit lives only on the release branch. `main` keeps
`skills-kilo/` gitignored.

## 3. Fork `Kilo-Org/kilo-marketplace`

If you have not already forked it:

```bash
gh repo fork Kilo-Org/kilo-marketplace --clone --remote
cd kilo-marketplace
git checkout -b add-mpi-kanban-skills
```

If you already have a fork:

```bash
cd <wherever-your-fork-lives>
git fetch upstream
git checkout main
git merge upstream/main
git checkout -b add-mpi-kanban-skills
```

## 4. Add each skill via the marketplace script

Run `add-remote-skill.ts` once per skill. The script sparse-checks the skill
folder, copies it into `skills/<name>/`, and writes the `metadata.source`
block automatically.

```bash
SKILLS=(
  mpi-init
  mpi-brainstorm
  mpi-create-plan
  mpi-create-large-plan
  mpi-continue
  mpi-execute-parallel
  mpi-handoff
  mpi-end-session
  mpi-cleanup
  mpi-archive
  mpi-brief-rule
  mpi-project-setup
  mpi-project-mode
  mpi-project-refresh
)

for s in "${SKILLS[@]}"; do
  npx tsx bin/add-remote-skill.ts \
    "https://github.com/MadPonyInteractive/mpi-kanban/tree/kilo-release-0.6.0/skills-kilo/$s"
done
```

Each run should print success and leave a new directory under
`skills/<name>/SKILL.md` in your `kilo-marketplace` checkout.

## 5. Verify the metadata block

Spot-check one of the added skills:

```bash
head -20 skills/mpi-init/SKILL.md
```

Expected frontmatter:

```yaml
---
name: mpi-init
description: Initialize MPI kanban or import a freeform to-do / backlog / ideas markdown file...
metadata:
  source:
    repository: https://github.com/MadPonyInteractive/mpi-kanban
    path: skills-kilo/mpi-init
    license_path: LICENSE
  category: unknown
---
```

If `category` is `unknown`, edit it to `productivity` (closest fit for MPI
workflow tooling) before committing.

## 6. Commit and open PR

```bash
git add skills/
git commit -m "Add mpi-* skills (Mpi-Kanban v0.6.0)"
git push origin add-mpi-kanban-skills

gh pr create \
  --repo Kilo-Org/kilo-marketplace \
  --title "Add mpi-* skills" \
  --body "$(cat <<'EOF'
Adds 14 MPI workflow skills from MadPonyInteractive/mpi-kanban:

- mpi-init, mpi-brainstorm, mpi-create-plan, mpi-create-large-plan
- mpi-continue, mpi-execute-parallel, mpi-handoff, mpi-end-session
- mpi-cleanup, mpi-archive, mpi-brief-rule
- mpi-project-setup, mpi-project-mode, mpi-project-refresh

The skills drive a per-project Markdown kanban board at
.claude/mpi-kanban/kanban.md and a shared coordination state contract at
.agents/mpi-kanban/state/. They are pure Markdown (no executable layer).

Source: https://github.com/MadPonyInteractive/mpi-kanban
License: MIT
Companion VS Code extension: MadPonyInteractive.mpi-kanban

The skills-kilo/ tree pulled from kilo-release-0.6.0 is a generated,
self-contained version of the shared skills/ tree with all
${CLAUDE_PLUGIN_ROOT}/lib/... sibling references inlined so each skill is
loadable standalone via the marketplace.
EOF
)"
```

## 7. Post-merge smoke test

After the PR merges:

1. Open a fresh KiloCode workspace.
2. In the Kilo skill picker, search for `mpi-init`. It should appear with the
   description from the SKILL.md.
3. Install it via the marketplace UI (or `npx tsx bin/add-remote-skill.ts ...`
   pointed at the merged location).
4. Ask the agent to `run $mpi-init`. Confirm the skill prompts for a freeform
   to-do file or fresh-board creation.
5. Verify `.claude/mpi-kanban/kanban.md` is created with the locked column
   layout.

If any skill fails to surface or runs incorrectly, capture the error and file
an issue against `Kilo-Org/kilo-marketplace` (not this repo) so upstream can
investigate marketplace-side fetching.

## 8. Record the release

After PR merge, append to `CHANGELOG.md` under the matching version section:

```markdown
- KiloCode marketplace: published mpi-* skills to Kilo-Org/kilo-marketplace
  (PR <link>). Install via `npx tsx bin/add-remote-skill.ts <url>` or the
  marketplace UI once a Kilo release indexes the new skills.
```

## Per-release rerun

For each subsequent release that should reach Kilo users:

1. Rerun `python scripts/build_kilo_skills.py`.
2. Push a fresh `kilo-release-<version>` branch with the updated `skills-kilo/`.
3. Open a new marketplace PR with title `Update mpi-* skills (v<version>)` and
   rerun `add-remote-skill.ts` against the new branch URL.

The marketplace stores skills as static snapshots; bumping the version is the
only way to roll out skill changes to existing Kilo users.
