"""Validate a live Mpi-Kanban JSON task board.

Usage:

    python validate_board.py [project-root] [--fix]
    python validate_board.py --selftest

`--fix` repairs two things. First, orphaned task folders - a `tasks/<id>/` with
a `task.json` that no `board.json` column lists, the residue of a card create
that stopped halfway - by listing the id in the column its own card names and
appending the missing `task.created` event. Second, the five derived arrays of
`state/index.json`, rebuilt from the status of each record on disk. Nothing
else is auto-repaired: both are restatements of facts already written down,
never a judgement call.

`project-root` defaults to the current directory. The board is expected at
`<project-root>/.agents/mpi-kanban/board.json`; a project with no board is not
an error. Exits 0 when the board is consistent, 1 with one line per violation.

This ships with the `mpi-lib` skill so any project can check its own board.
The pack's own `scripts/validate_plugin.py` imports this module instead of
keeping a second copy of the rules, which also makes the maturity enum below
the single code-level source of truth.
"""
from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

TASK_ID = re.compile(r"^MPI-[1-9][0-9]*$")
TASK_COLUMNS = ("todo", "doing", "done")
TASK_MATURITIES = (
    "idea", "planned", "research", "needs-decision", "blocked", "deferred",
    "in-progress", "validating", "complete", "rejected",
)
TASK_MATURITY_BY_COLUMN = {
    "todo": {"idea", "planned", "research", "needs-decision", "blocked", "deferred"},
    "doing": {"in-progress", "validating"},
    "done": {"complete", "rejected"},
}
TASK_REQUIRED_FIELDS = {"schema", "id", "title", "column", "created_at", "updated_at", "links"}
FILE_CLAIM_STATUSES = {
    "claimed", "complete", "needs_review", "needs_verification",
    "needs_integration", "verified", "released", "stale", "closed",
}
UNRESOLVED_COORDINATION_STATUSES = {
    "needs_review",
    "needs_verification",
    "needs_integration",
}
# The five derived arrays of state/index.json: which directory each one indexes
# and which record statuses belong in it, per the "Index Rules" section of
# coordination-ops/lifecycle.md. `active_tasks` is NOT here - it is checked
# record-by-record above, because a task record pointing at a done card needs a
# judgement the status alone does not carry.
INDEX_ARRAYS = {
    "active_sessions": ("sessions", {"active", "idle", "handoff_ready"}),
    "active_file_claims": ("files", {"claimed"}),
    "pending_file_states": ("files", UNRESOLVED_COORDINATION_STATUSES | {"complete"}),
    "open_messages": ("messages", {"open", "acknowledged", "replied"}),
    "active_handoffs": ("handoffs", {"open", "accepted"}),
}


def now() -> str:
    """A timestamp from the clock, offset included, matching what boards carry."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def style(path: Path) -> tuple[str, int]:
    """(newline, indent) copied off an existing file, so a write stays a one-line diff.

    Boards in the wild are `indent=2` with CRLF; this repo's own is `indent=1`.
    Rewriting with json.dump defaults reformats the whole file into a useless diff.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return "\n", 2
    newline = "\r\n" if b"\r\n" in raw else "\n"
    for line in raw.decode("utf-8-sig", "replace").splitlines()[1:]:
        stripped = line.lstrip(" ")
        if stripped and stripped != "}":
            return newline, len(line) - len(stripped) or 2
    return newline, 2


def write_json(path: Path, data: dict, newline: str, indent: int,
               exclusive: bool = False) -> None:
    """Write `data`, keeping the file's own newline and indent.

    `exclusive` uses mode 'x', never 'w': 'w' silently overwrites the card another
    agent just created, and the loser only finds out if they happen to commit.
    """
    body = (json.dumps(data, indent=indent, ensure_ascii=False) + "\n").replace("\n", newline)
    if exclusive:
        with open(path, "xb") as handle:
            handle.write(body.encode("utf-8"))
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(body.encode("utf-8"))
    os.replace(tmp, path)


def append_event(path: Path, record: dict, newline: str) -> None:
    line = (json.dumps(record, ensure_ascii=False) + "\n").replace("\n", newline)
    with open(path, "ab") as handle:
        handle.write(line.encode("utf-8"))


def load_json(errors: list[str], path: Path, label: str) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is invalid JSON: {exc}")
    except OSError as exc:
        errors.append(f"{label} could not be read: {exc}")
    return None


def validate_event_log(
    errors: list[str], path: Path, label: str, *, require_task_id: bool = False
) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"{label} could not be read: {exc}")
        return
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{label}:{index} malformed JSONL event: {exc}")
            continue
        if not isinstance(event, dict):
            errors.append(f"{label}:{index} event must be a JSON object")
            continue
        if event.get("schema") != "mpi-kanban/event/v1":
            errors.append(f"{label}:{index} event schema must be mpi-kanban/event/v1")
        if not event.get("type"):
            errors.append(f"{label}:{index} event missing type")
        if not event.get("at"):
            errors.append(f"{label}:{index} event missing at")
        if require_task_id and not event.get("id"):
            errors.append(f"{label}:{index} task event missing id")


def linked_path_is_inside(task_dir: Path, link_value: object) -> Path | None:
    if not isinstance(link_value, str) or not link_value:
        return None
    if Path(link_value).is_absolute():
        return None
    target = (task_dir / link_value).resolve()
    try:
        target.relative_to(task_dir.resolve())
    except ValueError:
        return None
    return target


def validate_board(root: Path) -> list[str]:
    """Return one message per board violation. Empty list means the board is fine."""
    errors: list[str] = []
    board_root = root / ".agents" / "mpi-kanban"
    board_path = board_root / "board.json"
    if not board_path.exists():
        return errors

    board = load_json(errors, board_path, ".agents/mpi-kanban/board.json")
    if not isinstance(board, dict):
        return errors
    if board.get("schema") != "mpi-kanban/board/v1":
        errors.append(".agents/mpi-kanban/board.json schema must be mpi-kanban/board/v1")
    next_id = board.get("next_id")
    if not isinstance(next_id, int) or next_id < 1:
        errors.append(".agents/mpi-kanban/board.json next_id must be a positive integer")

    columns = board.get("columns")
    if not isinstance(columns, dict) or tuple(columns.keys()) != TASK_COLUMNS:
        errors.append(".agents/mpi-kanban/board.json columns must be exactly todo, doing, done")
        return errors

    listed: dict[str, str] = {}
    max_suffix = 0
    for column in TASK_COLUMNS:
        ids = columns.get(column)
        if not isinstance(ids, list):
            errors.append(f".agents/mpi-kanban/board.json column {column} must be a list")
            continue
        for task_id in ids:
            if not isinstance(task_id, str) or not TASK_ID.match(task_id):
                errors.append(
                    f".agents/mpi-kanban/board.json contains invalid task id in {column}: {task_id!r}"
                )
                continue
            if task_id in listed:
                errors.append(f"task id {task_id} appears in both {listed[task_id]} and {column}")
            listed[task_id] = column
            max_suffix = max(max_suffix, int(task_id.split("-", 1)[1]))

    if isinstance(next_id, int) and next_id <= max_suffix:
        errors.append(
            ".agents/mpi-kanban/board.json next_id must be greater than all existing task IDs"
        )

    tasks_root = board_root / "tasks"
    for task_id, column in listed.items():
        task_dir = tasks_root / task_id
        task_json = task_dir / "task.json"
        rel = task_json.relative_to(root)
        if not task_json.exists():
            errors.append(f"listed task {task_id} is missing {rel}")
            continue
        task = load_json(errors, task_json, str(rel))
        if not isinstance(task, dict):
            continue
        if task.get("schema") != "mpi-kanban/task-card/v1":
            errors.append(f"{rel} schema must be mpi-kanban/task-card/v1")
        missing = TASK_REQUIRED_FIELDS - set(task)
        if missing:
            errors.append(f"{rel} missing required fields: {sorted(missing)}")
        if task.get("id") != task_id:
            errors.append(f"{rel} id must match folder/listed id {task_id}")
        if task.get("column") != column:
            errors.append(f"{rel} column must match board column {column}")
        maturity = task.get("maturity")
        if maturity is not None:
            if maturity not in TASK_MATURITIES:
                errors.append(
                    f"{rel} maturity must be one of {', '.join(TASK_MATURITIES)}; "
                    f"got {maturity!r}, which renders as an invalid card"
                )
            elif maturity not in TASK_MATURITY_BY_COLUMN[column]:
                errors.append(f"{rel} maturity {maturity!r} is invalid for column {column}")
        if column == "done" and task.get("status") == "active":
            errors.append(f"{rel} is done but still has status active")
        links = task.get("links")
        if not isinstance(links, dict):
            errors.append(f"{rel} links must be an object")
            continue
        for key, value in links.items():
            target = linked_path_is_inside(task_dir, value)
            if target is None:
                errors.append(f"{rel} link {key!r} must be a relative path inside the task folder")
                continue
            if target.exists() and target.name == "events.jsonl":
                validate_event_log(errors, target, str(target.relative_to(root)), require_task_id=True)
            if target.exists() and target.name.endswith(".json"):
                load_json(errors, target, str(target.relative_to(root)))
        checklist = linked_path_is_inside(task_dir, links.get("checklist"))
        validation = linked_path_is_inside(task_dir, links.get("validation"))
        brief = linked_path_is_inside(task_dir, links.get("brief"))
        attention = task.get("attention")
        if column == "doing" and checklist is not None and not checklist.exists():
            errors.append(f"{rel} is in doing but missing linked checklist.md")
        if column == "done" and validation is not None and not validation.exists():
            errors.append(f"{rel} is in done but missing linked validation.md")
        if (
            isinstance(attention, dict)
            and attention.get("state") == "required"
            and brief is not None
            and not brief.exists()
        ):
            errors.append(f"{rel} requires attention but missing linked brief.md")

    if tasks_root.exists():
        for child in tasks_root.iterdir():
            if child.is_dir() and (child / "task.json").exists() and child.name not in listed:
                errors.append(f"orphaned task folder not listed in board.json: {child.relative_to(root)}")

    validate_event_log(errors, board_root / "events.jsonl", ".agents/mpi-kanban/events.jsonl")

    state_index = board_root / "state" / "index.json"
    if state_index.exists():
        state = load_json(errors, state_index, ".agents/mpi-kanban/state/index.json")
        if isinstance(state, dict):
            if state.get("board") != ".agents/mpi-kanban/board.json":
                errors.append(
                    ".agents/mpi-kanban/state/index.json board must point to "
                    ".agents/mpi-kanban/board.json when board.json exists"
                )
            active_tasks = state.get("active_tasks", [])
            if not isinstance(active_tasks, list):
                errors.append(".agents/mpi-kanban/state/index.json active_tasks must be a list")
            else:
                for value in active_tasks:
                    if not isinstance(value, str):
                        errors.append(
                            ".agents/mpi-kanban/state/index.json active_tasks entries must be strings"
                        )
                        continue
                    task_record_path = root / value
                    if not task_record_path.exists():
                        errors.append(
                            f".agents/mpi-kanban/state/index.json active task is missing: {value}"
                        )
                        continue
                    task_record = load_json(errors, task_record_path, value)
                    if not isinstance(task_record, dict):
                        continue
                    status = task_record.get("status")
                    if status == "closed":
                        errors.append(f"{value} is closed but still listed in active_tasks")
                    task_card = task_record.get("task_card")
                    if isinstance(task_card, str) and listed.get(task_card) == "done":
                        if status not in UNRESOLVED_COORDINATION_STATUSES:
                            errors.append(
                                f"{value} points at done card {task_card} with resolved status "
                                f"{status!r}; remove it from active_tasks or mark the unresolved "
                                "state explicitly"
                            )
            validate_state_index(errors, board_root, state)

    validate_file_claims(errors, board_root)

    return errors



def derive_index_arrays(board_root: Path) -> dict[str, list[str]]:
    """The five derived index arrays as the records on disk say they should be.

    Status-based, and deliberately NOT heartbeat-based: a stale heartbeat is not
    a dead session, and `guard-claim` counts live peers by listing `sessions/`
    rather than reading this index, so a session dropped here on a freshness
    guess would be a lie with no upside.
    """
    derived: dict[str, list[str]] = {}
    cache: dict[str, list[tuple[str, object]]] = {}
    for field, (subdir, statuses) in INDEX_ARRAYS.items():
        if subdir not in cache:
            records: list[tuple[str, object]] = []
            directory = board_root / "state" / subdir
            if directory.is_dir():
                for path in sorted(directory.glob("*.json")):
                    try:
                        records.append((f".agents/mpi-kanban/state/{subdir}/{path.name}",
                                        json.loads(path.read_text(encoding="utf-8-sig"))))
                    except (OSError, json.JSONDecodeError):
                        continue  # an unreadable record is the per-record checks' problem
            cache[subdir] = records
        derived[field] = [rel for rel, record in cache[subdir]
                          if isinstance(record, dict) and record.get("status") in statuses]
    return derived


def entry_path(value: object) -> str | None:
    """The record path an index entry points at, string or object form.

    The contract is a list of path strings, but Cubric-Vision's index carried 28
    inlined objects in `active_handoffs` alone - `{"id": ..., "path": ...,
    "status": "resolved", ...}`, a whole record copied into the index. Reading
    the path out of them is what lets the rest of the check still run; they are
    reported as a shape violation, and `--fix` writes them back as strings.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("path"), str):
        return value["path"]
    return None


def summarise(values: list[str]) -> str:
    """Name a few records, not all 274 of them - a wall of paths is not a report."""
    head = ", ".join(value.rsplit("/", 1)[-1] for value in values[:5])
    return head + (f", +{len(values) - 5} more" if len(values) > 5 else "")


def validate_state_index(errors: list[str], board_root: Path, state: dict) -> None:
    """Nothing reconciled the derived index arrays until MPI-36, and they drift.

    Measured 2026-09-21: Cubric-Vision's index claimed 41 open messages against
    30 on disk, 7 active sessions against 14, and its `active_handoffs` had
    regrown 3 -> 32 in the five weeks since a hand prune. The only repair was a
    prose sweep in `mpi-cleanup`, and the numbers say it was not being run.
    """
    label = ".agents/mpi-kanban/state/index.json"
    for field, expected in derive_index_arrays(board_root).items():
        listed_raw = state.get(field, [])
        if not isinstance(listed_raw, list):
            errors.append(f"{label} {field} must be a list")
            continue
        inlined = sum(1 for value in listed_raw if not isinstance(value, str))
        if inlined:
            errors.append(f"{label} {field} has {inlined} entry/entries inlined as objects; "
                          "the contract is a list of record paths")
        listed = [path for path in map(entry_path, listed_raw) if path is not None]
        unreadable = len(listed_raw) - len(listed)
        if unreadable:
            errors.append(f"{label} {field} has {unreadable} entry/entries that name no record path")
        duplicates = len(listed) - len(set(listed))
        if duplicates:
            # On its own a duplicate trips neither extra nor missing, so without
            # this line an index can be wrong and report nothing.
            errors.append(f"{label} {field} lists {duplicates} record(s) twice")
        extra = [value for value in listed if value not in expected]
        missing = [value for value in expected if value not in listed]
        if extra:
            errors.append(f"{label} {field} lists {len(extra)} record(s) whose status no "
                          f"longer qualifies: {summarise(extra)}")
        if missing:
            errors.append(f"{label} {field} is missing {len(missing)} record(s): "
                          f"{summarise(missing)}")


def validate_file_claims(errors: list[str], board_root: Path) -> None:
    """Nothing validated state/files/ until MPI-26, and it had drifted."""
    claims_root = board_root / "state" / "files"
    if not claims_root.is_dir():
        return
    for record_path in sorted(claims_root.glob("*.json")):
        label = f".agents/mpi-kanban/state/files/{record_path.name}"
        if record_path.read_bytes().startswith(codecs.BOM_UTF8):
            errors.append(f"{label} starts with a UTF-8 BOM; write it without one")
        record = load_json(errors, record_path, label)
        if not isinstance(record, dict):
            continue
        if record.get("schema") != "mpi-kanban/file-claim/v1":
            errors.append(f"{label} schema must be mpi-kanban/file-claim/v1")
        path, paths = record.get("path"), record.get("paths")
        if (path is None) == (paths is None):
            errors.append(f"{label} must set exactly one of path or paths")
        elif path is not None and not isinstance(path, str):
            errors.append(f"{label} path must be a string")
        elif paths is not None and (
            not isinstance(paths, list) or not all(isinstance(v, str) for v in paths)
        ):
            errors.append(f"{label} paths must be a list of strings")
        status = record.get("status")
        if status not in FILE_CLAIM_STATUSES:
            errors.append(f"{label} has unknown status {status!r}")
        if status != "claimed":
            continue
        # A claim that outlives its owner locks the NEXT session out of its own
        # card. It happened on 2026-09-21: a session handed MPI-36 over with its
        # claim still `claimed`, and `guard-claim` refused the successor every
        # write. The heartbeat was five minutes old, so freshness could not tell
        # a handed-off session from a working one. Its STATUS can.
        owner = record.get("owner_session")
        if not isinstance(owner, str):
            errors.append(f"{label} is claimed but names no owner_session")
            continue
        owner_path = board_root.parents[1] / owner
        if not owner_path.is_file():
            errors.append(f"{label} is claimed but its owner session record is missing: {owner}")
            continue
        owner_record = load_json(errors, owner_path, owner)
        owner_status = owner_record.get("status") if isinstance(owner_record, dict) else None
        if owner_status != "active":
            errors.append(
                f"{label} is still claimed while its owner session is {owner_status!r}; "
                "release or complete it, or the next session is locked out of its own card"
            )

def already_logged(path: Path, task_id: str) -> bool:
    """Whether this log already carries a `task.created` for `task_id`."""
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return False
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("type") == "task.created" \
                and record.get("id") == task_id:
            return True
    return False


def repair_orphans(root: Path) -> list[str]:
    """Put orphaned task folders back on the board. Returns one line per repair.

    An orphan is a `tasks/<id>/` with a `task.json` that no column lists - the
    residue of a create that stopped after writing the card. The repair is the
    one the two 2026-08-27 orphans needed by hand: insert the id at the head of
    the column its own `task.json` names, and append the missing `task.created`.

    Deliberately narrow. It does not touch maturities, columns, links or claims:
    a --fix that rewrites judgement calls is one nobody can run without reading
    the diff, which defeats the point of having it.
    """
    board_path = root / ".agents" / "mpi-kanban" / "board.json"
    board_root = board_path.parent
    if not board_path.is_file():
        return []
    board = load_json([], board_path, "board.json")
    columns = board.get("columns") if isinstance(board, dict) else None
    if not isinstance(columns, dict):
        return []  # a board this broken needs a human, not an automatic insert
    listed = {task_id for column in TASK_COLUMNS for task_id in (columns.get(column) or [])}
    tasks_root = board_root / "tasks"
    if not tasks_root.is_dir():
        return []

    newline, indent = style(board_path)
    repaired: list[str] = []
    for child in sorted(tasks_root.iterdir()):
        if not child.is_dir() or child.name in listed or not (child / "task.json").is_file():
            continue
        card = load_json([], child / "task.json", child.name)
        if not isinstance(card, dict):
            continue
        column = card.get("column") if card.get("column") in TASK_COLUMNS else "todo"
        columns.setdefault(column, []).insert(0, child.name)
        suffix = child.name.rsplit("-", 1)[-1]
        if suffix.isdigit():
            board["next_id"] = max(int(board.get("next_id") or 1), int(suffix) + 1)
        record = {"schema": "mpi-kanban/event/v1", "type": "task.created", "id": child.name,
                  "at": card.get("created_at") or now(), "actor": "validate_board --fix",
                  "column": column, "title": card.get("title") or child.name}
        for log in (board_root / "events.jsonl", child / "events.jsonl"):
            if not already_logged(log, child.name):
                append_event(log, record, newline)
        repaired.append(f"listed orphan {child.name} in {column}")

    if repaired:
        write_json(board_path, board, newline, indent)
    return repaired


def repair_state_index(root: Path) -> list[str]:
    """Rewrite the five derived index arrays from the records on disk.

    The corrected arrays are built IN MEMORY and the whole file is written
    through `write_json`, which keeps the file's own newline and indent so the
    change reads one line per entry. Never byte-patched: slicing an entry out of
    the text breaks when it is the array's LAST element, which is how an index
    has been corrupted before.

    Derived data only. Unlike `repair_orphans` this rewrites no judgement -
    every value it writes is a restatement of a status already on disk.
    """
    board_root = root / ".agents" / "mpi-kanban"
    index_path = board_root / "state" / "index.json"
    if not board_root.joinpath("board.json").is_file() or not index_path.is_file():
        return []
    state = load_json([], index_path, "index.json")
    if not isinstance(state, dict):
        return []  # an index this broken needs a human, not an automatic rewrite
    repaired: list[str] = []
    for field, expected in derive_index_arrays(board_root).items():
        if state.get(field) != expected:
            repaired.append(f"state/index.json {field}: "
                            f"{len(state.get(field) or [])} -> {len(expected)} record(s)")
            state[field] = expected
    if repaired:
        state["updated_at"] = now()
        newline, indent = style(index_path)
        write_json(index_path, state, newline, indent)
    return repaired


def selftest() -> None:
    """One runnable check: the drift is seen, and --fix clears it."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        board_root = root / ".agents" / "mpi-kanban"
        board_root.mkdir(parents=True)
        (board_root / "board.json").write_text(
            '{\n "schema": "mpi-kanban/board/v1",\n "next_id": 1,\n'
            ' "columns": {\n  "todo": [],\n  "doing": [],\n  "done": []\n }\n}\n',
            encoding="utf-8")
        state_root = board_root / "state"

        def record(subdir: str, name: str, body: dict) -> None:
            (state_root / subdir).mkdir(parents=True, exist_ok=True)
            (state_root / subdir / f"{name}.json").write_text(
                json.dumps(body, indent=2) + "\n", encoding="utf-8")

        record("sessions", "live", {"schema": "mpi-kanban/session/v1", "status": "active"})
        record("sessions", "gone", {"schema": "mpi-kanban/session/v1", "status": "closed"})
        record("handoffs", "open1", {"status": "open"})
        record("handoffs", "old", {"status": "resolved"})
        record("messages", "m1", {"status": "acknowledged"})
        claim = {"schema": "mpi-kanban/file-claim/v1", "claim_kind": "write",
                 "owner_role": "implementer", "paths": ["a.py"]}
        record("files", "held", dict(claim, status="claimed",
               owner_session=".agents/mpi-kanban/state/sessions/live.json"))
        record("files", "orphan", dict(claim, status="claimed",
               owner_session=".agents/mpi-kanban/state/sessions/gone.json"))
        record("files", "pending", dict(claim, status="needs_review",
               owner_session=".agents/mpi-kanban/state/sessions/live.json"))
        (state_root / "index.json").write_text(json.dumps({
            "schema": "mpi-kanban/state-index/v1",
            "board": ".agents/mpi-kanban/board.json",
            "active_sessions": [".agents/mpi-kanban/state/sessions/gone.json"],
            "active_tasks": [],
            "active_file_claims": [],
            "pending_file_states": [],
            # the same record twice: extra and missing both come back empty for it
            "open_messages": [".agents/mpi-kanban/state/messages/m1.json"] * 2,
            # a whole record inlined, the shape Cubric-Vision's index had drifted into
            "active_handoffs": [{"id": "old", "status": "resolved",
                                 "path": ".agents/mpi-kanban/state/handoffs/old.json"}],
        }, indent=2) + "\n", encoding="utf-8")

        errors = validate_board(root)
        joined = "\n".join(errors)
        assert "active_sessions lists 1" in joined, joined      # closed, still listed
        assert "active_sessions is missing 1" in joined, joined  # active, not listed
        assert "active_file_claims is missing 2" in joined, joined
        assert "pending_file_states is missing 1" in joined, joined
        assert "open_messages lists 1 record(s) twice" in joined, joined
        assert "open_messages is missing" not in joined, "the duplicate hides nothing else"
        assert "active_handoffs is missing 1" in joined, joined
        # the inlined object is still read far enough to be judged on its status
        assert "active_handoffs has 1 entry/entries inlined as objects" in joined, joined
        assert "active_handoffs lists 1" in joined, joined
        assert sum("locked out of its own card" in e for e in errors) == 1, joined

        repaired = repair_state_index(root)
        assert len(repaired) == 5, repaired
        left = [e for e in validate_board(root) if "index.json" in e]
        assert left == [], left
        rewritten = json.loads((state_root / "index.json").read_text(encoding="utf-8"))
        assert all(isinstance(v, str) for v in rewritten["active_handoffs"]), "not normalised"
        # the repair restates statuses; it never silences the claim rule
        assert any("locked out" in e for e in validate_board(root))

        # an index whose arrays are already right is not rewritten at all
        assert repair_state_index(root) == []
    print("validate_board selftest: OK")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--fix", action="store_true",
                        help="list orphaned task folders back on the board and reconcile "
                             "state/index.json, then validate")
    parser.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    args = parser.parse_args(argv[1:])
    if args.selftest:
        selftest()
        return 0
    root = Path(args.project_root).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    if args.fix:
        for line in repair_orphans(root) + repair_state_index(root) or ["nothing to repair"]:
            print(line)
    board_errors = validate_board(root)
    if board_errors:
        print(f"Board validation FAILED ({root}):", file=sys.stderr)
        for err in board_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    if not (root / ".agents" / "mpi-kanban" / "board.json").exists():
        print("No .agents/mpi-kanban/board.json; nothing to validate.")
        return 0
    print("Board validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
