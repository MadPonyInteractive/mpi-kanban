---
name: mpi-execute-next
description: Execute the next incomplete to-do from an MPI plan file with brief and verified gates; transitions the kanban entry to IMPLEMENTING on first call.
---

Invoke the `mpi-execute-next` skill and follow it end-to-end. Both gates
(brief before code, verified after) are mandatory — never skip them. On the
first call against a plan, transition the kanban entry from PLANNING to
IMPLEMENTING and add the derived `steps` block.
