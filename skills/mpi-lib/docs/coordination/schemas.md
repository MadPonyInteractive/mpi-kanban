# Minimal Coordination Schemas

These examples define the compact Phase 1 record shape. They are not exhaustive
JSON Schemas. Add fields only when they support agent coordination directly.

## `state/index.json`

```json
{
  "schema": "mpi-kanban/state-index/v1",
  "updated_at": "2026-05-17T12:00:00Z",
  "board": ".agents/mpi-kanban/board.json",
  "heartbeat_timeout_minutes": 120,
  "active_sessions": [
    ".agents/mpi-kanban/state/sessions/018f6e8a-7b9f-4f0b-85f3-6a11f6de2b1a.json"
  ],
  "active_tasks": [
    ".agents/mpi-kanban/state/tasks/8b39a23b-bca6-4dd2-b1ab-64d90677d22e.json"
  ],
  "active_file_claims": [
    ".agents/mpi-kanban/state/files/63f0a8e1-17e1-42ff-8b8e-b510a4f58ec8.json"
  ],
  "pending_file_states": [
    ".agents/mpi-kanban/state/files/a90d5036-353d-4b7e-a6cc-0f11c9f804b8.json"
  ],
  "open_messages": [
    ".agents/mpi-kanban/state/messages/a3b8ac9e-9d78-4ef2-a0c6-034d3a6746d2.json"
  ],
  "active_handoffs": [
    ".agents/mpi-kanban/state/handoffs/5e89a64e-5efd-4087-a4a6-75c64d4280a0.json"
  ]
}
```

`active_file_claims` lists only active write locks with file status `claimed`.
`pending_file_states` lists file records that no longer block writers but still
carry pending-change provenance, such as `complete`, `needs_review`,
`needs_verification`, or `needs_integration`.
`open_messages` lists unresolved message records with status `open`,
`acknowledged`, or `replied`.

Use `.agents/mpi-kanban/kanban.md` here only for unmigrated legacy projects.

## `state/interop.json`

```json
{
  "schema": "mpi-kanban/interop/v1",
  "updated_at": "2026-05-27T12:00:00Z",
  "source_of_truth": "file",
  "last_detected_environment": {
    "kind": "generic",
    "detected_at": "2026-05-27T12:00:00Z",
    "signals": []
  },
  "last_sync_at": null,
  "last_export_at": null,
  "id_mappings": []
}
```

`source_of_truth` is `file` or `nimbalyst`. `file` is the default when this file
is absent. In `nimbalyst` mode, Nimbalyst trackers/sessions are canonical and
the JSON task board is imported or exported only on explicit sync boundaries.
`id_mappings` links MPI entries to Nimbalyst tracker IDs without adding card
metadata fields.

## `state/sessions/<uuid>.json`

```json
{
  "schema": "mpi-kanban/session/v1",
  "id": "018f6e8a-7b9f-4f0b-85f3-6a11f6de2b1a",
  "agent": "codex",
  "role": "implementer",
  "status": "active",
  "claude_session_id": "cf6200bf-9db8-41ca-9260-f38bdd986d44",
  "task": ".agents/mpi-kanban/state/tasks/8b39a23b-bca6-4dd2-b1ab-64d90677d22e.json",
  "heartbeat_at": "2026-05-17T12:00:00Z",
  "allowed_actions": ["read", "edit_owned_files", "update_plan", "handoff"],
  "recent_events": [
    {
      "at": "2026-05-17T11:45:00Z",
      "event": "session_started"
    }
  ]
}
```

## `state/files/<uuid>.json`

```json
{
  "schema": "mpi-kanban/file-claim/v1",
  "id": "63f0a8e1-17e1-42ff-8b8e-b510a4f58ec8",
  "path": "skills/mpi-handoff/SKILL.md",
  "owner_session": ".agents/mpi-kanban/state/sessions/018f6e8a-7b9f-4f0b-85f3-6a11f6de2b1a.json",
  "owner_role": "implementer",
  "status": "claimed",
  "claim_kind": "write",
  "heartbeat_at": "2026-05-17T12:00:00Z",
  "allowed_actions": ["edit", "verify"],
  "recent_events": [
    {
      "at": "2026-05-17T11:50:00Z",
      "event": "claimed_for_write"
    }
  ]
}
```

When a file claim is no longer actively being edited, keep the record and move
it out of `active_file_claims`. If the work still matters to review,
verification, integration, or final commit summary, set status to `complete`,
`needs_review`, `needs_verification`, or `needs_integration` and list it in
`pending_file_states`.

### What a claim covers

A record claims **either** one path or a set of paths:

- `path` - a single string. Use it for a single-file claim.
- `paths` - a list of strings. Use it for one claim over several files, which is
  what "module ownership" in `coordination-ops/lifecycle.md` means in practice.

Exactly one of the two is present. Both are first-class: a reader that only
looks at `path` silently misses every multi-file claim, which is how a live
project ran for weeks with claims on disk and nothing enforcing them.

An entry ending in `/` claims that subtree, not a file. `skills/mpi-continue/`
covers every file under it. Match a candidate file against a claim entry with:
exact string equality, or the entry ends in `/` and the candidate starts with
it.

Write these records as UTF-8 **without** a BOM. On Windows, PowerShell `>` and
`Out-File` add one by default; `Set-Content -Encoding utf8` in PowerShell 5.1
does too. A leading BOM makes a strict `JSON.parse` / `json.load` throw, so use
a writer that omits it, or read with `utf-8-sig`.

Folder-aware file references may replace or supplement plain `path` fields when
a VS Code workspace contains several folders:

```json
{
  "workspace_folder": "Website",
  "workspace_root": "C:/work/Website",
  "path": "src/App.tsx"
}
```

`workspace_folder` is the workspace member alias when available,
`workspace_root` is the resolved folder path, and `path` is relative to that
folder.

## `state/messages/<uuid>.json`

```json
{
  "schema": "mpi-kanban/message/v1",
  "id": "a3b8ac9e-9d78-4ef2-a0c6-034d3a6746d2",
  "status": "open",
  "created_at": "2026-05-31T12:00:00Z",
  "updated_at": "2026-05-31T12:00:00Z",
  "from": {
    "session": ".agents/mpi-kanban/state/sessions/018f6e8a-7b9f-4f0b-85f3-6a11f6de2b1a.json",
    "agent": "codex",
    "role": "implementer"
  },
  "to": {
    "selector": "file",
    "value": {
      "workspace_folder": "Website",
      "workspace_root": "C:/work/Website",
      "path": "src/App.tsx"
    }
  },
  "subject": "Request file-claim handoff",
  "body": "I need to edit this file for MPI-2. Can you release or hand off the claim?",
  "related": {
    "task_card": "MPI-2",
    "task": ".agents/mpi-kanban/state/tasks/8b39a23b-bca6-4dd2-b1ab-64d90677d22e.json",
    "files": [
      {
        "workspace_folder": "Website",
        "workspace_root": "C:/work/Website",
        "path": "src/App.tsx"
      }
    ]
  },
  "thread": {
    "root": null,
    "parent": null
  },
  "recent_events": [
    {
      "at": "2026-05-31T12:00:00Z",
      "event": "created"
    }
  ]
}
```

Message status values are `open`, `acknowledged`, `replied`, `resolved`,
`superseded`, and `closed`. Recipient selectors are `session`, `agent`, `role`,
`task`, `file`, `workspace`, and `user`.

Same-machine peer routing writes the record into a known peer workspace root's
`.agents/mpi-kanban/state/messages/` directory and adds provenance fields:

```json
{
  "from_workspace": "C:/work/Mpi-Kanban",
  "to_workspace": "C:/work/mpi-kanban-vscode"
}
```

Peer routing is explicit. It is not remote delivery, a global broadcast, or a
daemon-backed queue.

## `state/tasks/<uuid>.json`

```json
{
  "schema": "mpi-kanban/task/v1",
  "id": "8b39a23b-bca6-4dd2-b1ab-64d90677d22e",
  "title": "Implement shared coordination contract",
  "status": "in_progress",
  "kanban_entry": "Design shared agent coordination layer",
  "plan": "docs/plans/2026-05-17-shared-agent-coordination-phase-1.md",
  "owner_session": ".agents/mpi-kanban/state/sessions/018f6e8a-7b9f-4f0b-85f3-6a11f6de2b1a.json",
  "file_claims": [
    ".agents/mpi-kanban/state/files/63f0a8e1-17e1-42ff-8b8e-b510a4f58ec8.json"
  ],
  "allowed_actions": ["coordinate", "claim_files", "handoff"],
  "recent_events": [
    {
      "at": "2026-05-17T11:45:00Z",
      "event": "task_started"
    }
  ]
}
```

## `state/handoffs/<uuid>.json`

```json
{
  "schema": "mpi-kanban/handoff/v1",
  "id": "5e89a64e-5efd-4087-a4a6-75c64d4280a0",
  "generated_at": "2026-05-17T12:00:00Z",
  "from_session": ".agents/mpi-kanban/state/sessions/018f6e8a-7b9f-4f0b-85f3-6a11f6de2b1a.json",
  "to_role": "implementer",
  "status": "open",
  "plan": "docs/plans/2026-05-17-shared-agent-coordination-phase-1.md",
  "kanban_entry": "Design shared agent coordination layer",
  "summary": "Phase 1 docs are drafted; validation remains.",
  "next_action": "Run validator and targeted wording checks.",
  "allowed_actions": ["read", "verify", "continue"],
  "files_to_read_first": [
    "docs/plans/2026-05-17-shared-agent-coordination-phase-1.md",
    "docs/coordination/README.md"
  ],
  "recent_events": [
    {
      "at": "2026-05-17T12:00:00Z",
      "event": "handoff_created"
    }
  ]
}
```

