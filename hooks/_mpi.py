"""Shared helpers for the Mpi-Kanban PreToolUse guards.

Every guard is a no-op in a project that has no `.agents/mpi-kanban/board.json`:
the plugin is installed globally, so a hook that fires in an unadopted repo is a
bug, not enforcement.
"""
import json
import os
import sys

BOARD = ".agents/mpi-kanban/board.json"
STATE = ".agents/mpi-kanban/state"
HOOK_STATE = STATE + "/hooks"


def payload():
    """The hook input, or None when it is unreadable. Never a reason to block."""
    try:
        return json.load(sys.stdin)
    except Exception:
        return None


def read_json(path):
    """Read JSON tolerating a BOM, which PowerShell writers add by default."""
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return json.load(handle)
    except Exception:
        return None


def project_root(data):
    return data.get("cwd") or os.getcwd()


def adopted(root):
    return os.path.exists(os.path.join(root, BOARD))


def edited_path(data):
    """The workspace-relative path an Edit/Write/NotebookEdit call targets."""
    target = (data.get("tool_input") or {}).get("file_path")
    if not target:
        return None
    root = project_root(data)
    try:
        rel = os.path.relpath(target, root)
    except ValueError:  # different drive on Windows
        return target.replace(os.sep, "/")
    return rel.replace(os.sep, "/")


def session_state(root, session_id):
    """Per-Claude-session guard state. Keyed by the hook payload's session_id."""
    path = os.path.join(root, HOOK_STATE, f"{session_id}.json")
    return path, (read_json(path) or {})


def write_session_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    os.replace(tmp, path)


def deny(reason):
    """Block the tool call and hand the reason back to the agent."""
    print(reason, file=sys.stderr)
    sys.exit(2)


def claim_covers(entry, candidate):
    """A claim entry matches a file exactly, or as a subtree when it ends in `/`."""
    entry = (entry or "").replace(os.sep, "/")
    candidate = (candidate or "").replace(os.sep, "/")
    if not entry or not candidate:
        return False
    if entry.endswith("/"):
        return candidate.startswith(entry)
    return entry == candidate


def claim_paths(record):
    """A record claims EITHER `path` or `paths`; both are first class.

    16 of 44 records in a live project used `paths`, so a reader that only looks
    at `path` misses every multi-file claim in silence.
    """
    if not isinstance(record, dict):
        return []
    if isinstance(record.get("paths"), list):
        return [p for p in record["paths"] if isinstance(p, str)]
    single = record.get("path")
    return [single] if isinstance(single, str) else []


def _selftest():
    assert claim_covers("src/App.tsx", "src/App.tsx")
    assert not claim_covers("src/App.tsx", "src/App.tsx.bak")
    assert claim_covers("skills/mpi-continue/", "skills/mpi-continue/SKILL.md")
    assert not claim_covers("skills/mpi-continue/", "skills/mpi-init/SKILL.md")
    assert claim_covers("src/App.tsx", "src\\App.tsx")
    assert claim_paths({"path": "a.py"}) == ["a.py"]
    assert claim_paths({"paths": ["a.py", "b/"]}) == ["a.py", "b/"]
    assert claim_paths({}) == []
    print("_mpi selftest OK")


if __name__ == "__main__":
    _selftest()
