# Committing in a shared tree

The commit recipe for `mpi-handoff` and `mpi-end-session`. An MPI tree may have
live peer agents in it, so a commit is not "save my work" - it is a claim about
which bytes are yours, and git will happily publish someone else's under your
message.

## Why staging by name is not enough

`git add <path>` puts your files in the index. A plain `git commit` afterwards
commits **the whole index**, so anything a peer had already staged rides along
under your subject line. Staging carefully and then committing carelessly is
the failure; the pack shipped exactly that advice until 1.5.0.

The commit must carry the pathspec, not just the `add`.

## The recipe

```bash
git status --short                      # what is actually there
git add <new-path> [<new-path> ...]     # ONLY files git does not track yet
git commit --only <path> [<path> ...] -m "<subject>"
git status --short                      # AFTER, not only before
```

`--only` commits exactly the listed paths and nothing else, whatever the index
holds. That is the property staging by name does not give you.

## The three ways it goes wrong

**An UNTRACKED path aborts the whole commit.** `--only` resolves its pathspec
against what git tracks, so a brand-new file fails with
`error: pathspec '<file>' did not match any file(s) known to git` and takes the
tracked paths down with it. It reads like a typo or a wrong working directory;
it is neither. `git add` every new file first - still never `-A` or `.` - then
name it in the same `--only` list.

**A DIRECTORY pathspec hides that trap SILENTLY.** `git commit --only <dir>/`
matches the directory's *tracked* files, skips the untracked ones, prints
nothing and exits 0. A card move that creates `checklist.md`, `validation.md`
and `files.json` then commits without them: the files exist on disk, the card
looks complete, and the commit is missing half of it. The loud form above at
least stops you. **Name files, not directories**, and read
`git status --short` afterwards - leftover `??` lines under a path you just
committed are this bug and nothing else.

**A pre-commit hook that stashes can fold a peer's edits in.** `lint-staged`
and friends stash the working tree, run, and reapply; that cycle can pull a
sibling's unstaged changes into your commit even when your index was clean. If
the project has such a hook, check `git show --stat HEAD` after committing and
confirm it lists only your files.

## Backticks in `-m` are command substitution

`git commit -m "adds \`someFlag\` to the parser"` **runs** `someFlag`. The
shell prints `command not found` to stderr and the commit lands anyway with a
hole where that word should be. Exit 0, message silently wrong, and the log is
the one place nobody re-reads. Double quotes do not protect backticks.

- Message contains a backtick -> write it to a file inside the repo and use
  `git commit -F <file>`, with the flag BEFORE any `--`.
- Never repair it with `--amend -m`; that re-runs the same substitution. Amend
  with `-F`.
- `guard-git` blocks this at the tool call when the plugin is installed, but
  the rule outlives any one repo's hooks.

## Never

- `git add -A`, `git add .`, `git add --all` - they stage every peer's
  half-finished edit in the tree. `guard-git` blocks these too.
- `git commit -a` - same sweep, one flag shorter.
- Force-push, or auto-rebase a shared tree.

## Verify

Reading the exit code is not verification. After every commit:

```bash
git status --short          # no leftover ?? under a path you just committed
git show --stat HEAD        # exactly the files you named, no peer's
```
