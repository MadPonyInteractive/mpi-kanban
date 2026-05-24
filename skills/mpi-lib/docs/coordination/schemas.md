# Minimal Coordination Schemas

These examples define the compact Phase 1 record shape. They are not exhaustive
JSON Schemas. Add fields only when they support agent coordination directly.

## `state/index.json`

```json
{
  "schema": "mpi-kanban/state-index/v1",
  "updated_at": "2026-05-17T12:00:00Z",
  "board": ".agents/mpi-kanban/kanban.md",
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
  "active_handoffs": [
    ".agents/mpi-kanban/state/handoffs/5e89a64e-5efd-4087-a4a6-75c64d4280a0.json"
  ]
}
```

`active_file_claims` lists only active write locks with file status `claimed`.
`pending_file_states` lists file records that no longer block writers but still
carry pending-change provenance, such as `complete`, `needs_review`,
`needs_verification`, or `needs_integration`.

## `state/sessions/<uuid>.json`

```json
{
  "schema": "mpi-kanban/session/v1",
  "id": "018f6e8a-7b9f-4f0b-85f3-6a11f6de2b1a",
  "agent": "codex",
  "role": "implementer",
  "status": "active",
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

