#!/usr/bin/env python3
"""PreCompact hook: offer a handoff at the moment context is about to be lost.

71% of measured usage sits above 150k context, and the user currently has to
notice compaction coming by eye and ask for a handoff by hand. Compaction is the
one event that knows it is about to happen.

Read-only, never blocks, and stays silent unless there is live work to preserve:
a card in `doing`, or a file claimed for write. `systemMessage` surfaces it to
the user rather than burying it in the transcript.

Run self-check:  python precompact-handoff.py --selftest
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mpi  # noqa: E402


def nudge(trigger, doing, claim_count):
    """The message to surface, or None when there is nothing worth preserving."""
    if not doing and not claim_count:
        return None
    when = "Auto-compaction" if trigger == "auto" else "Compaction"
    parts = []
    if doing:
        parts.append("%s in `doing` (%s)" % (len(doing), ", ".join(doing[:4])))
    if claim_count:
        parts.append("%d file claim%s open" % (claim_count, "" if claim_count == 1 else "s"))
    return ("%s is about to drop this session's context: %s.\n"
            "Run `/mpi-handoff` first if this work should survive it, or "
            "`/mpi-end-session` if it is finished."
            % (when, " and ".join(parts)))


def main():
    data = _mpi.payload()
    if not data:
        sys.exit(0)
    root = _mpi.project_root(data)
    if not _mpi.adopted(root):
        sys.exit(0)
    board = _mpi.read_json(os.path.join(root, _mpi.BOARD)) or {}
    doing = list((board.get("columns") or {}).get("doing") or [])
    index = _mpi.read_json(os.path.join(root, _mpi.STATE, "index.json")) or {}
    message = nudge(data.get("trigger"), doing, len(index.get("active_file_claims") or []))
    if message:
        json.dump({"systemMessage": message}, sys.stdout)
    sys.exit(0)


def _selftest():
    assert nudge("auto", [], 0) is None, "nothing live, nothing to say"
    auto = nudge("auto", ["MPI-28"], 2)
    assert "Auto-compaction" in auto and "MPI-28" in auto and "2 file claims" in auto
    assert "/mpi-handoff" in auto and "/mpi-end-session" in auto
    assert "1 file claim open" in nudge("manual", [], 1)
    assert nudge("manual", ["MPI-1"], 0).startswith("Compaction")
    print("precompact-handoff selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
