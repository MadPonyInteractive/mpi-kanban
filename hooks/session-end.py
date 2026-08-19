#!/usr/bin/env python3
"""SessionEnd hook: close this session's coordination record.

Nothing in the pack ever wrote `status: closed` -- it was a step in
`coordination-ops/lifecycle.md`, and prose steps are exactly what stopped
happening. So a window closed with the X button, a crash, or any session that
skipped close-out left an `active` record behind with a recent heartbeat.

That is not a cosmetic leak. `guard-claim`'s unclaimed-write rule counts live
peers, so one dead-but-`active` record charges every LATER session in that repo
for the whole heartbeat window while it is genuinely alone -- inverting the cost
model the rule exists to protect. A hook cannot forget; an agent can.

Claims are deliberately left alone. Releasing them is a decision with a status
attached (`complete`, `needs_review`, ...) that only the working agent can make,
and rule 1 already treats a claim whose owner is closed as advisory.

Never blocks, and says nothing.

Run self-check:  python session-end.py --selftest
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mpi  # noqa: E402


def close_record(record, now):
    """Mark a session record ended. Returns None when there is nothing to do."""
    if not isinstance(record, dict) or record.get("status") == "closed":
        return None
    record["status"] = "closed"
    record["heartbeat_at"] = _mpi._stamp(now)
    events = record.get("recent_events")
    if not isinstance(events, list):
        events = []
    events.append({"at": _mpi._stamp(now), "event": "session_closed"})
    record["recent_events"] = events[-20:]  # ponytail: a record, not a log file
    return record


def main():
    data = _mpi.payload()
    if not data:
        sys.exit(0)
    root = _mpi.project_root(data)
    if not _mpi.adopted(root):
        sys.exit(0)
    session_id = data.get("session_id")
    if not session_id:
        sys.exit(0)
    path = os.path.join(root, _mpi.SESSIONS, "%s.json" % session_id)
    closed = close_record(_mpi.read_json(path), datetime.datetime.now(datetime.timezone.utc))
    if closed:
        _mpi.write_json(path, closed)
    sys.exit(0)


def _selftest():
    now = datetime.datetime(2026, 8, 19, 12, 0, tzinfo=datetime.timezone.utc)

    out = close_record({"status": "active", "heartbeat_at": "2026-08-19T11:00:00Z"}, now)
    assert out["status"] == "closed"
    assert out["heartbeat_at"] == "2026-08-19T12:00:00Z"
    assert out["recent_events"][-1]["event"] == "session_closed"
    assert not _mpi.live_session(out, 120, now), "a closed record is never a live peer"

    assert close_record({"status": "closed"}, now) is None, "already closed"
    assert close_record(None, now) is None, "no record, nothing to close"

    kept = close_record({"status": "active", "recent_events": [{"event": "session_started"}]}, now)
    assert len(kept["recent_events"]) == 2, "existing history is kept"
    print("session-end selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
