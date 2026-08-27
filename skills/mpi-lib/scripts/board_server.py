#!/usr/bin/env python3
"""Serve every Mpi-Kanban board in the browser, read-only, from one address.

The board is otherwise only visible through the companion VS Code extension.
An agent harness with no webview cannot show it at all, so this serves the same
data over plain HTTP: it works in the Claude Code browser pane and in Chrome or
Edge at the same time, on the same URL.

One server holds every repo, rather than one server per repo on a port you have
to remember:

    ~/.mpi-kanban/boards.json           the registry of project roots

which is machine-global for the same reason the GPU lease is -- a record that
must span repos cannot live inside one. Like the lease it is NOT a coordination
record: no heartbeat, no `index.json` entry, no claim. Nothing here writes to a
board; the only mutable state in this whole script is that one list of paths.

Usage:

    python board_server.py [project-root] [--port 7337]

Same command every time. It registers `project-root` (default: cwd), then either
starts the server or, when one is already up, prints the URL and exits -- so
running it from a second repo joins the board already open in your browser
instead of fighting for the port. The port is pinned and never auto-picked: the
address is a bookmark, and a bookmark that moves is worse than no bookmark.

The page polls, so two browsers on one board agree within about two seconds and
there is no Refresh button to distrust.

Run self-check:  python ../../../scripts/smoke_board_server.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

SERVER_ID = "mpi-kanban-board"
DEFAULT_PORT = 7337
BOARD_DIR = (".agents", "mpi-kanban")
COLUMN_TITLES = {"todo": "To Do", "doing": "Doing", "done": "Done"}
TASK_ID = re.compile(r"^MPI-[1-9][0-9]*$")
CHECKBOX = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s*(.*)$")
TASK_FIELDS = ("id", "title", "description", "column", "maturity", "status",
               "attention", "created_at", "updated_at", "links")
PAGE = Path(__file__).with_name("board.html")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> object | None:
    """Parsed JSON, or None. `utf-8-sig` because MPI repos carry mixed encodings."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


# --- the registry -----------------------------------------------------------

def registry_path() -> Path:
    """Where the list of repos lives. Overridable so the smoke never touches it."""
    override = os.environ.get("MPI_KANBAN_BOARDS_FILE")
    if override:
        return Path(override)
    return Path.home() / ".mpi-kanban" / "boards.json"


def read_registry() -> list[Path]:
    """Registered roots, most recently registered last.

    A root whose directory is gone drops out here. A root that still exists but
    has no board does NOT -- that is a repo waiting on `/mpi-init`, and saying so
    on its tab is more use than making it vanish.
    """
    data = read_json(registry_path())
    roots = data.get("roots", []) if isinstance(data, dict) else []
    return [Path(raw) for raw in roots if isinstance(raw, str) and Path(raw).is_dir()]


def register(root: Path, forget: bool = False) -> None:
    """Add `root` to the registry, moving it to most-recent. Or drop it."""
    # ponytail: read-modify-write, no lock. Two registrations in the same instant
    # can lose one; re-run the command if a repo does not show up. A lock file
    # here would out-weigh the cost of typing the command twice.
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = read_json(path)
    roots = data.get("roots", []) if isinstance(data, dict) else []
    roots = [r for r in roots if isinstance(r, str) and r != str(root)]
    if not forget:
        roots.append(str(root))
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"roots": roots}, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def names(roots: list[Path]) -> dict[str, Path]:
    """Display name -> root. Folder name, with the parent prepended on collision."""
    seen: dict[str, int] = {}
    for root in roots:
        seen[root.name] = seen.get(root.name, 0) + 1
    table: dict[str, Path] = {}
    for root in roots:
        name = root.name if seen[root.name] == 1 else f"{root.parent.name}-{root.name}"
        while name in table:  # ugly beats silently dropping a repo
            name += "-2"
        table[name] = root
    return table


def branch(root: Path) -> str | None:
    """The checked-out branch, read straight out of `.git/HEAD`. None if not a repo.

    A label, not a filter. `.agents/` is gitignored in an adopted project, so the
    board belongs to the WORKING TREE and switching branches does not change a
    single card - the label is there to say which checkout the agent writing
    these cards is standing in. Per-branch boards would need a card field, and
    the board contract is fixed.

    No subprocess: `git rev-parse` on every 2-second poll of every registered
    repo is a lot of process spawns for one line of text.
    """
    git = root / ".git"
    if git.is_file():  # a linked worktree or a submodule: `.git` names the real dir
        try:
            pointer = git.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not pointer.startswith("gitdir:"):
            return None
        git = Path(pointer.split(":", 1)[1].strip())
        if not git.is_absolute():
            git = root / git
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if head.startswith("ref: refs/heads/"):
        return head[len("ref: refs/heads/"):] or None
    return head[:7] or None  # detached: the short sha is the honest answer


# --- reading a board --------------------------------------------------------

def resolve_link(folder: Path, links: object, key: str) -> Path | None:
    """The file `links[key]` names, or None when it escapes the task folder.

    Trust boundary: `key` arrives from the URL. It must name a link the card
    itself declares, and the result must land inside that card's own folder.
    """
    rel = links.get(key) if isinstance(links, dict) else None
    if not isinstance(rel, str) or not rel:
        return None
    try:
        target = (folder / rel).resolve()
        target.relative_to(folder.resolve())
    except (OSError, ValueError):
        return None
    return target


def read_checklist(folder: Path, links: object) -> list[dict]:
    target = resolve_link(folder, links, "checklist")
    if target is None:
        return []
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return []
    items = []
    for line in text.splitlines():
        match = CHECKBOX.match(line)
        if match:
            # ponytail: first line only. A wrapped item loses its continuation;
            # join indented follow-on lines if that ever reads badly.
            items.append({"text": match.group(2).strip(),
                          "completed": match.group(1) != " "})
    return items


def load_task(root: Path, task_id: str, column_id: str) -> dict:
    folder = root.joinpath(*BOARD_DIR, "tasks", task_id)
    card = read_json(folder / "task.json")
    if not isinstance(card, dict):
        # A stub, never a dropped card: a column one entry short reads as work done.
        return {"id": task_id, "title": task_id, "column": column_id, "checklist": [],
                "error": f"{task_id}/task.json is missing or unreadable"}
    task = {field: card[field] for field in TASK_FIELDS if field in card}
    task["id"] = card.get("id") or task_id
    task["checklist"] = read_checklist(folder, card.get("links"))
    return task


def load_board(root: Path, name: str) -> dict:
    board_file = root.joinpath(*BOARD_DIR, "board.json")
    board = read_json(board_file)
    if not isinstance(board, dict):
        return {"repo": name, "root": str(root), "branch": branch(root), "ok": False,
                "columns": [],
                "error": f"No board at {board_file} - run /mpi-init in that project"}
    columns = board.get("columns") if isinstance(board.get("columns"), dict) else {}
    return {
        "repo": name, "root": str(root), "branch": branch(root),
        "ok": True, "generated_at": now(),
        "columns": [
            {"id": column_id, "title": title,
             "tasks": [load_task(root, task_id, column_id)
                       for task_id in (columns.get(column_id) or [])
                       if isinstance(task_id, str)]}
            for column_id, title in COLUMN_TITLES.items()
        ],
    }


def list_boards() -> list[dict]:
    boards = []
    for name, root in names(read_registry()).items():
        board_file = root.joinpath(*BOARD_DIR, "board.json")
        ok = board_file.is_file()
        boards.append({"name": name, "root": str(root), "branch": branch(root), "ok": ok,
                       "error": None if ok else "No board here - run /mpi-init"})
    return boards


# --- the server -------------------------------------------------------------

class Server(ThreadingHTTPServer):
    # `HTTPServer` sets this True, which on Windows does not mean "reuse a dead
    # socket" -- it means a second bind SILENTLY HIJACKS a port that is already
    # serving. That turns the second repo's launch, the whole point of one shared
    # server, into a process that steals the port and then blocks forever. Unix
    # keeps the default, where it only smooths over a restart into TIME_WAIT.
    allow_reuse_address = os.name != "nt"


class Handler(BaseHTTPRequestHandler):
    server_version = "MpiKanbanBoard/1.0"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        if route == "/":
            return self.send_page()
        if route == "/api/health":
            return self.send_json(200, {"server": SERVER_ID})
        if route == "/api/boards":
            return self.send_json(200, {"boards": list_boards()})
        if route == "/api/board":
            return self.send_board(parse_qs(parsed.query).get("repo", [""])[0])
        if route.startswith("/api/task/"):
            return self.send_task_file(route[len("/api/task/"):])
        self.send_json(404, {"error": f"No route {route}"})

    def send_board(self, repo: str) -> None:
        table = names(read_registry())
        if not table:
            return self.send_json(404, {"error": "No repos registered yet"})
        repo = repo or list(table)[-1]  # newest registration is the session you just started
        if repo not in table:
            return self.send_json(404, {"error": f"Unknown repo {repo!r}"})
        self.send_json(200, load_board(table[repo], repo))

    def send_task_file(self, tail: str) -> None:
        parts = [unquote(part) for part in tail.split("/")]
        if len(parts) != 3:
            return self.send_json(404, {"error": "Expected /api/task/<repo>/<id>/<link>"})
        repo, task_id, key = parts
        root = names(read_registry()).get(repo)
        if root is None or not TASK_ID.match(task_id):
            return self.send_json(403, {"error": "Unknown repo or task id"})
        folder = root.joinpath(*BOARD_DIR, "tasks", task_id)
        card = read_json(folder / "task.json")
        target = resolve_link(folder, card.get("links") if isinstance(card, dict) else None, key)
        if target is None or not target.is_file():
            return self.send_json(403, {"error": f"{task_id} declares no readable {key!r}"})
        try:
            body = target.read_bytes()
        except OSError as exc:
            return self.send_json(404, {"error": str(exc)})
        self.send_bytes(200, "text/plain; charset=utf-8", body)

    def send_page(self) -> None:
        try:
            body = PAGE.read_bytes()
        except OSError:
            return self.send_json(500, {"error": f"{PAGE} is missing - reinstall the plugin"})
        self.send_bytes(200, "text/html; charset=utf-8", body)

    def send_json(self, status: int, payload: dict) -> None:
        self.send_bytes(status, "application/json; charset=utf-8",
                        json.dumps(payload).encode("utf-8"))

    def send_bytes(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass  # the page polls every 2s forever; the default log buries the URL


def probe(port: int) -> str:
    """Whether the server already on `port` is one of ours: 'ours' or 'stranger'.

    Only asked once a bind has failed, so something is listening and will answer.
    Worth the round trip rather than assuming the holder is a sibling: without it
    the command cheerfully prints a board URL pointing at somebody else's app.

    Do not use this to decide whether a port is FREE. A closed loopback port does
    not always refuse -- on this developer's Windows box it drops, and the connect
    times out after two seconds. Binding is the authoritative test; this is not.
    """
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
            body = json.loads(response.read().decode("utf-8", "replace"))
        return "ours" if isinstance(body, dict) and body.get("server") == SERVER_ID else "stranger"
    except (urllib.error.URLError, OSError, ValueError):
        return "stranger"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_root", nargs="?", default=".",
                        help="project to register and show (default: current directory)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"pinned port, never auto-picked (default: {DEFAULT_PORT})")
    parser.add_argument("--forget", action="store_true",
                        help="drop this project from the registry and exit")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    if args.forget:
        # A repo registered from the wrong directory otherwise sticks for good:
        # only a repo whose folder is DELETED drops itself, and a boardless one
        # is kept on purpose so its tab can say "run /mpi-init".
        register(root, forget=True)
        print(f"Forgot {root}")
        return 0
    if not root.is_dir():
        print(f"No such directory: {root}", file=sys.stderr)
        return 1
    register(root)
    url = f"http://localhost:{args.port}"

    # Bind first: it is the only authoritative answer to "is this port free?".
    # Only once it fails is it worth asking who is holding it.
    try:
        server = Server(("127.0.0.1", args.port), Handler)
    except OSError:
        if probe(args.port) == "ours":
            print(f"Already serving. Registered {root.name} -> {url}?repo={root.name}")
            return 0
        print(f"Port {args.port} is held by something that is not the board server. "
              f"Free it, or pass --port.", file=sys.stderr)
        return 1
    print(f"Mpi-Kanban boards at {url}   (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
