"""Exercise MPI same-filesystem message coordination state.

The smoke uses temporary MPI roots by default, so it proves the file contract
without mutating the active project. Pass --peer-root to exercise explicit
same-machine delivery into a real peer root; the delivered peer message is
resolved and archived before exit.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UNRESOLVED = {"open", "acknowledged", "replied"}
TERMINAL = {"resolved", "superseded", "closed"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def state_root(root: Path) -> Path:
    return root / ".agents" / "mpi-kanban" / "state"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_state_root(root: Path) -> dict[str, Any]:
    state = state_root(root)
    for name in ("sessions", "tasks", "files", "messages", "handoffs", "archive"):
        (state / name).mkdir(parents=True, exist_ok=True)
    index_path = state / "index.json"
    if index_path.exists():
        index = read_json(index_path)
    else:
        index = {
            "schema": "mpi-kanban/state-index/v1",
            "updated_at": now(),
            "board": ".agents/mpi-kanban/board.json",
            "heartbeat_timeout_minutes": 120,
            "active_sessions": [],
            "active_tasks": [],
            "active_file_claims": [],
            "pending_file_states": [],
            "open_messages": [],
            "active_handoffs": [],
        }
    index.setdefault("open_messages", [])
    write_json(index_path, index)
    return index


def save_index(root: Path, index: dict[str, Any]) -> None:
    index["updated_at"] = now()
    write_json(state_root(root) / "index.json", index)


def message_path(root: Path, message_id: str) -> Path:
    return state_root(root) / "messages" / f"{message_id}.json"


def send_message(
    root: Path,
    sender: dict[str, Any],
    recipient: dict[str, Any],
    subject: str,
    body: str,
    *,
    related: dict[str, Any] | None = None,
    thread: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
) -> Path:
    ensure_state_root(root)
    index = read_json(state_root(root) / "index.json")
    message_id = str(uuid.uuid4())
    path = message_path(root, message_id)
    stamp = now()
    message: dict[str, Any] = {
        "schema": "mpi-kanban/message/v1",
        "id": message_id,
        "status": "open",
        "created_at": stamp,
        "updated_at": stamp,
        "from": sender,
        "to": recipient,
        "subject": subject,
        "body": body,
        "related": related or {},
        "thread": thread or {"root": None, "parent": None},
        "recent_events": [{"at": stamp, "event": "created"}],
    }
    if provenance:
        message.update(provenance)
    write_json(path, message)
    pointer = rel(root, path)
    if pointer not in index.setdefault("open_messages", []):
        index["open_messages"].append(pointer)
    save_index(root, index)
    return path


def reply_to_message(root: Path, parent_path: Path, sender: dict[str, Any], body: str) -> Path:
    parent = read_json(parent_path)
    parent_pointer = rel(root, parent_path)
    root_pointer = parent.get("thread", {}).get("root") or parent_pointer
    recipient = {"selector": "session", "value": parent["from"].get("session", parent["from"])}
    child = send_message(
        root,
        sender,
        recipient,
        f"Re: {parent['subject']}",
        body,
        related=parent.get("related", {}),
        thread={"root": root_pointer, "parent": parent_pointer},
    )
    parent["status"] = "replied"
    parent["updated_at"] = now()
    parent.setdefault("recent_events", []).append(
        {"at": parent["updated_at"], "event": "replied", "reply": rel(root, child)}
    )
    write_json(parent_path, parent)
    index = read_json(state_root(root) / "index.json")
    if parent_pointer not in index.setdefault("open_messages", []):
        index["open_messages"].append(parent_pointer)
    save_index(root, index)
    return child


def resolve_message(root: Path, path: Path, resolver: dict[str, Any], outcome: str) -> None:
    index = read_json(state_root(root) / "index.json")
    message = read_json(path)
    message["status"] = "resolved"
    message["updated_at"] = now()
    message.setdefault("recent_events", []).append(
        {"at": message["updated_at"], "event": "resolved", "by": resolver, "outcome": outcome}
    )
    write_json(path, message)
    pointer = rel(root, path)
    index["open_messages"] = [item for item in index.get("open_messages", []) if item != pointer]
    save_index(root, index)


def create_claim(root: Path, owner_session: str, file_path: str) -> Path:
    ensure_state_root(root)
    claim_id = str(uuid.uuid4())
    path = state_root(root) / "files" / f"{claim_id}.json"
    claim = {
        "schema": "mpi-kanban/file-claim/v1",
        "id": claim_id,
        "path": file_path,
        "owner_session": owner_session,
        "owner_role": "implementer",
        "status": "claimed",
        "claim_kind": "write",
        "heartbeat_at": now(),
        "recent_events": [{"at": now(), "event": "claimed_for_write"}],
    }
    write_json(path, claim)
    index = read_json(state_root(root) / "index.json")
    pointer = rel(root, path)
    if pointer not in index.setdefault("active_file_claims", []):
        index["active_file_claims"].append(pointer)
    save_index(root, index)
    return path


def negotiate_claim(root: Path, requester: dict[str, Any], requested_path: str) -> Path:
    index = read_json(state_root(root) / "index.json")
    for pointer in index.get("active_file_claims", []):
        claim_path = root / pointer
        claim = read_json(claim_path)
        paths = [claim.get("path"), *claim.get("paths", [])]
        if claim.get("status") == "claimed" and requested_path in paths:
            return send_message(
                root,
                requester,
                {"selector": "session", "value": claim["owner_session"]},
                "Request file-claim handoff",
                f"I need to edit {requested_path}. Can you release or hand off the claim?",
                related={"files": [{"path": requested_path}], "claim": pointer},
            )
    raise AssertionError(f"expected an active claim for {requested_path}")


def route_to_peer(source_root: Path, peer_root: Path, source_session: str) -> Path:
    return send_message(
        peer_root,
        {"session": source_session, "agent": "codex", "role": "implementer"},
        {"selector": "workspace", "value": str(peer_root)},
        "Peer workspace message smoke",
        "This verifies explicit same-machine peer workspace routing.",
        provenance={"from_workspace": str(source_root), "to_workspace": str(peer_root)},
    )


def archive_terminal_messages(root: Path) -> list[Path]:
    index = read_json(state_root(root) / "index.json")
    archive_root = state_root(root) / "archive" / "messages"
    archive_root.mkdir(parents=True, exist_ok=True)
    archived: list[Path] = []
    for path in sorted((state_root(root) / "messages").glob("*.json")):
        message = read_json(path)
        if message.get("status") in TERMINAL:
            pointer = rel(root, path)
            target = archive_root / path.name
            shutil.move(str(path), target)
            archived.append(target)
            index["open_messages"] = [item for item in index.get("open_messages", []) if item != pointer]
    save_index(root, index)
    return archived


def assert_index_consistent(root: Path) -> None:
    index = read_json(state_root(root) / "index.json")
    for pointer in index.get("open_messages", []):
        path = root / pointer
        message = read_json(path)
        assert message["status"] in UNRESOLVED, (pointer, message["status"])
    for path in (state_root(root) / "messages").glob("*.json"):
        message = read_json(path)
        pointer = rel(root, path)
        if message["status"] in UNRESOLVED:
            assert pointer in index.get("open_messages", []), pointer
        else:
            assert pointer not in index.get("open_messages", []), pointer


def run_smoke(peer_root: Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="mpi-message-smoke-") as temp:
        source = Path(temp) / "source"
        peer = peer_root or Path(temp) / "peer"
        source.mkdir(parents=True, exist_ok=True)
        peer.mkdir(parents=True, exist_ok=True)
        ensure_state_root(source)
        ensure_state_root(peer)

        owner_session = ".agents/mpi-kanban/state/sessions/css-agent.json"
        requester = {"session": ".agents/mpi-kanban/state/sessions/js-agent.json", "agent": "codex", "role": "implementer"}

        first = send_message(
            source,
            requester,
            {"selector": "role", "value": "reviewer"},
            "Review message bus contract",
            "Please review the message state contract.",
            related={"task_card": "MPI-2"},
        )
        child = reply_to_message(
            source,
            first,
            {"session": ".agents/mpi-kanban/state/sessions/reviewer.json", "agent": "codex", "role": "reviewer"},
            "The contract is coherent.",
        )
        resolve_message(source, first, requester, "Parent request answered.")

        create_claim(source, owner_session, "src/app.js")
        negotiation = negotiate_claim(source, requester, "src/app.js")

        peer_message = route_to_peer(source, peer, requester["session"])
        peer_index_before_cleanup = read_json(state_root(peer) / "index.json")
        assert rel(peer, peer_message) in peer_index_before_cleanup["open_messages"]
        resolve_message(peer, peer_message, requester, "Peer delivery verified.")

        archived = archive_terminal_messages(source)
        peer_archived = archive_terminal_messages(peer)

        assert_index_consistent(source)
        assert_index_consistent(peer)
        assert negotiation.exists()
        assert child.exists()
        assert archived
        assert peer_archived
        return {
            "source_root": str(source),
            "peer_root": str(peer),
            "reply": rel(source, child),
            "claim_negotiation": rel(source, negotiation),
            "peer_message_archived": str(peer_archived[0]),
            "source_archived_count": len(archived),
            "open_messages_after_cleanup": len(read_json(state_root(source) / "index.json")["open_messages"]),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--peer-root", type=Path, help="explicit peer root for same-machine delivery")
    args = parser.parse_args()
    result = run_smoke(args.peer_root)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
