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
    python task_ops.py archive MPI-7 MPI-9 | --all-done [--reason "..."] [--root .]
    python task_ops.py release [--session <claude-session-id>] [--status complete]
                             [--root .]
    python task_ops.py commit-card MPI-42 [MPI-43 ...] -m "subject" [--root .]

`commit-card` commits those cards' folders plus ONLY their own entries in
`board.json` and the root `events.jsonl`, through a private index, so a peer's
uncommitted board moves stay out of the commit. It never pushes.

`release` hands back every file claim a session holds - by default this one,
read from CLAUDE_CODE_SESSION_ID - and reconciles `state/index.json`.

Run self-check:  python task_ops.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_board import (  # noqa: E402
    FILE_CLAIM_STATUSES,
    TASK_COLUMNS,
    TASK_MATURITY_BY_COLUMN,
    append_event,
    load_json,
    now,
    repair_orphans,
    repair_state_index,
    set_claim_status,
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

    # `doing` needs a checklist: seed a header-only one, as `create` does, and
    # let beginImplementation derive the items once the card is in `doing`.
    # Refusing here deadlocked that recipe (MPI-48): it writes the checklist
    # AFTER the move, and guard-card blocks that write while nothing is in doing.
    # `done` needs validation EVIDENCE, which a stub would fake - so refuse
    # BEFORE writing anything rather than produce the half-state this prevents.
    key = REQUIRED_LINK.get(to_column)
    rel = (card.get("links") or {}).get(key) if key else None
    if isinstance(rel, str) and to_column == "doing" and not (tasks_root / task_id / rel).exists():
        (tasks_root / task_id / rel).write_text(f"# {task_id} Checklist\n", encoding="utf-8")
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


def drop_from_column(raw: str, column: str, drop: set[str]) -> str | None:
    """`raw` with `drop` removed from one column's array, every other byte kept.

    A JSON round-trip would reflow a board some other tool formatted; this edits
    only the inside of that one array, reusing its own separator. Returns None
    when the array cannot be found, so the caller falls back to a round-trip.
    """
    match = re.search(rf'"{column}"\s*:\s*\[', raw)
    if not match:
        return None
    start = match.end()
    end = raw.find("]", start)  # task ids never contain "]"
    inner = raw[start:end]
    items = list(re.finditer(r'"([^"]*)"', inner))
    if not items:
        return raw
    prefix, suffix = inner[:items[0].start()], inner[items[-1].end():]
    sep = inner[items[0].end():items[1].start()] if len(items) > 1 else ", "
    kept = [item.group(0) for item in items if item.group(1) not in drop]
    return raw[:start] + (prefix + sep.join(kept) + suffix if kept else "") + raw[end:]


def archive(root: Path, ids: list[str], all_done: bool, reason: str, actor: str) -> list[str]:
    """Take done cards off the board and leave their folders where they are.

    Moving `tasks/<id>/` breaks every doc, commit message and memory note that
    links into it; dropping the id alone made `--fix` re-list it as an orphan.
    `status: "archived"` is the marker the orphan check and repair skip. It is
    an existing field's value, not a new field, so the board contract holds.
    Cards first, board second: a stop in between leaves listed archived cards,
    which the validator names and a rerun finishes.
    """
    board_root, board_path, tasks_root = paths(root)
    newline, indent = style(board_path)
    stamp = now()
    raw_bytes = board_path.read_bytes()
    bom = raw_bytes.startswith(b"\xef\xbb\xbf")
    raw = raw_bytes.decode("utf-8-sig")
    board = json.loads(raw)
    columns = board.get("columns") or {}
    done = list(columns.get("done") or [])

    targets = done if all_done else list(dict.fromkeys(ids))
    if not targets:
        raise Failure("nothing to archive - name card ids or pass --all-done")
    for task_id in targets:  # refuse before writing anything
        held = [name for name in TASK_COLUMNS if task_id in (columns.get(name) or [])]
        if held != ["done"]:
            raise Failure(f"{task_id} is in {', '.join(held) or 'no column'}, not done; "
                          "only done cards archive")
        load(tasks_root / task_id / "task.json")

    lines = []
    for task_id in targets:
        card_path = tasks_root / task_id / "task.json"
        card = load(card_path)
        card.update(status="archived", updated_at=stamp)
        card_newline, card_indent = style(card_path)
        write_json(card_path, card, card_newline, card_indent)
        record = event("task.archived", task_id, stamp, actor, column="done", folder="kept")
        if reason:
            record["reason"] = reason
        append_event(tasks_root / task_id / "events.jsonl", record, newline)
        lines.append(record)

    columns["done"] = [task_id for task_id in done if task_id not in set(targets)]
    edited = drop_from_column(raw, "done", set(targets))
    if edited is not None and json.loads(edited) == board:
        board_path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + edited.encode("utf-8"))
    else:
        write_json(board_path, board, newline, indent)
    body = "".join((json.dumps(r, ensure_ascii=False) + "\n").replace("\n", newline) for r in lines)
    with open(board_root / "events.jsonl", "ab") as handle:  # one write for the whole batch
        handle.write(body.encode("utf-8"))
    return targets


def release(root: Path, session_id: str, status: str) -> list[str]:
    """Hand back every file claim `session_id` still holds. Returns the records released.

    `mpi-handoff` never did this, so a handed-off window kept its claims: the
    next session was locked out of its own card (MPI-36, 2026-09-21), and a
    window the user returns to weeks later renews its heartbeat on its first
    tool call, which re-arms every claim it ever held. Releasing is two writes
    per claim - the record, then the index - the shape an agent stops between.
    Ownership is matched the way `guard-claim` matches it.
    """
    board_root, _, _ = paths(root)
    claims_root = board_root / "state" / "files"
    released: list[str] = []
    for record_path in sorted(claims_root.glob("*.json")) if claims_root.is_dir() else []:
        record = load_json([], record_path, record_path.name)
        if not isinstance(record, dict) or record.get("status") != "claimed":
            continue
        owner_path = record.get("owner_session")
        if not isinstance(owner_path, str) or not owner_path:
            continue
        owner = load_json([], root / owner_path, owner_path)
        if Path(owner_path).name == f"{session_id}.json" or (
                isinstance(owner, dict) and owner.get("claude_session_id") == session_id):
            set_claim_status(record_path, record, status, "claim_released")
            released.append(record_path.name)
    if released:
        repair_state_index(root)
    return released


def git(top: Path, *args: str, data: bytes | None = None, env: dict | None = None) -> bytes:
    done = subprocess.run(["git", *args], cwd=top, input=data, capture_output=True, env=env)
    if done.returncode:
        raise Failure(f"git {' '.join(args[:3])}: {done.stderr.decode('utf-8', 'replace').strip()}")
    return done.stdout


def put_in_column(raw: str, column: str, task_id: str) -> str | None:
    """`raw` with `task_id` first in one column's array, every other byte kept."""
    match = re.search(rf'"{column}"\s*:\s*\[', raw)
    if not match:
        return None
    start = match.end()
    end = raw.find("]", start)
    inner = raw[start:end]
    items = list(re.finditer(r'"([^"]*)"', inner))
    quoted = f'"{task_id}"'
    if not items:
        return raw[:start] + quoted + raw[end:]
    if len(items) > 1:
        sep = inner[items[0].end():items[1].start()]
    else:
        lead = inner[:items[0].start()]
        sep = "," + lead if "\n" in lead else ", "
    at = start + items[0].start()
    return raw[:at] + quoted + sep + raw[at:]


def commit_card(root: Path, ids: list[str], message: str) -> str | None:
    """Commit these cards and nothing a peer left uncommitted on the same board.

    `git commit --only board.json` publishes every other session's uncommitted
    move along with yours, and the root `events.jsonl` can carry a peer's whole
    rewrite. So the two shared files are built as HEAD + only these cards'
    entries, the card folders are taken whole from disk, and the commit is
    made through a PRIVATE index so nothing a peer staged can ride along
    (Cubric-Vision, 2026-09; the traps are each recorded where they bite).
    Returns the new commit, or None when there was nothing to commit.
    """
    board_root, board_path, tasks_root = paths(root)
    if not ids:
        raise Failure("name at least one card id")
    top = Path(git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip())
    rel = lambda p: p.resolve().relative_to(top.resolve()).as_posix()  # noqa: E731
    board_rel, events_rel = rel(board_path), rel(board_root / "events.jsonl")
    if subprocess.run(["git", "check-ignore", "-q", board_rel], cwd=top).returncode == 0:
        raise Failure(f"{board_rel} is ignored by git here, so there is no board to commit")
    ref = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=top, capture_output=True)
    if ref.returncode:
        raise Failure("HEAD is detached - check out a branch first")
    ref_name = ref.stdout.decode("utf-8").strip()
    head = git(top, "rev-parse", "HEAD").decode("utf-8").strip()

    def at_head(path: str) -> bytes | None:
        shown = subprocess.run(["git", "cat-file", "blob", f"{head}:{path}"], cwd=top,
                               capture_output=True)
        return shown.stdout if shown.returncode == 0 else None

    def blob(data: bytes) -> str:  # --no-filters: autocrlf would re-EOL a peer's lines
        sha = git(top, "hash-object", "-w", "--no-filters", "--stdin", data=data).decode().strip()
        if git(top, "cat-file", "blob", sha) != data:
            raise Failure("git stored different bytes than were built - nothing was committed")
        return sha

    # board.json: HEAD text, each card moved to the column it holds on disk.
    disk = load(board_path)
    head_board = at_head(board_rel)
    if head_board is None:
        new_board = board_path.read_bytes()  # the board's first commit is all of it
    else:
        text = head_board.decode("utf-8-sig")
        bom = head_board[:3] if head_board.startswith(b"\xef\xbb\xbf") else b""
        expected = json.loads(text)
        known = {i for col in (expected.get("columns") or {}).values() for i in col}
        for task_id in ids:
            target = [c for c, col in (disk.get("columns") or {}).items() if task_id in col]
            for column in list((expected.get("columns") or {})):
                if task_id in expected["columns"][column]:
                    text = drop_from_column(text, column, {task_id})
                    expected["columns"][column].remove(task_id)
            if target:
                edited = put_in_column(text, target[0], task_id)
                if edited is None:
                    raise Failure(f"HEAD's {board_rel} has no {target[0]!r} column")
                text = edited
                expected["columns"].setdefault(target[0], []).insert(0, task_id)
            number = re.fullmatch(r"MPI-(\d+)", task_id)
            if task_id not in known and number and int(number[1]) >= int(expected.get("next_id") or 1):
                expected["next_id"] = int(number[1]) + 1
                text = re.sub(r'("next_id"\s*:\s*)\d+', rf"\g<1>{expected['next_id']}", text, count=1)
        if json.loads(text) != expected:
            raise Failure(f"could not edit {board_rel} cleanly - nothing was committed")
        new_board = bom + text.encode("utf-8")

    # events.jsonl: HEAD bytes, then these cards' disk lines HEAD lacks, in HEAD's EOL.
    head_events = at_head(events_rel) or b""
    eol = b"\r\n" if b"\r\n" in head_events else b"\n"
    have = Counter(line.strip() for line in head_events.splitlines())
    wanted = set(ids)
    added = []
    events_path = board_root / "events.jsonl"
    for line in (events_path.read_bytes().splitlines() if events_path.is_file() else []):
        line = line.strip()
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict) or record.get("id") not in wanted:
            continue
        if have[line]:
            have[line] -= 1
        else:
            added.append(line)
    new_events = head_events
    if added:
        if new_events and not new_events.endswith(b"\n"):
            new_events += eol
        new_events += eol.join(added) + eol

    # The card folders are wholly this session's: every file on disk, as is.
    modes = {}  # an executable bit at HEAD survives; everything else is 100644
    for line in git(top, "ls-tree", "-r", head, "--", board_rel, events_rel,
                    *(rel(tasks_root / i) for i in ids)).decode("utf-8").splitlines():
        meta, path = line.split("\t", 1)
        modes[path] = meta.split()[0]
    entries: dict[str, str | None] = {board_rel: blob(new_board)}
    if added:
        entries[events_rel] = blob(new_events)
    for task_id in ids:
        folder = tasks_root / task_id
        if not folder.is_dir():
            raise Failure(f"no card folder {rel(folder)}")
        for file in sorted(p for p in folder.rglob("*") if p.is_file()):
            entries[rel(file)] = git(top, "hash-object", "-w", f"--path={rel(file)}",
                                     str(file)).decode().strip()
        for gone in [p for p in modes if p.startswith(rel(folder) + "/")]:
            entries.setdefault(gone, None)  # tracked at HEAD, deleted on disk

    staged = git(top, "diff", "--cached", "--name-only", "--", *entries).decode().split()
    if staged:  # BEFORE update-ref: afterwards every path of mine reads as staged
        raise Failure("another session has these staged in the shared index: "
                      + ", ".join(staged) + " - nothing was committed")

    with tempfile.TemporaryDirectory() as scratch:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(scratch) / "index")}
        git(top, "read-tree", head, env=env)
        for path, sha in entries.items():
            if sha is None:
                git(top, "update-index", "--force-remove", "--", path, env=env)
            else:
                git(top, "update-index", "--add", "--cacheinfo", f"{modes.get(path, '100644')},{sha},{path}", env=env)
        tree = git(top, "write-tree", env=env).decode().strip()
    if tree == git(top, "rev-parse", f"{head}^{{tree}}").decode().strip():
        return None
    commit = git(top, "commit-tree", tree, "-p", head, "-F", "-",
                 data=message.encode("utf-8")).decode().strip()
    git(top, "update-ref", "-m", f"commit-card: {message.splitlines()[0]}", ref_name, commit, head)

    # Point the SHARED index at the commit for exactly these paths, or git status
    # shows each one as a staged revert of it. --add: new files are not in it yet.
    for path, sha in entries.items():
        if sha is None:
            git(top, "update-index", "--force-remove", "--", path)
        else:
            git(top, "update-index", "--add", "--cacheinfo", f"{modes.get(path, '100644')},{sha},{path}")
    return commit


def report(root: Path) -> int:
    """The check the create path could finish without ever running.

    The derived index is repaired first: session-start writes a session record
    but never its `state/index.json` line (an index write would race other
    windows), so without this every new session's create or move did its work
    and then exited 1 - and a model that trusts the exit code creates the card
    again. The repair only restates statuses already on disk.
    """
    repair_state_index(root)
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

    shelve = sub.add_parser("archive", help="take done cards off the board, folders stay")
    shelve.add_argument("task_ids", nargs="*")
    shelve.add_argument("--all-done", action="store_true", help="every card in done")
    shelve.add_argument("--reason", default="")

    free = sub.add_parser("release", help="release every file claim a session holds")
    free.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID"),
                      help="default: this session, from CLAUDE_CODE_SESSION_ID")
    free.add_argument("--status", default="complete",
                      choices=sorted(FILE_CLAIM_STATUSES - {"claimed", "stale"}))
    # `mutate.md` put --root AFTER the subcommand and argparse exited 2 on it,
    # one wasted round trip per agent; SUPPRESS keeps the top-level value.
    land = sub.add_parser("commit-card", help="commit these cards and only their board entries")
    land.add_argument("task_ids", nargs="+")
    land.add_argument("-m", "--message", required=True)
    for each in (new, shift, shelve, free, land):
        each.add_argument("--root", default=argparse.SUPPRESS)
        each.add_argument("--actor", default=argparse.SUPPRESS)

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.command == "create":
            task_id = create(root, args.title, args.description, args.column,
                             args.maturity, args.status, args.position, args.actor)
            print(f"Created {task_id} in {args.column}")
        elif args.command == "archive":
            if args.task_ids and args.all_done:
                raise Failure("name card ids or pass --all-done, not both")
            done = archive(root, args.task_ids, args.all_done, args.reason, args.actor)
            print(f"Archived {len(done)} card(s) in place; folders kept under .agents/mpi-kanban/tasks/")
        elif args.command == "release":
            if not args.session:
                raise Failure("no session id - pass --session <claude-session-id>")
            names = release(root, args.session, args.status)
            print(f"Released {len(names)} claim(s) as {args.status}"
                  + (": " + ", ".join(names) if names else ""))
        elif args.command == "commit-card":
            commit = commit_card(root, args.task_ids, args.message)
            print(f"Committed {', '.join(args.task_ids)} as {commit[:10]}" if commit
                  else "Nothing to commit for " + ", ".join(args.task_ids))
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

        # done without validation evidence is refused before anything is written
        folder = board_root / "tasks" / task_id
        try:
            move(root, task_id, "done", None, "", "claude")
        except Failure as exc:
            assert "validation.md" in str(exc)
            assert task_id not in load(board_root / "board.json")["columns"]["done"]
        else:
            raise AssertionError("moving to done without validation.md must be refused")

        # a todo card with no checklist reaches doing in ONE command (MPI-48),
        # and the move reconciles maturity, status, and both logs
        assert not (folder / "checklist.md").exists()
        move(root, task_id, "doing", None, "picked up", "claude")
        assert (folder / "checklist.md").read_text(encoding="utf-8") == f"# {task_id} Checklist\n"
        board = load(board_root / "board.json")
        assert board["columns"]["doing"] == ["MPI-7", third]
        assert board["columns"]["todo"] == ["MPI-8"]
        assert load(board_root / "tasks" / task_id / "task.json")["maturity"] == "in-progress"
        assert validate_board(root) == []
        (folder / "validation.md").write_text(f"# {task_id} Validation\n", encoding="utf-8")
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

        # release hands back only this session's claims, and the index follows.
        # Record names differ from the ids, so ownership must come from
        # claude_session_id - the way guard-claim reads it - not the filename.
        state = board_root / "state"
        (state / "sessions").mkdir(parents=True)
        (state / "files").mkdir()
        rel = ".agents/mpi-kanban/state/"
        for name, sid in (("s1", "me"), ("s2", "peer")):
            write_json(state / "sessions" / f"{name}.json", {
                "schema": "mpi-kanban/session/v1", "status": "active",
                "claude_session_id": sid}, "\n", 2)
            write_json(state / "files" / f"{sid}.json", {
                "schema": "mpi-kanban/file-claim/v1", "status": "claimed", "claim_kind": "write",
                "paths": ["a.py"], "owner_session": f"{rel}sessions/{name}.json"}, "\n", 2)
        write_json(state / "index.json", {
            "schema": "mpi-kanban/state-index/v1", "board": ".agents/mpi-kanban/board.json",
            "active_file_claims": [f"{rel}files/me.json", f"{rel}files/peer.json"]}, "\n", 2)
        assert main(["release", "--root", str(root), "--session", "me"]) == 0, \
            "--root after the subcommand must work, and the board must validate"
        index = load(state / "index.json")
        assert index["active_file_claims"] == [f"{rel}files/peer.json"], index
        assert index["pending_file_states"] == [f"{rel}files/me.json"], index
        mine = load(state / "files" / "me.json")
        assert mine["status"] == "complete" and mine["recent_events"][-1]["event"] == "claim_released"
        assert load(state / "files" / "peer.json")["status"] == "claimed", "a peer's claim is not mine"
        assert release(root, "me", "complete") == [], "nothing left to release"

        # A new session: session-start writes the record but never the index
        # line, so a create that worked must still exit 0 (MPI-46).
        write_json(state / "sessions" / "s3.json", {
            "schema": "mpi-kanban/session/v1", "status": "active",
            "claude_session_id": "fresh"}, "\n", 2)
        assert validate_board(root), "the unlisted session must be seen first"
        assert main(["create", "--root", str(root), "--title", "Fresh"]) == 0, \
            "a create in a new session must not report failure"
        assert f"{rel}sessions/s3.json" in load(state / "index.json")["active_sessions"]

    # Archive in place: off the board, folder kept, and NOT an orphan to --fix.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        board_root = root.joinpath(*BOARD_DIR)
        board_root.mkdir(parents=True)
        board_path = board_root / "board.json"
        board_path.write_bytes(
            ('﻿{\r\n  "schema": "mpi-kanban/board/v1",\r\n  "next_id": 1,\r\n'
             '  "columns": {\r\n    "todo": [],\r\n    "doing": [],\r\n    "done": []\r\n  }\r\n}\r\n'
             ).encode("utf-8"))
        made = [create(root, f"Card {n}", "", "todo", None, "active", "top", "claude") for n in range(3)]
        for task_id in made:
            (board_root / "tasks" / task_id / "validation.md").write_text("ok", encoding="utf-8")
            card = load(board_root / "tasks" / task_id / "task.json")
            card.setdefault("links", {})["validation"] = "validation.md"
            write_json(board_root / "tasks" / task_id / "task.json", card, "\r\n", 2)
        move(root, made[0], "done", None, "", "claude")
        move(root, made[1], "done", None, "", "claude")
        try:
            archive(root, [made[2]], False, "", "claude")
            raise AssertionError("a todo card must not archive")
        except Failure:
            pass
        board_path.write_bytes(b"\xef\xbb\xbf" + board_path.read_bytes())
        before = board_path.read_bytes()
        assert archive(root, [], True, "bulk", "claude") == [made[1], made[0]]
        after = board_path.read_bytes()
        assert after.startswith(b"\xef\xbb\xbf") and b"\r\n" in after, "BOM and CRLF kept"
        assert after.replace(b'"done": []', b"") == before.replace(
            f'"done": [\r\n      "{made[1]}",\r\n      "{made[0]}"\r\n    ]'.encode(), b""), \
            "only the done array may change"
        assert load(board_path)["columns"]["done"] == []
        for task_id in made[:2]:
            card = load(board_root / "tasks" / task_id / "task.json")
            assert card["status"] == "archived" and card["column"] == "done"
            assert "task.archived" in (board_root / "tasks" / task_id / "events.jsonl").read_text("utf-8")
        assert (board_root / "events.jsonl").read_text("utf-8").count("task.archived") == 2
        assert validate_board(root) == [], validate_board(root)
        assert repair_orphans(root) == [], "--fix must leave archived cards off the board"

        # The VS Code extension's Delete leaves the same shape with status "deleted".
        board = load(board_path)
        board["columns"]["todo"].remove(made[2])
        write_json(board_path, board, "\r\n", 2)
        card = load(board_root / "tasks" / made[2] / "task.json")
        card["status"] = "deleted"
        write_json(board_root / "tasks" / made[2] / "task.json", card, "\r\n", 2)
        assert validate_board(root) == [] and repair_orphans(root) == []

    # commit-card (MPI-40): my cards land, a peer's uncommitted board moves do not.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run = lambda *a: git(root, *a)  # noqa: E731
        run("init", "-q", "-b", "main")
        for key, value in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            run("config", key, value)
        board_root = root.joinpath(*BOARD_DIR)
        board_root.mkdir(parents=True)
        board_path = board_root / "board.json"
        board_path.write_bytes(
            ('{\r\n "schema": "mpi-kanban/board/v1",\r\n "next_id": 1,\r\n'
             ' "columns": {\r\n  "todo": [],\r\n  "doing": [],\r\n  "done": []\r\n }\r\n}\r\n'
             ).encode("utf-8"))
        peer = create(root, "Peer", "", "todo", None, "active", "top", "peer")
        mine = create(root, "Mine", "", "todo", None, "active", "top", "me")
        events_path = board_root / "events.jsonl"
        crlf = json.dumps(event("task.updated", peer, now(), "peer")).encode() + b"\r\n"
        events_path.write_bytes(events_path.read_bytes() + crlf)
        run("add", "--", ".agents")
        run("commit", "-q", "-m", "init")
        run("config", "core.autocrlf", "true")  # the filter that re-EOLs a peer's lines
        head_events = run("show", f"HEAD:{events_path.relative_to(root).as_posix()}")

        move(root, peer, "doing", None, "", "peer")  # the peer's move, left uncommitted
        new = create(root, "New", "", "todo", None, "active", "top", "me")
        move(root, mine, "doing", None, "", "me")
        commit = main(["commit-card", new, mine, "-m", "my cards", "--root", str(root)])
        assert commit == 0

        board_rel = board_path.relative_to(root).as_posix()
        committed = run("show", f"HEAD:{board_rel}")
        assert b"\r\n" in committed and b'\r\n "schema"' in committed, "formatting kept"
        columns = json.loads(committed)["columns"]
        assert columns["todo"] == [new, peer] and columns["doing"] == [mine], columns
        assert json.loads(committed)["next_id"] == 4
        events = run("show", f"HEAD:{events_path.relative_to(root).as_posix()}")
        assert events.startswith(head_events), "HEAD's events bytes kept verbatim, CRLF too"
        tail = events[len(head_events):].decode("utf-8")
        assert f'"{new}"' in tail and f'"{mine}"' in tail and f'"{peer}"' not in tail, tail
        tree = run("ls-tree", "-r", "--name-only", "HEAD").decode().split()
        assert f".agents/mpi-kanban/tasks/{new}/task.json" in tree
        assert f".agents/mpi-kanban/tasks/{mine}/checklist.md" in tree
        peer_card = run("show", f"HEAD:.agents/mpi-kanban/tasks/{peer}/task.json")
        assert json.loads(peer_card)["column"] == "todo", "the peer's card was not committed"
        assert run("diff", "--cached", "--name-only") == b"", "shared index left in step"
        leftover = run("status", "--porcelain", "--", f".agents/mpi-kanban/tasks/{new}",
                       f".agents/mpi-kanban/tasks/{mine}")
        assert leftover == b"", leftover
        assert load(board_path)["columns"]["doing"] == [mine, peer], "the peer's move is on disk"
        assert board_rel in run("diff", "--name-only").decode(), "the peer's move still pending"
        assert commit_card(root, [new], "again") is None, "nothing new to commit"

        # a peer mid-commit on a path of mine: refuse before anything moves
        before = run("rev-parse", "HEAD")
        (board_root / "tasks" / mine / "notes.md").write_text("x", encoding="utf-8")
        run("add", "--", f".agents/mpi-kanban/tasks/{mine}/notes.md")
        try:
            commit_card(root, [mine], "clobber")
            raise AssertionError("a path a peer has staged must be refused")
        except Failure as exc:
            assert "staged" in str(exc)
        assert run("rev-parse", "HEAD") == before

        (root / ".gitignore").write_text(".agents/*\n", encoding="utf-8")
        run("rm", "-q", "-r", "--cached", "--", ".agents")
        run("commit", "-q", "-m", "untrack")
        try:
            commit_card(root, [mine], "ignored")
            raise AssertionError("an ignored board must be refused")
        except Failure as exc:
            assert "ignored" in str(exc)

    print("task_ops selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        raise SystemExit(main())
