"""End-to-end smoke: run each guard as a real hook process against a temp project."""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HOOKS = pathlib.Path(__file__).resolve().parents[1] / "hooks"


def run(hook, payload):
    proc = subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stderr.strip()


def build_project(root):
    board = pathlib.Path(root, ".agents", "mpi-kanban")
    (board / "state" / "sessions").mkdir(parents=True)
    (board / "state" / "files").mkdir(parents=True)
    (board / "board.json").write_text(
        json.dumps({"schema": "mpi-kanban/board/v1", "next_id": 2,
                    "columns": {"todo": [], "doing": [], "done": []}}),
        encoding="utf-8")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (board / "state" / "sessions" / "peer.json").write_text(
        json.dumps({"schema": "mpi-kanban/session/v1", "id": "peer", "status": "active",
                    "claude_session_id": "peer-session", "heartbeat_at": now}),
        encoding="utf-8")
    (board / "state" / "files" / "claim.json").write_text(
        json.dumps({"schema": "mpi-kanban/file-claim/v1", "id": "claim",
                    "paths": ["src/api/"], "status": "claimed",
                    "owner_session": ".agents/mpi-kanban/state/sessions/peer.json"}),
        encoding="utf-8")
    # a BOM, which PowerShell writers add by default and a strict reader chokes on
    (board / "state" / "index.json").write_text(
        json.dumps({"schema": "mpi-kanban/state-index/v1",
                    "active_file_claims": [".agents/mpi-kanban/state/files/claim.json"]}),
        encoding="utf-8-sig")


def edit_payload(root, path, session="me"):
    return {"session_id": session, "cwd": root, "hook_event_name": "PreToolUse",
            "tool_name": "Edit", "tool_input": {"file_path": os.path.join(root, path)}}


def main():
    with tempfile.TemporaryDirectory() as root:
        build_project(root)
        checks = []

        code, err = run("guard-git.py", {"session_id": "me", "cwd": root,
                                         "tool_name": "Bash",
                                         "tool_input": {"command": "git checkout -- src/"}})
        checks.append(("guard-git blocks a destructive checkout", code == 2 and "BLOCKED" in err))

        code, _ = run("guard-git.py", {"session_id": "me", "cwd": root, "tool_name": "Bash",
                                       "tool_input": {"command": "git status"}})
        checks.append(("guard-git allows git status", code == 0))

        code, err = run("guard-claim.py", edit_payload(root, "src/api/routes.py"))
        checks.append(("guard-claim blocks a live peer's subtree claim",
                       code == 2 and "claimed for write" in err))

        code, _ = run("guard-claim.py", edit_payload(root, "src/ui/main.py"))
        checks.append(("guard-claim allows an unclaimed file", code == 0))

        code, _ = run("guard-claim.py", edit_payload(root, "src/api/routes.py", "peer-session"))
        checks.append(("guard-claim allows the owner's own write", code == 0))

        code, err = run("guard-card.py", edit_payload(root, "src/ui/main.py"))
        checks.append(("guard-card blocks a code edit with no card",
                       code == 2 and "maturity" in err))

        code, _ = run("guard-card.py", edit_payload(root, "src/ui/main.py"))
        checks.append(("guard-card blocks only once per session", code == 0))

        code, _ = run("guard-card.py", edit_payload(root, ".agents/mpi-kanban/tasks/MPI-1/task.json"))
        checks.append(("guard-card allows the first card", code == 0))

        code, err = run("guard-card.py", edit_payload(root, ".agents/mpi-kanban/tasks/MPI-2/task.json"))
        checks.append(("guard-card blocks a second card", code == 2 and "MPI-1" in err))

        # an unadopted repo must be untouched by every guard
        with tempfile.TemporaryDirectory() as plain:
            code, _ = run("guard-card.py", edit_payload(plain, "src/app.py"))
            checks.append(("guard-card is a no-op without a board", code == 0))
            code, _ = run("guard-claim.py", edit_payload(plain, "src/app.py"))
            checks.append(("guard-claim is a no-op without a board", code == 0))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS  " if ok else "FAIL  ") + name)
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
