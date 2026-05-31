---
name: mpi-show
description: MPI workflow pack - Show or read one Mpi-Kanban board task/card by ID or title. Use when the user asks "what is MPI-5", "tell me about MPI-5", "show MPI-5", "open MPI-5", "read MPI-5", "what is this card", "what is this board entry about", "look at the <title> card", "$mpi-show", or "/mpi-show". Bounded read-only path: resolves board type, reads only the named JSON task folder and direct linked files, or one legacy Markdown entry when board.json is absent.
---

# mpi-show Skill

## Locating shared references

Shared reference docs live in the sibling skill `mpi-lib`. At first use, find the first existing directory from this candidate list:

1. `~/.agents/skills/mpi-lib`
2. `.agents/skills/mpi-lib`
3. `~/.claude/skills/mpi-lib`
4. `.claude/skills/mpi-lib`

Cache that root path for the rest of this session. All references below resolve as `<mpi-lib-root>/<sub/path>.md`. If no candidate exists, stop and tell the user to reinstall the complete pack with:

`npx skills add MadPonyInteractive/mpi-kanban --all -y -g`

## Purpose

Show one board task/card without changing project state. This is the owned path
for common read requests such as "what is MPI-5?", "tell me about this card",
or "open the <title> entry".

`mpi-show` is read-only. It does not move cards, edit checklists, update
handoffs, refresh project knowledge, or search sibling repositories.

## Required Reading

- `<mpi-lib-root>/task-board-ops/read.md` - JSON board lookup and task loading.
- `<mpi-lib-root>/task-board-ops/_schema.md` - task-card links and fields.
- `<mpi-lib-root>/kanban-ops/find.md` - legacy Markdown lookup only when
  `board.json` is absent.
- `<mpi-lib-root>/interop-ops/modes.md` - source-of-truth wording when needed.

## Inputs

Accept:

- Task ID: `MPI-5`
- Exact or partial task title: `Agent Message Bus`
- UI selection context if the agent receives one from the host tool

If the user says "this card" or "the selected entry" but no ID, title, or
structured selection is available in context, ask for the task ID or title.

## Process

### 1. Detect Board Type

1. Check for `.agents/mpi-kanban/board.json`.
2. If present, use the JSON board path. Ignore `.agents/mpi-kanban/kanban.md`
   except to mention that it is legacy/tombstoned if relevant.
3. If `board.json` is absent, check for legacy `.agents/mpi-kanban/kanban.md`
   and `.claude/mpi-kanban/kanban.md`.
4. If no board exists, stop and tell the user to run `mpi-init`.

`source_of_truth: "file"` in `.agents/mpi-kanban/state/interop.json` means the
JSON board and task workspaces when `board.json` exists. It does not mean
`kanban.md`.

### 2. Resolve The Named Entry

For JSON boards:

1. If input matches `^MPI-[1-9][0-9]*$`, find that ID in exactly one
   `board.json` column.
2. Otherwise, load visible `task.json` files listed by `board.json` and match
   title case-insensitively.
3. If multiple title matches exist, list the matching IDs and ask the user to
   choose one.
4. If no match exists, report that the task was not found on the active JSON
   board. Do not search sibling repos or legacy boards to "confirm" unless the
   user explicitly asks.

For legacy boards:

1. Use `<mpi-lib-root>/kanban-ops/find.md` `findEntry(predicate)`.
2. Match by exact title first, then case-insensitive title.
3. Legacy boards do not have `MPI-*` IDs unless the title/body explicitly
   contains one. If the user provided an `MPI-*` ID and no legacy entry matches,
   say the active legacy board has no such entry.

### 3. Read Adjacent Files

For JSON tasks, stay inside `.agents/mpi-kanban/tasks/<id>/` and read direct
links only:

1. Required: `task.json`.
2. Summary first: `brief.md`, when present.
3. Current work detail: `plan.md`, then `checklist.md`, when present.
4. Completion evidence: `validation.md`, when present.
5. File context: `files.json`, when present.
6. Recent activity: last 10 lines of `events.jsonl`, when present.
7. Handoffs: list files under `handoffs/` and read only the newest one unless
   the user asks for all.
8. Research: list files under `research/`; read only a named research file or
   the newest one if the task summary depends on it.

Do not follow links that escape the task folder. Do not scan the repository for
matching text unless the user explicitly asks for a broader investigation.

For legacy entries, read only the matching entry block. If it contains a
`Plan file: <path>` pointer, mention the pointer and ask before reading it
unless the user asked for implementation detail.

### 4. Report

Use this shape:

```text
<ID or legacy title> - <title>
Column: <todo | doing | done | legacy column>
Status: <status/maturity/attention summary when available>

Summary:
<brief explanation in plain language>

Linked context read:
- <files read or "task.json only">

Next useful action:
<one sentence, e.g. continue, review validation, archive, or no action obvious>
```

Keep the answer concise. If the task is large, summarize and offer specific
linked files that can be read next.

## Hard Rules

- Read one named task/card only.
- Prefer `board.json` whenever it exists.
- Do not read or edit `kanban.md` when `board.json` exists.
- Do not search sibling repositories or unrelated board surfaces.
- Do not mutate board, task, state, memory, docs, or plan files.
- Do not infer that `source_of_truth: file` means legacy Markdown.
