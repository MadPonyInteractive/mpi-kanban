#!/usr/bin/env python3
"""SessionStart hook: put the coordination state in front of the agent, unasked.

Claims, messages and handoffs only ever reached an agent that typed an `/mpi-*`
command first. `mpi-continue` carries 2% of usage, so for the other 98% the
coordination layer was invisible -- which is how a live project ran for six
weeks with file claims on disk binding nothing.

Read-only and never blocks. It prints nothing at all when the repo has no board
or has nothing outstanding, so a quiet project stays quiet.

Run self-check:  python session-start.py --selftest
"""
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


def summarize(doing, claims, messages, handoffs):
    """Build the context lines from already-loaded records. None means silent."""
    lines = []
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
    if not lines:
        return None
    lines.append("Resume with `/mpi-continue`; close with `/mpi-end-session`.")
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
    context = summarize(*collect(root))
    if context:
        json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                          "additionalContext": context}}, sys.stdout)
    sys.exit(0)


def _selftest():
    assert summarize([], [], [], []) is None, "a quiet project must stay silent"

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
    print("session-start selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
