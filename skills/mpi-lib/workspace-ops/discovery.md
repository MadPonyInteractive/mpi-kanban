# Workspace Scope Discovery

Use this reference when a workflow needs to decide which folders belong to the
active Mpi-Kanban work context.

## Mental Model

One Kanban root represents one work context. The work context can be:

- a single folder containing `.agents/mpi-kanban/board.json`;
- a VS Code `.code-workspace` whose `folders` entries define all member
  folders for the shared board, coordination state, and message inbox;
- a separate peer Kanban root reached only by an explicit same-machine message.

Do not infer workspace membership from sibling folders on disk. A sibling
folder is outside scope unless it is listed in the active `.code-workspace` or
the user identifies it as a separate peer root for explicit routing.

## Active Root Selection

Resolve the active Kanban root in this order:

1. Use an explicit root from the user's prompt, handoff, task card, or
   coordination record.
2. If the current session is attached to a VS Code `.code-workspace`, use that
   file as the scope map. The Kanban root is the workspace member folder that
   owns `.agents/mpi-kanban/board.json` and `.agents/mpi-kanban/state/`.
3. If exactly one workspace member contains `.agents/mpi-kanban/board.json`,
   select that member as the Kanban root.
4. If multiple workspace members contain a board, ask the user which board is
   active or use an existing persisted project setting. Do not pick silently.
5. If no board exists, `mpi-init` may create one only in the selected project
   folder after its normal onboarding checks. Do not initialize every workspace
   member.

After selecting the Kanban root, read and write the board, task workspaces,
coordination state, and messages under that root unless a record explicitly
routes to a peer root.

## `.code-workspace` Parsing

Treat a `.code-workspace` file as a VS Code workspace descriptor. Parse the
top-level `folders` array. Each entry can contain:

- `path`: folder path, absolute or relative to the `.code-workspace` file's
  directory;
- `name`: optional display alias.

Resolve each member folder by normalizing `path`:

1. If `path` is absolute, normalize it as written.
2. If `path` is relative, resolve it relative to the directory containing the
   `.code-workspace` file.
3. Use `name` as the folder alias when present.
4. Otherwise use the final path segment of the resolved folder as the alias.

If the workspace file contains comments or trailing commas, use a JSONC-capable
parser when available. If no structured parser is available, inspect the
`folders` entries conservatively and do not infer extra folders.

## Folder Aliases And Roles

Use folder aliases in user-facing messages, file references, and coordination
records when a plain relative path could be ambiguous.

Folder-aware records use:

```json
{
  "workspace_folder": "Mpi-Kanban",
  "workspace_root": "C:/AI/Mpi/Plugins/Mpi-Kanban",
  "path": "README.md"
}
```

`workspace_folder` is the alias, `workspace_root` is the resolved member folder,
and `path` is relative to that member folder.

Roles are descriptive, not schema-enforced. Record them in profile/index notes
or message prose when helpful, for example:

- `Mpi-Kanban`: skill-pack source and active Kanban root;
- `mpi-kanban-vscode`: companion VS Code extension member folder.

Do not create new task-card fields for roles.

## Mpi-Kanban.code-workspace Example

`Mpi-Kanban.code-workspace` in this repository contains:

```json
{
  "folders": [
    {
      "path": "."
    },
    {
      "path": "../mpi-kanban-vscode"
    }
  ]
}
```

Because the workspace file lives in `C:/AI/Mpi/Plugins/Mpi-Kanban`, resolve the
members as:

| Alias | Resolved folder | Role |
|---|---|---|
| `Mpi-Kanban` | `C:/AI/Mpi/Plugins/Mpi-Kanban` | skill-pack source and active Kanban root |
| `mpi-kanban-vscode` | `C:/AI/Mpi/Plugins/mpi-kanban-vscode` | companion extension member folder |

Do not discover `C:/AI/Mpi/Plugins/*` as a set of implicit members. Only these
two folders are in scope for this workspace file.

## Outside-Folder Guidance

If the user asks for work in a related folder outside the active workspace
scope, pause before treating it as shared context. Use wording like:

```text
That folder is outside the active Mpi-Kanban workspace. Add it to the
.code-workspace folders list if it should share this board and message inbox,
or identify it as a separate peer Kanban root for an explicit same-machine
message.
```

Separate Kanban roots can exchange messages only through explicit peer routing.
Do not scan the machine for peers, broadcast globally, or assume every sibling
repository participates in the same board.
