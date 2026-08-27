#!/usr/bin/env python3
"""Create or move a task card as ONE command, instead of a six-step recipe.

A card create is four file writes: the task folder, `task.json`, the id inserted
into a `board.json` column, and a line in each of two event logs. As prose in
`task-board-ops/mutate.md` an agent performed them one at a time -- and twice in
one hour on 2026-08-27, in two different repos, an agent stopped after the second
one. That leaves a card that exists on disk, owns an id nobody else can take, and
is invisible to the VS Code extension, to `board_server.py`, and to everything
else that reads `board.json`. Nothing errors: `next_id` has already moved, so no
later create collides. The only symptom is a human saying the board is empty.

A move has the same shape and the same failure: `board.json` says `doing` while
the card says `todo`. `validate_board.py` has carried a rule for that mismatch
from the start, which is evidence it happens.

So the writes stop being steps an agent can stop between. Either the whole card
lands or the folder is removed again, the timestamps come from the clock rather
than from an agent typing a plausible-looking one, and `validate_board()` runs
before this exits.

Usage:

    python task_ops.py create --title "Short title" [--description "..."]
                             [--column todo] [--maturity idea] [--status active]
                             [--position top|bottom] [--actor claude] [--root .]
    python task_ops.py move MPI-42 --to doing [--maturity validating]
                             [--reason "..."] [--actor claude] [--root .]

Run self-check:  python task_ops.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_board import (  # noqa: E402
    TASK_COLUMNS,
    TASK_MATURITY_BY_COLUMN,
    append_event,
    now,
    repair_orphans,
    style,
    validate_board,
    write_json,
)

BOARD_DIR = (".agents", "mpi-kanban")
TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "task.json"
DEFAULT_MATURITY = {"todo": "planned", "doing": "in-progress", "done": "complete"}
REQUIRED_LINK = {"doing": "checklist", "done": "validation"}  # the validator's own rule
MAX_ATTEMPTS = 10  # every loser retries at the same free id, so this must exceed the herd


class Failure(Exception):
    """Something the caller has to decide about. Printed, not traced."""


def load(path: Path) -> dict:
    """`utf-8-sig` because MPI repos carry mixed encodings."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise Failure(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise Failure(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise Failure(f"{path} must hold a JSON object")
    return data


def event(kind: str, task_id: str, stamp: str, actor: str, **extra) -> dict:
    return {"schema": "mpi-kanban/event/v1", "type": kind, "id": task_id,
            "at": stamp, "actor": actor, **extra}


def coherent(column: str, maturity: str | None) -> str:
    """The maturity to write. Explicit and wrong is an error; absent is a default."""
    if column not in TASK_COLUMNS:
        raise Failure(f"column must be one of {', '.join(TASK_COLUMNS)}, not {column!r}")
    if maturity is None:
        return DEFAULT_MATURITY[column]
    if maturity not in TASK_MATURITY_BY_COLUMN[column]:
        allowed = ", ".join(sorted(TASK_MATURITY_BY_COLUMN[column]))
        raise Failure(f"maturity {maturity!r} is invalid for column {column!r}; use one of: {allowed}")
    return maturity


def paths(root: Path) -> tuple[Path, Path, Path]:
    board_root = root.joinpath(*BOARD_DIR)
    board_path = board_root / "board.json"
    if not board_path.is_file():
        raise Failure(f"no board at {board_path} - run /mpi-init in that project")
    return board_root, board_path, board_root / "tasks"


def create(root: Path, title: str, description: str, column: str, maturity: str | None,
           status: str, position: str, actor: str) -> str:
    board_root, board_path, tasks_root = paths(root)
    maturity = coherent(column, maturity)
    newline, indent = style(board_path)
    stamp = now()

    # The mkdir IS the id lock: exactly one agent wins it, every other raises.
    # Never `exist_ok=True` here - that hands the same id to both.
    candidate = max(int(load(board_path).get("next_id") or 1), 1)
    folder = None
    for _ in range(MAX_ATTEMPTS):
        try:
            folder = tasks_root / f"MPI-{candidate}"
            folder.mkdir(parents=True)
            break
        except FileExistsError:
            folder = None
            candidate = max(int(load(board_path).get("next_id") or 1), candidate + 1)
    if folder is None:
        raise Failure(f"could not claim a task id after {MAX_ATTEMPTS} tries - board is contended")
    task_id = folder.name

    try:
        card = load(TEMPLATE)
        card.update(id=task_id, title=title, description=description, column=column,
                    maturity=maturity, status=status, created_at=stamp, updated_at=stamp)
        write_json(folder / "task.json", card, newline, indent, exclusive=True)
        # A card born straight into `doing` or `done` needs that column's linked
        # file to exist, so it is seeded here rather than left to fail validation.
        key = REQUIRED_LINK.get(column)
        rel = (card.get("links") or {}).get(key) if key else None
        if isinstance(rel, str):
            (folder / rel).write_text(f"# {task_id} {key.capitalize()}\n", encoding="utf-8")
        board = load(board_path)  # re-read: never write back a board read before the mkdir
        ids = board.setdefault("columns", {}).setdefault(column, [])
        ids.append(task_id) if position == "bottom" else ids.insert(0, task_id)
        board["next_id"] = max(int(board.get("next_id") or 1), candidate + 1)
        write_json(board_path, board, newline, indent)
    except Exception:
        # Before this point nothing outside the folder has changed, so removing it
        # leaves no trace. After it the card is on the board and visible, and the
        # worst that remains is a missing event line - which is history, not a card.
        shutil.rmtree(folder, ignore_errors=True)
        raise

    record = event("task.created", task_id, stamp, actor, column=column, title=title)
    append_event(board_root / "events.jsonl", record, newline)
    append_event(folder / "events.jsonl", record, newline)
    return task_id


def move(root: Path, task_id: str, to_column: str, maturity: str | None,
         reason: str, actor: str) -> str:
    board_root, board_path, tasks_root = paths(root)
    if to_column not in TASK_COLUMNS:
        raise Failure(f"--to must be one of {', '.join(TASK_COLUMNS)}, not {to_column!r}")
    newline, indent = style(board_path)
    stamp = now()

    board = load(board_path)
    columns = board.setdefault("columns", {})
    holding = [name for name in TASK_COLUMNS if task_id in (columns.get(name) or [])]
    if len(holding) != 1:
        where = ", ".join(holding) or "no column"
        raise Failure(f"{task_id} must be in exactly one column, found it in {where}")
    from_column = holding[0]

    card_path = tasks_root / task_id / "task.json"
    card = load(card_path)
    if maturity is None and card.get("maturity") in TASK_MATURITY_BY_COLUMN[to_column]:
        maturity = card["maturity"]  # a legal value survives the move
    maturity = coherent(to_column, maturity)

    # Refuse BEFORE writing anything. `doing` needs a checklist and `done` needs
    # validation evidence, so making the move first and reporting after would be
    # this script producing the very half-state it exists to prevent.
    key = REQUIRED_LINK.get(to_column)
    rel = (card.get("links") or {}).get(key) if key else None
    if isinstance(rel, str) and not (tasks_root / task_id / rel).exists():
        raise Failure(f"{task_id} cannot move to {to_column} until {rel} exists - "
                      f"write it, then repeat this command")

    columns[from_column].remove(task_id)
    columns.setdefault(to_column, []).insert(0, task_id)
    card.update(column=to_column, maturity=maturity, updated_at=stamp)
    if to_column == "done" and card.get("status") == "active":
        card["status"] = "done"  # else the board fails its own validator

    write_json(card_path, card, newline, indent)
    write_json(board_path, board, newline, indent)
    record = event("task.moved", task_id, stamp, actor, **{"from": from_column, "to": to_column})
    if reason:
        record["reason"] = reason
    append_event(board_root / "events.jsonl", record, newline)
    append_event(tasks_root / task_id / "events.jsonl", record, newline)
    return task_id


def report(root: Path) -> int:
    """The check the create path could finish without ever running."""
    errors = validate_board(root)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    if errors:
        print("Board validation FAILED. Repair with: "
              "python validate_board.py --fix", file=sys.stderr)
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--actor", default="claude")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("create", help="create a card and put it on the board")
    new.add_argument("--title", required=True)
    new.add_argument("--description", default="")
    new.add_argument("--column", default="todo", choices=TASK_COLUMNS)
    new.add_argument("--maturity", default=None, help="default: the column's own default")
    new.add_argument("--status", default="active")
    new.add_argument("--position", default="top", choices=("top", "bottom"))

    shift = sub.add_parser("move", help="move a card between columns")
    shift.add_argument("task_id")
    shift.add_argument("--to", required=True, choices=TASK_COLUMNS)
    shift.add_argument("--maturity", default=None, help="default: reconciled from the column")
    shift.add_argument("--reason", default="")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.command == "create":
            task_id = create(root, args.title, args.description, args.column,
                             args.maturity, args.status, args.position, args.actor)
            print(f"Created {task_id} in {args.column}")
        else:
            move(root, args.task_id, args.to, args.maturity, args.reason, args.actor)
            print(f"Moved {args.task_id} to {args.to}")
    except Failure as exc:
        print(f"task_ops: {exc}", file=sys.stderr)
        return 1
    return report(root)


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        board_root = root.joinpath(*BOARD_DIR)
        board_root.mkdir(parents=True)
        # CRLF and indent=1, the shape of this repo's own board.
        (board_root / "board.json").write_bytes(
            ('{\r\n "schema": "mpi-kanban/board/v1",\r\n "next_id": 7,\r\n'
             ' "columns": {\r\n  "todo": [],\r\n  "doing": [],\r\n  "done": []\r\n }\r\n}\r\n'
             ).encode("utf-8"))

        task_id = create(root, "First", "", "todo", None, "active", "top", "claude")
        assert task_id == "MPI-7", task_id
        board = load(board_root / "board.json")
        assert board["columns"]["todo"] == ["MPI-7"], "the id must be ON the board"
        assert board["next_id"] == 8
        card = load(board_root / "tasks" / task_id / "task.json")
        assert card["column"] == "todo" and card["maturity"] == "planned"
        # Not "does it end in :00" - an offset like +01:00 does, which is why a hook
        # rejecting that suffix would have blocked correct writes. Read from a clock.
        drift = datetime.fromisoformat(card["created_at"]) - datetime.now().astimezone()
        assert abs(drift.total_seconds()) < 60, "the timestamp did not come from a clock"
        for log in (board_root / "events.jsonl", board_root / "tasks" / task_id / "events.jsonl"):
            assert "task.created" in log.read_text(encoding="utf-8")
        raw = (board_root / "board.json").read_bytes()
        assert b"\r\n" in raw and b'\r\n "schema"' in raw, "formatting was not preserved"
        assert validate_board(root) == []

        # a second create takes the next id, and does not disturb the first
        second = create(root, "Second", "", "todo", "idea", "active", "bottom", "claude")
        assert second == "MPI-8"
        assert load(board_root / "board.json")["columns"]["todo"] == ["MPI-7", "MPI-8"]

        # a card created straight into doing is valid on arrival
        third = create(root, "Third", "", "doing", None, "active", "top", "claude")
        assert (board_root / "tasks" / third / "checklist.md").is_file()
        assert validate_board(root) == []

        # a column whose linked file is missing is refused before anything is written
        try:
            move(root, task_id, "doing", None, "", "claude")
        except Failure as exc:
            assert "checklist.md" in str(exc)
            assert task_id not in load(board_root / "board.json")["columns"]["doing"]
        else:
            raise AssertionError("moving to doing without a checklist must be refused")

        # move reconciles maturity, status, and both logs
        folder = board_root / "tasks" / task_id
        (folder / "checklist.md").write_text(f"# {task_id} Checklist\n", encoding="utf-8")
        (folder / "validation.md").write_text(f"# {task_id} Validation\n", encoding="utf-8")
        move(root, task_id, "doing", None, "picked up", "claude")
        board = load(board_root / "board.json")
        assert board["columns"]["doing"] == ["MPI-7", third]
        assert board["columns"]["todo"] == ["MPI-8"]
        assert load(board_root / "tasks" / task_id / "task.json")["maturity"] == "in-progress"
        move(root, task_id, "done", None, "", "claude")
        card = load(board_root / "tasks" / task_id / "task.json")
        assert card["maturity"] == "complete" and card["status"] == "done"
        assert validate_board(root) == []

        # --fix puts back a card whose create stopped before the board write
        board = load(board_root / "board.json")
        board["columns"]["todo"].remove("MPI-8")
        write_json(board_root / "board.json", board, "\r\n", 1)
        assert any("orphan" in err for err in validate_board(root)), "the orphan must be seen"
        assert repair_orphans(root) == ["listed orphan MPI-8 in todo"]
        assert load(board_root / "board.json")["columns"]["todo"] == ["MPI-8"]
        assert validate_board(root) == []
        assert repair_orphans(root) == [], "a second --fix must be a no-op"
        created = [line for line in (board_root / "events.jsonl").read_text(
            encoding="utf-8").splitlines() if '"MPI-8"' in line and "task.created" in line]
        assert len(created) == 1, "the repair must not duplicate an existing event"

        # the failure modes report rather than half-write
        for bad in (lambda: coherent("doing", "idea"), lambda: coherent("nope", None)):
            try:
                bad()
            except Failure:
                pass
            else:
                raise AssertionError("an invalid maturity/column must not be written")
        try:
            move(root, "MPI-999", "doing", None, "", "claude")
        except Failure as exc:
            assert "exactly one column" in str(exc)
        else:
            raise AssertionError("moving an unlisted card must fail")

    print("task_ops selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        raise SystemExit(main())
