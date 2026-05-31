# Coordination State Layout

The project-local coordination root is:

```text
.agents/mpi-kanban/state/
```

Expected layout:

```text
.agents/
  mpi-kanban/
    state/
      index.json
      sessions/
        <uuid>.json
      tasks/
        <uuid>.json
      files/
        <uuid>.json
      messages/
        <uuid>.json
      handoffs/
        <uuid>.json
      archive/
```

`index.json` is the first machine-readable file every agent checks. It should
remain small and pointer-driven. It directly lists active record paths, active
write claims, pending file states, open messages, and handoffs so agents can
decide what to inspect next.

The JSON task board remains human-visible state only:

```text
.agents/mpi-kanban/board.json
.agents/mpi-kanban/tasks/<id>/
```

The board must keep the locked `todo` / `doing` / `done` columns and task-card
fields required by the VS Code extension. Agent-only coordination details belong
in `.agents/mpi-kanban/state/`, not in extra board columns or task-card fields.

Do not reuse `.agents/mpi-kanban/state/tasks/` for human board cards. Human task
folders live under `.agents/mpi-kanban/tasks/<id>/`.

## Workspace Scope

One Kanban root represents one work context. In a single-folder project, paths
are relative to that project root unless a record says otherwise. In a VS Code
multi-root workspace, the active `.code-workspace` file is the scope map and its
`folders` entries are member folders of the same board, coordination state, and
message inbox.

Agents should not silently treat sibling folders as in scope. If the user asks
for work in a related folder outside the active workspace scope, recommend
adding that folder to the VS Code workspace first.

Coordination records that mention files may use folder-aware references when a
plain path is ambiguous:

```json
{
  "workspace_folder": "Website",
  "workspace_root": "C:/work/Website",
  "path": "src/App.tsx"
}
```

This distinguishes files such as `Website/src/App.tsx` and `App/src/App.tsx`
inside the same workspace context.

## Active Records

Active records should retain only recent operational history. Keep roughly the
last 5-10 events in each record and move long-term narrative context into
plans, docs, or handoffs.

Only file records with status `claimed` are active write locks. Completed or
released write ownership does not erase pending-change provenance; agents must
inspect pending file states before editing or committing related work.

Message records with status `open`, `acknowledged`, or `replied` belong in
`open_messages` when that key is present in `index.json`. Resolved,
superseded, or closed messages should not remain in the open-message index.
Message bodies and thread detail live only under `state/messages/`; task cards
and `index.json` keep compact pointers.

## Heartbeats

The default heartbeat timeout is 2 hours.

Stale claims are reclaimable by an orchestrator or integrator. Uncertain cases
should ask the user instead of guessing ownership intent.

## Cleanup

`mpi-cleanup` owns garbage collection for coordination state. It should keep
active state out of archive/delete proposals and move closed state out of
`index.json` only after approval. Approved terminal message records move under
`state/archive/messages/`; unresolved messages stay in `state/messages/` and
remain listed in `open_messages`.

