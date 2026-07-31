"""Validate a live Mpi-Kanban JSON task board.

Usage:

    python validate_board.py [project-root]

`project-root` defaults to the current directory. The board is expected at
`<project-root>/.agents/mpi-kanban/board.json`; a project with no board is not
an error. Exits 0 when the board is consistent, 1 with one line per violation.

This ships with the `mpi-lib` skill so any project can check its own board.
The pack's own `scripts/validate_plugin.py` imports this module instead of
keeping a second copy of the rules, which also makes the maturity enum below
the single code-level source of truth.
"""
from __future__ import annotations

import json
import re
import sys
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
UNRESOLVED_COORDINATION_STATUSES = {
    "needs_review",
    "needs_verification",
    "needs_integration",
}


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

    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
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
