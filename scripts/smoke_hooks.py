"""End-to-end smoke: run each guard as a real hook process against a temp project."""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HOOKS = pathlib.Path(__file__).resolve().parents[1] / "hooks"


def _proc(hook, payload):
    return subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def run(hook, payload):
    """A blocking guard is judged by its exit code and the reason it printed."""
    proc = _proc(hook, payload)
    return proc.returncode, proc.stderr.strip()


def run_out(hook, payload):
    """A reporting hook never blocks; what it emits on stdout is the behaviour."""
    proc = _proc(hook, payload)
    return proc.returncode, proc.stdout.strip()


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


def sessions_dir(root):
    return pathlib.Path(root, ".agents", "mpi-kanban", "state", "sessions")


def age_every_peer(root, keep, minutes):
    """Backdate every session but `keep`, leaving them `active` as a kill would.

    Every guard-claim call registers its own session, so by this point the
    project holds more than one peer record; ageing a single file proves
    nothing.
    """
    beat = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=minutes)).isoformat()
    for record_path in sessions_dir(root).glob("*.json"):
        record = json.loads(record_path.read_text(encoding="utf-8-sig"))
        if record.get("claude_session_id") == keep:
            continue
        record["heartbeat_at"] = beat
        record_path.write_text(json.dumps(record), encoding="utf-8")


def bash_payload(root, command, session="me"):
    return {"session_id": session, "cwd": root, "hook_event_name": "PreToolUse",
            "tool_name": "Bash", "tool_input": {"command": command}}


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

        code, err = run("guard-claim.py", edit_payload(root, "src/ui/main.py"))
        checks.append(("guard-claim blocks an unclaimed file while a peer is live",
                       code == 2 and "not claimed" in err))

        code, _ = run("guard-claim.py", edit_payload(root, "src/api/routes.py", "peer-session"))
        checks.append(("guard-claim allows the owner's own write", code == 0))

        # The Bash path. Registered only against Edit|Write|NotebookEdit until
        # 1.0.1, so `sed -i` walked straight through a live claim.
        code, err = run("guard-claim.py",
                        bash_payload(root, "sed -i 's/a/b/' src/api/routes.py"))
        checks.append(("guard-claim blocks a shell in-place edit of a claimed file",
                       code == 2 and "BLOCKED" in err))

        code, err = run("guard-claim.py", bash_payload(root, "echo x > src/api/new.py"))
        checks.append(("guard-claim blocks a shell redirect into a claimed subtree",
                       code == 2 and "BLOCKED" in err))

        code, _ = run("guard-claim.py",
                      bash_payload(root, "grep -n 'x > y' src/api/routes.py"))
        checks.append(("guard-claim allows a read of a claimed file", code == 0))

        # Rule 2 has to leave the coordination records themselves writable, or
        # claiming -- itself a write -- could never happen.
        code, _ = run("guard-claim.py",
                      edit_payload(root, ".agents/mpi-kanban/state/files/new.json"))
        checks.append(("guard-claim allows an unclaimed write under .agents/", code == 0))

        checks.append(("guard-claim registers this session on a guarded write",
                       (sessions_dir(root) / "me.json").exists()))

        # A session killed before SessionEnd runs leaves an `active` record
        # behind. Rule 2 must stop counting it well before its claim expires,
        # or one dead window charges every later solo session for two hours.
        age_every_peer(root, "me", 45)

        code, _ = run("guard-claim.py", edit_payload(root, "src/ui/main.py"))
        checks.append(("guard-claim stops counting a peer that went quiet", code == 0))

        code, err = run("guard-claim.py", edit_payload(root, "src/api/routes.py"))
        checks.append(("guard-claim still honours that peer's claim",
                       code == 2 and "claimed for write" in err))

        # Alone in the workspace there is nobody to collide with, so rule 2
        # costs a solo session nothing. This is what keeps the guard affordable.
        age_every_peer(root, "me", 60 * 24)
        code, _ = run("guard-claim.py", edit_payload(root, "src/ui/main.py"))
        checks.append(("guard-claim allows an unclaimed file once alone", code == 0))

        code, err = run("guard-card.py", edit_payload(root, "src/ui/main.py"))
        checks.append(("guard-card blocks a code edit with no card",
                       code == 2 and "maturity" in err))

        code, _ = run("guard-card.py", edit_payload(root, "src/ui/main.py"))
        checks.append(("guard-card blocks only once per session", code == 0))

        code, _ = run("guard-card.py", edit_payload(root, ".agents/mpi-kanban/tasks/MPI-1/task.json"))
        checks.append(("guard-card allows the first card", code == 0))

        code, err = run("guard-card.py", edit_payload(root, ".agents/mpi-kanban/tasks/MPI-2/task.json"))
        checks.append(("guard-card blocks a second card", code == 2 and "MPI-1" in err))

        code, _ = run("guard-card.py", edit_payload(root, ".agents/mpi-kanban/tasks/MPI-2/task.json"))
        checks.append(("guard-card lets the justified second card through on retry", code == 0))

        code, err = run("guard-card.py", edit_payload(root, ".agents/mpi-kanban/tasks/MPI-3/task.json"))
        checks.append(("guard-card still blocks a third card", code == 2 and "MPI-1" in err))

        # The Bash path, on its own session so the once-per-session state is fresh.
        code, err = run("guard-card.py",
                        bash_payload(root, "sed -i 's/a/b/' src/ui/main.py", "shell"))
        checks.append(("guard-card blocks a shell edit with no card",
                       code == 2 and "BLOCKED" in err))

        code, _ = run("guard-card.py",
                      bash_payload(root, "python -m pytest -q", "shell-read"))
        checks.append(("guard-card allows a command that writes nothing", code == 0))

        # A scratchpad script is not project work and no card could own it. Fresh
        # session, so the once-per-session flag cannot be what lets it through.
        outside = os.path.join(os.path.dirname(root), "scratchpad", "probe.py")
        code, _ = run("guard-card.py", edit_payload(root, outside, "outside"))
        checks.append(("guard-card allows a write outside the project root", code == 0))

        code, err = run("guard-card.py", edit_payload(root, "src/ui/main.py", "outside"))
        checks.append(("guard-card still blocks inside that same session",
                       code == 2 and "maturity" in err))

        code, err = run("guard-shell.py", bash_payload(root, "cat <<'EOF'\nhello\nEOF"))
        checks.append(("guard-shell blocks a heredoc", code == 2 and "heredoc" in err))

        code, err = run("guard-shell.py", bash_payload(root, "grep foo \\\n  -r ."))
        checks.append(("guard-shell blocks a line continuation",
                       code == 2 and "continuation" in err))

        code, _ = run("guard-shell.py", bash_payload(root, "git log --oneline -5"))
        checks.append(("guard-shell allows a single-line command", code == 0))

        # The GPU lease is opt-in, so the unconfigured project comes first.
        code, _ = run("guard-gpu.py", bash_payload(root, "python train.py --steps 10"))
        checks.append(("guard-gpu is off until the project configures patterns", code == 0))

        pathlib.Path(root, ".agents", "mpi-kanban.local.md").write_text(
            "---\ngpu_command_patterns:\n  - python .*train\n---\n", encoding="utf-8")

        code, err = run("guard-gpu.py", bash_payload(root, "python train.py --steps 10"))
        checks.append(("guard-gpu blocks an unleased GPU command",
                       code == 2 and "without holding a lease" in err))

        code, _ = run("guard-gpu.py", bash_payload(
            root, 'python "/p/skills/mpi-lib/scripts/gpu_lease.py" run -- python train.py'))
        checks.append(("guard-gpu allows the leased form", code == 0))

        code, _ = run("guard-gpu.py", bash_payload(root, "python -m pytest -q"))
        checks.append(("guard-gpu allows a command no pattern matches", code == 0))

        code, _ = run("guard-gpu.py", edit_payload(root, "train.py"))
        checks.append(("guard-gpu ignores a file edit", code == 0))

        code, out = run_out("session-start.py", {"session_id": "me", "cwd": root,
                                                 "hook_event_name": "SessionStart",
                                                 "source": "startup"})
        checks.append(("session-start reports an open claim",
                       code == 0 and "src/api/" in out and "additionalContext" in out))

        checks.append(("session-start registers the session it was handed",
                       (sessions_dir(root) / "me.json").exists()))

        code, out = run_out("session-end.py", {"session_id": "me", "cwd": root,
                                               "hook_event_name": "SessionEnd",
                                               "reason": "clear"})
        record = json.loads((sessions_dir(root) / "me.json").read_text(encoding="utf-8-sig"))
        checks.append(("session-end closes the record it was handed",
                       code == 0 and not out and record["status"] == "closed"))

        code, out = run_out("precompact-handoff.py", {"session_id": "me", "cwd": root,
                                                      "hook_event_name": "PreCompact",
                                                      "trigger": "auto"})
        checks.append(("precompact-handoff offers a handoff",
                       code == 0 and "mpi-handoff" in out and "Auto-compaction" in out))

        # an unadopted repo must be untouched by every hook
        with tempfile.TemporaryDirectory() as plain:
            code, _ = run("guard-card.py", edit_payload(plain, "src/app.py"))
            checks.append(("guard-card is a no-op without a board", code == 0))
            code, _ = run("guard-claim.py", edit_payload(plain, "src/app.py"))
            checks.append(("guard-claim is a no-op without a board", code == 0))
            checks.append(("guard-claim registers nothing without a board",
                           not sessions_dir(plain).exists()))
            code, _ = run("guard-shell.py", bash_payload(plain, "cat <<EOF\nx\nEOF"))
            checks.append(("guard-shell is a no-op without a board", code == 0))
            code, _ = run("guard-gpu.py", bash_payload(plain, "python train.py"))
            checks.append(("guard-gpu is a no-op without a board", code == 0))
            code, out = run_out("session-start.py", {"session_id": "me", "cwd": plain,
                                                     "hook_event_name": "SessionStart",
                                                     "source": "startup"})
            checks.append(("session-start is silent without a board", code == 0 and not out))
            code, out = run_out("session-end.py", {"session_id": "me", "cwd": plain,
                                                   "hook_event_name": "SessionEnd",
                                                   "reason": "clear"})
            checks.append(("session-end is a no-op without a board", code == 0 and not out))
            code, out = run_out("precompact-handoff.py", {"session_id": "me", "cwd": plain,
                                                          "hook_event_name": "PreCompact",
                                                          "trigger": "auto"})
            checks.append(("precompact-handoff is silent without a board",
                           code == 0 and not out))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS  " if ok else "FAIL  ") + name)
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
