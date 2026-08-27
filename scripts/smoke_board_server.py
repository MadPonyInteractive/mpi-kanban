#!/usr/bin/env python3
"""Smoke the read-only board server against throwaway projects.

Boots `skills/mpi-lib/scripts/board_server.py` on an ephemeral port with the
registry pointed at a temp file, then drives it over real HTTP. No network, no
dependencies, and it never touches `~/.mpi-kanban/boards.json`.

What it is here to catch: a column that silently loses a card, a repo with no
board taking the whole page down, the path guard on `/api/task/...` letting a
read escape a task folder, and a second repo failing to join a running server --
which is the whole point of one server holding every board.

    python scripts/smoke_board_server.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "mpi-lib" / "scripts"))
import board_server  # noqa: E402

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(("  ok   " if condition else "  FAIL ") + label + (f"  {detail}" if not condition else ""))
    if not condition:
        FAILURES.append(label)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_project(root: Path, columns: dict, cards: dict) -> Path:
    """A project with a board. `cards` maps task id -> task.json dict (or None to omit)."""
    board_dir = root / ".agents" / "mpi-kanban"
    write(board_dir / "board.json", json.dumps(
        {"schema": "mpi-kanban/board/v1", "next_id": 99, "columns": columns}))
    for task_id, card in cards.items():
        if card is None:
            continue
        write(board_dir / "tasks" / task_id / "task.json", json.dumps(card))
    return root


def card(task_id: str, column: str, maturity: str, links: dict | None = None) -> dict:
    return {"schema": "mpi-kanban/task-card/v1", "id": task_id, "title": f"Card {task_id}",
            "description": "body", "column": column, "maturity": maturity,
            "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-02T00:00:00+00:00",
            "links": links or {}}


def fetch(port: int, path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        os.environ["MPI_KANBAN_BOARDS_FILE"] = str(home / "boards.json")

        alpha = make_project(
            home / "alpha",
            {"todo": ["MPI-2"], "doing": ["MPI-1"], "done": []},
            {"MPI-1": card("MPI-1", "doing", "validating",
                           {"checklist": "checklist.md", "plan": "plan.md",
                            "escape": "../../../../board.json", "handoffs": "handoffs/"}),
             "MPI-2": card("MPI-2", "todo", "planned")},
        )
        write(alpha / ".agents/mpi-kanban/tasks/MPI-1/checklist.md",
              "# Checklist\n\n- [x] done one\n- [ ] not yet\n")
        write(alpha / ".agents/mpi-kanban/tasks/MPI-1/plan.md", "PLAN BODY\n")

        # MPI-7 is listed in a column but has no task.json on disk.
        beta = make_project(home / "beta", {"todo": [], "doing": ["MPI-7"], "done": ["MPI-3"]},
                            {"MPI-3": card("MPI-3", "done", "complete")})

        empty = home / "empty"          # a real repo that never ran /mpi-init
        empty.mkdir()

        for root in (alpha, beta, empty):
            board_server.register(root)

        server = board_server.Server(("127.0.0.1", 0), board_server.Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            run_checks(port, home, alpha)
        finally:
            server.shutdown()
            server.server_close()

    print("")
    if FAILURES:
        print(f"{len(FAILURES)} failed: " + ", ".join(FAILURES))
        return 1
    print("board server smoke passed")
    return 0


def run_checks(port: int, home: Path, alpha: Path) -> None:
    print("registry and tabs")
    status, body = fetch(port, "/api/boards")
    boards = json.loads(body)["boards"]
    by_name = {entry["name"]: entry for entry in boards}
    check("lists every registered repo", status == 200 and set(by_name) == {"alpha", "beta", "empty"},
          f"got {sorted(by_name)}")
    check("a repo with no board is reported, not hidden",
          by_name.get("empty", {}).get("ok") is False and by_name["empty"]["error"])
    check("a repo with a board is ok", by_name.get("alpha", {}).get("ok") is True)

    print("board assembly")
    status, body = fetch(port, "/api/board?repo=alpha")
    board = json.loads(body)
    columns = {column["id"]: column["tasks"] for column in board["columns"]}
    check("three columns in order", [c["id"] for c in board["columns"]] == ["todo", "doing", "done"])
    check("cards land in their own column",
          [t["id"] for t in columns["doing"]] == ["MPI-1"] and
          [t["id"] for t in columns["todo"]] == ["MPI-2"])
    doing = columns["doing"][0]
    check("maturity survives", doing.get("maturity") == "validating")
    check("checklist parsed 1 of 2",
          [item["completed"] for item in doing["checklist"]] == [True, False],
          str(doing["checklist"]))

    print("branch label")
    check("a project with no .git carries no branch", board_server.branch(alpha) is None)
    write(alpha / ".git" / "HEAD", "ref: refs/heads/feature/board-server\n")
    check("the branch comes out of .git/HEAD",
          board_server.branch(alpha) == "feature/board-server", str(board_server.branch(alpha)))
    write(alpha / ".git" / "HEAD", "9f3c1a2b4d5e6f708192a3b4c5d6e7f809a1b2c3\n")
    check("a detached head shows its short sha", board_server.branch(alpha) == "9f3c1a2")
    # A linked worktree has a `.git` FILE, not a directory -- the case a naive
    # read of `<root>/.git/HEAD` misses, and the one that matters here, since a
    # worktree is a second checkout with a board of its own.
    tree = home / "tree"
    write(tree / ".git", f"gitdir: {alpha / '.git' / 'worktrees' / 'tree'}\n")
    write(alpha / ".git" / "worktrees" / "tree" / "HEAD", "ref: refs/heads/side\n")
    check("a linked worktree reports its own branch", board_server.branch(tree) == "side",
          str(board_server.branch(tree)))
    write(alpha / ".git" / "HEAD", "ref: refs/heads/main\n")
    status, body = fetch(port, "/api/board?repo=alpha")
    check("the board carries the branch to the page", json.loads(body).get("branch") == "main",
          body[:80])

    print("failure modes stay visible")
    status, body = fetch(port, "/api/board?repo=beta")
    beta = {column["id"]: column["tasks"] for column in json.loads(body)["columns"]}
    check("a missing task.json becomes a stub, not a dropped card",
          len(beta["doing"]) == 1 and beta["doing"][0]["id"] == "MPI-7" and beta["doing"][0].get("error"),
          str(beta["doing"]))
    status, body = fetch(port, "/api/board?repo=empty")
    check("a repo with no board answers ok:false, not a 500",
          status == 200 and json.loads(body)["ok"] is False, f"{status} {body[:80]}")
    status, _ = fetch(port, "/api/board?repo=nope")
    check("an unknown repo is 404", status == 404, str(status))

    print("path guard")
    status, body = fetch(port, "/api/task/alpha/MPI-1/plan")
    check("a declared link is readable", status == 200 and body.strip() == "PLAN BODY", body[:80])
    for label, path in [
        ("an undeclared link is refused", "/api/task/alpha/MPI-1/board.json"),
        ("a link escaping the task folder is refused", "/api/task/alpha/MPI-1/escape"),
        ("a traversal in the link key is refused", "/api/task/alpha/MPI-1/..%2F..%2Fboard.json"),
        ("a traversal in the task id is refused", "/api/task/alpha/..%2F..%2F/plan"),
        ("an unregistered repo is refused", "/api/task/nope/MPI-1/plan"),
    ]:
        status, _ = fetch(port, path)
        check(label, status == 403, str(status))
    status, _ = fetch(port, "/api/task/alpha/MPI-1/handoffs")
    check("a link naming a folder is refused", status == 403, str(status))

    print("joining a running server")
    check("health identifies the server",
          json.loads(fetch(port, "/api/health")[1])["server"] == board_server.SERVER_ID)
    check("probe recognises our own server", board_server.probe(port) == "ours")
    gamma = make_project(home / "gamma", {"todo": ["MPI-5"], "doing": [], "done": []},
                         {"MPI-5": card("MPI-5", "todo", "idea")})
    # The real multi-repo path: the same command, run from a second repo, must
    # join the running server rather than fail on the port.
    check("a second launch registers and exits 0",
          board_server.main([str(gamma), "--port", str(port)]) == 0)
    names = {entry["name"] for entry in json.loads(fetch(port, "/api/boards")[1])["boards"]}
    check("a repo registered mid-run appears with no restart", "gamma" in names, str(sorted(names)))
    status, body = fetch(port, "/api/board")
    check("no ?repo= shows the newest registration", json.loads(body)["repo"] == "gamma", body[:80])

    print("registry hygiene")
    dead = home / "dead"
    dead.mkdir()
    board_server.register(dead)
    dead.rmdir()
    names = {entry["name"] for entry in json.loads(fetch(port, "/api/boards")[1])["boards"]}
    check("a deleted repo drops out of the registry", "dead" not in names, str(sorted(names)))
    check("--forget exits 0", board_server.main([str(home / "beta"), "--forget"]) == 0)
    names = {entry["name"] for entry in json.loads(fetch(port, "/api/boards")[1])["boards"]}
    check("--forget drops a live repo that would otherwise stick", "beta" not in names,
          str(sorted(names)))


if __name__ == "__main__":
    raise SystemExit(main())
