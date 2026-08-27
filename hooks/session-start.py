#!/usr/bin/env python3
"""SessionStart hook: put the coordination state in front of the agent, unasked.

Claims, messages and handoffs only ever reached an agent that typed an `/mpi-*`
command first. `mpi-continue` carries 2% of usage, so for the other 98% the
coordination layer was invisible -- which is how a live project ran for six
weeks with file claims on disk binding nothing.

It also registers this session's coordination record, because asking the agent
to do it meant it stopped happening -- eight days of a live project with no
session records and no file claims, unnoticed. That record is what lets
`guard-claim` tell a solo session (nothing to coordinate) from two agents
writing at once (everything to coordinate).

Never blocks. It prints nothing at all when the repo has no board or has
nothing outstanding, so a quiet project stays quiet.

Run self-check:  python session-start.py --selftest
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mpi  # noqa: E402

MAX_ROWS = 5  # per section; a wall of text gets skimmed, not read


def _clip(text, width=64):
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def _more(items):
    extra = len(items) - MAX_ROWS
    return ["  ... and %d more" % extra] if extra > 0 else []


def lib_path():
    """`skills/mpi-lib/scripts`, which ships beside `hooks/` in the same plugin."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "mpi-lib", "scripts")


def register_board(root):
    """Add this repo to the browser board's registry, so the tab list fills itself.

    Registering used to mean running `board_server.py` once inside every repo,
    which is a command nobody remembers for a board they only look at when
    something is wrong. A session start already knows the repo root, so it does
    it. The registry is a machine-global list of paths and nothing more - not a
    coordination record, no heartbeat, no claim - so this is one small write.

    Never fatal: a board you cannot list is worth less than a session you cannot
    start.
    """
    try:
        sys.path.insert(0, lib_path())
        import board_server  # noqa: PLC0415 - only when a board actually exists
        from pathlib import Path
        board_server.register(Path(root))
    except Exception:
        pass


def board_errors(root):
    """`validate_board` findings, or []. The check the create path could skip.

    A half-written card - `task.json` on disk, id never inserted into a column -
    is invisible to every reader of `board.json`, so the only symptom is a human
    saying the board is empty. It is cheap to notice here and expensive to notice
    by hand: it cost a round of debugging the board server on 2026-08-27.
    """
    try:
        sys.path.insert(0, lib_path())
        import validate_board  # noqa: PLC0415
        from pathlib import Path
        return validate_board.validate_board(Path(root))
    except Exception:
        return []


def summarize(doing, claims, messages, handoffs, errors=()):
    """Build the context lines from already-loaded records. None means silent."""
    lines = []
    if errors:
        lines.append("Board file problems (repair: `validate_board.py <root> --fix`):")
        for message in errors[:MAX_ROWS]:
            lines.append("  %s" % _clip(message, 96))
        lines += _more(list(errors))
    if doing:
        lines.append("Cards in `doing`:")
        for card in doing[:MAX_ROWS]:
            lines.append("  %s  %s  [%s]" % (card.get("id", "?"),
                                             _clip(card.get("title")),
                                             card.get("maturity", "?")))
        lines += _more(doing)
    if claims:
        lines.append("Files claimed for write:")
        for paths, owner in claims[:MAX_ROWS]:
            lines.append("  %s  <- %s" % (_clip(", ".join(paths)), os.path.basename(owner)))
        lines += _more(claims)
    if messages:
        lines.append("Unresolved messages:")
        for subject, status in messages[:MAX_ROWS]:
            lines.append("  [%s] %s" % (status, _clip(subject)))
        lines += _more(messages)
    if handoffs:
        lines.append("Open handoffs:")
        for rel in handoffs[:MAX_ROWS]:
            lines.append("  %s" % rel)
        lines += _more(handoffs)
    if lines:
        lines.append("Resume with `/mpi-continue`; switch sessions with "
                     "`/mpi-handoff`; close with `/mpi-end-session`.")
    # The one line that lets any session in any adopted repo open the board
    # without being told the path. Cheaper than a skill, whose description would
    # load every session whether or not anyone wanted to look at a board.
    #
    # It sits OUTSIDE the `if lines:` on purpose. `main()` has already
    # established the project is adopted, and this is a capability pointer, not
    # state - 1.3.0 appended it after an early `return None` for an empty board
    # state, which made it invisible in exactly the quiet, fresh repo that has
    # no other way to learn the server exists. A hook with no board still
    # returns nothing, from `main()`; that constraint is untouched.
    lines.append("Board in a browser: this repo is registered, so it is already a tab. "
                 "Run `${CLAUDE_PLUGIN_ROOT}/skills/mpi-lib/scripts/board_server.py` "
                 "in the background if nothing is serving yet, then open the URL it prints.")
    return "Mpi-Kanban state:\n" + "\n".join(lines)


def collect(root):
    board = _mpi.read_json(os.path.join(root, _mpi.BOARD)) or {}
    doing = []
    for card_id in (board.get("columns") or {}).get("doing") or []:
        card = _mpi.read_json(os.path.join(
            root, ".agents/mpi-kanban/tasks", card_id, "task.json")) or {}
        doing.append({"id": card_id, "title": card.get("title"),
                      "maturity": card.get("maturity")})

    index = _mpi.read_json(os.path.join(root, _mpi.STATE, "index.json")) or {}
    claims = []
    for rel in index.get("active_file_claims") or []:
        record = _mpi.read_json(os.path.join(root, rel)) or {}
        paths = _mpi.claim_paths(record)
        if paths:
            claims.append((paths, record.get("owner_session") or rel))
    messages = []
    for rel in index.get("open_messages") or []:
        record = _mpi.read_json(os.path.join(root, rel)) or {}
        messages.append((record.get("subject") or rel, record.get("status") or "open"))
    handoffs = list(index.get("active_handoffs") or [])
    return doing, claims, messages, handoffs


def main():
    data = _mpi.payload()
    if not data:
        sys.exit(0)
    root = _mpi.project_root(data)
    if not _mpi.adopted(root):
        sys.exit(0)
    _mpi.ensure_session(root, data.get("session_id"),
                        datetime.datetime.now(datetime.timezone.utc))
    register_board(root)
    context = summarize(*collect(root), errors=board_errors(root))
    if context:
        json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                          "additionalContext": context}}, sys.stdout)
    sys.exit(0)


def _selftest():
    # A quiet ADOPTED project still gets the board pointer, and nothing else.
    # It used to return None here, which hid the pointer in the one repo with no
    # other way to find it. An UNADOPTED project is still silent - `main()`
    # exits before reaching this function.
    quiet = summarize([], [], [], [])
    assert quiet is not None, "a quiet adopted project must still offer the board"
    assert "board_server.py" in quiet
    assert "/mpi-continue" not in quiet, "nothing to resume, so do not say resume"

    out = summarize([{"id": "MPI-28", "title": "Rebuild", "maturity": "in-progress"}],
                    [(["hooks/", "scripts/x.py"], "state/sessions/abc.json")],
                    [("Release the claim", "open")],
                    [".agents/mpi-kanban/state/handoffs/dc9.json"])
    assert "MPI-28" in out and "in-progress" in out
    assert "hooks/, scripts/x.py" in out and "abc.json" in out
    assert "[open] Release the claim" in out
    assert "dc9.json" in out

    many = [{"id": "MPI-%d" % n, "title": "t", "maturity": "in-progress"} for n in range(9)]
    assert "and 4 more" in summarize(many, [], [], [])
    assert _clip("x" * 80).endswith("…")

    # A half-written card is invisible in every viewer, so it is said out loud
    # here rather than left for someone to find by reading board.json by hand.
    broken = summarize([], [], [], [], ["orphaned task folder not listed in "
                                        "board.json: tasks/MPI-629"])
    assert "tasks/MPI-629" in broken and "--fix" in broken
    print("session-start selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
