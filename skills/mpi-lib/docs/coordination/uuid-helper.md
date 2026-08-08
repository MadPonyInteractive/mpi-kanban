# UUID Helper

Core coordination records use UUIDs as primary IDs. Agents should use the shared
helper instead of inventing IDs from timestamps or task titles.

Generate one UUID:

```powershell
python <mpi-lib-root>/scripts/new_uuid.py
```

Generate several UUIDs:

```powershell
python <mpi-lib-root>/scripts/new_uuid.py 5
```

The helper emits lowercase UUIDv4 values, one per line. Use the same UUID for
the record `id` and the filename:

```text
.agents/mpi-kanban/state/tasks/<uuid>.json
```

If the helper is missing from the install, fall back to the standard library
instead of skipping the record:

```powershell
python -c "import uuid; print(uuid.uuid4())"
```

Never invent an ID from a timestamp or title, and never skip writing the record
because the helper could not be found.
