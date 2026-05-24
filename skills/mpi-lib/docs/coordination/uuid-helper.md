# UUID Helper

Core coordination records use UUIDs as primary IDs. Agents should use the shared
helper instead of inventing IDs from timestamps or task titles.

Generate one UUID:

```powershell
python scripts/new_uuid.py
```

Generate several UUIDs:

```powershell
python scripts/new_uuid.py 5
```

The helper emits lowercase UUIDv4 values, one per line. Use the same UUID for
the record `id` and the filename:

```text
.agents/mpi-kanban/state/tasks/<uuid>.json
```

