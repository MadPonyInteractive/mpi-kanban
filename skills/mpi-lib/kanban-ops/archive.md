# kanban-ops/archive - archive entries

Read this when the user asks to archive kanban entries. For locating the board
and parsing entries, also read `find.md` and `_schema.md`. For error wording,
also read `errors.md`.

---

## Archive file location

Archive files live beside the board:

```text
<project-root>/.agents/mpi-kanban/archived.md
<project-root>/.agents/mpi-kanban/archived-2.md
<project-root>/.agents/mpi-kanban/archived-3.md
```

Use `archived.md` first. If it exists and is over 200 lines, choose the first
incrementing filename whose file is missing or has 200 lines or fewer.

The archive file is plain Markdown, not a rendered kanban board. It stores
verbatim entry blocks grouped by archive batch.

---

## `selectArchiveFile()`

1. Resolve archive directory: `<project-root>/.agents/mpi-kanban/`.
2. Check `archived.md`.
3. If `archived.md` does not exist, use it.
4. If it exists and has 200 lines or fewer, use it.
5. If it exists and has more than 200 lines, check `archived-2.md`,
   `archived-3.md`, and so on. Use the first missing file or the first file
   with 200 lines or fewer.
6. If creating a new archive file, start it with:

   ```markdown
   # Archived Kanban Entries

   ```

---

## `archiveEntries(selector)`

Supported selectors:

- `completed` - archive every entry currently under `## COMPLETED`.
- `title` - archive the single entry whose H3 title exactly matches the user
  supplied title.

Procedure:

1. Read `find.md` for `findKanban()`.
2. Call `findKanban()`. If the board is missing, abort with:
   `Error: No kanban.md found at .agents/mpi-kanban/kanban.md. Nothing to archive.`
   Do not call `ensureKanban()` for archive requests.
3. Read `_schema.md` for the column and entry block shape.
4. Collect matching entry blocks:
   - `completed`: collect every `### ` block between `## COMPLETED` and EOF.
   - `title`: search all columns in order. A match is exact after trimming
     surrounding whitespace. If zero matches, abort. If more than one match,
     abort as ambiguous and list the matching columns.
5. If selector is `completed` and no entries exist in COMPLETED, report:
   `No completed kanban entries to archive.`
6. Call `selectArchiveFile()`.
7. Build one append block:

   ```markdown
   ## Archived YYYY-MM-DD

   Source: .agents/mpi-kanban/kanban.md

   ### Entry Title

   ...

   ```

   Use the current date. Preserve each entry block verbatim, including its
   metadata, body fence, steps, and trailing blank line.
8. Write or edit the archive file:
   - Missing file: write the header plus the append block.
   - Existing file: append the block at EOF, preserving one blank line between
     archive batches.
9. Remove each archived block from `kanban.md` only after the archive write
   succeeds. Remove the exact verbatim block captured in step 4.
10. Verify `kanban.md` still contains the five locked H2 headings and no
    archived title remains in its original location.
11. Report the result with clickable links:
    - `[kanban.md](.agents/mpi-kanban/kanban.md)`
    - `[archived.md](.agents/mpi-kanban/<archive-file>)`

---

## Hard rules

- Never archive by fuzzy title match. If the title is not exact, list likely
  candidates and ask the user to choose.
- Never delete an entry block before it has been written to an archive file.
- Never create archive files outside `.agents/mpi-kanban/`.
- Never modify entry metadata while archiving. Preserve the block verbatim.
- Do not call `ensureKanban()` for archive operations. Archiving a missing
  board is a no-op with an error report, not a bootstrap event.

