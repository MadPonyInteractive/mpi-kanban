#!/usr/bin/env python3
"""PreToolUse guard: refuse a write to a path another live session has claimed.

File claims sat on disk for six weeks binding nothing, because claiming was
prose in skills that an agent only reads when a skill is invoked. This binds it
to EVERY edit, skill-invoked or not.

What it blocks: a write to a path covered by an `active_file_claims` record with
status `claimed`, whose owning session is live (`status: active`, heartbeat
inside the index timeout) and is NOT this Claude session.

What it deliberately allows:
  * a claim this session owns
  * a claim whose owner session is stale, closed, or unreadable
  * any project with no `board.json`

The pack cannot lock files between independent Claude Code windows -- nothing
can, there is no cross-session file lock on any platform. Blocking on an
unattributable claim would stop an agent editing files it claimed itself, so
attribution failure allows and the claim stays advisory.

Ownership is matched through `claude_session_id` on the session record, written
by `coordination-ops/lifecycle.md` at session start.

Exit 2 blocks the call and returns the stderr text to the agent.

Run self-check:  python guard-claim.py --selftest
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mpi  # noqa: E402

BLOCK_MSG = """BLOCKED: `{path}` is claimed for write by another live session.

  claim   {record}
  owner   {owner}

That session has uncommitted work in this file. Writing over it produces a
conflict no `git status` will show you.

Do this instead:
  * work on a file inside your own ownership set
  * ask the owner to release it -- `mpi-message` reaches the same filesystem
  * if the owner is gone, release the claim explicitly, then repeat the edit

Never edit around a live claim by copying the file aside."""


def _live(session, timeout_minutes, now):
    """Is the owning session still running?"""
    if not isinstance(session, dict) or session.get("status") != "active":
        return False
    stamp = session.get("heartbeat_at")
    if not isinstance(stamp, str):
        return False
    try:
        beat = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    if beat.tzinfo is None:
        beat = beat.replace(tzinfo=datetime.timezone.utc)
    return (now - beat) <= datetime.timedelta(minutes=timeout_minutes)


def blocking_claim(candidate, claims, my_session_id, timeout_minutes, now):
    """Return (record_path, owner) for a live foreign claim, else None.

    `claims` is a list of (record_path, record, owner_session_record) triples, so
    the decision is testable without a project tree.
    """
    for record_path, record, owner in claims:
        if not isinstance(record, dict) or record.get("status") != "claimed":
            continue
        if not any(_mpi.claim_covers(entry, candidate) for entry in _mpi.claim_paths(record)):
            continue
        if not isinstance(owner, dict):
            continue  # unattributable: advisory only, see the module docstring
        if owner.get("claude_session_id") == my_session_id:
            continue  # my own claim
        if not _live(owner, timeout_minutes, now):
            continue
        return record_path, record.get("owner_session") or owner.get("id") or "unknown"
    return None


def main():
    data = _mpi.payload()
    if not data:
        sys.exit(0)
    root = _mpi.project_root(data)
    if not _mpi.adopted(root):
        sys.exit(0)
    candidates = _mpi.written_paths(data)
    if not candidates:
        sys.exit(0)

    index = _mpi.read_json(os.path.join(root, _mpi.STATE, "index.json")) or {}
    timeout = index.get("heartbeat_timeout_minutes") or 120
    claims = []
    for rel in index.get("active_file_claims") or []:
        record = _mpi.read_json(os.path.join(root, rel))
        owner_rel = (record or {}).get("owner_session")
        owner = _mpi.read_json(os.path.join(root, owner_rel)) if owner_rel else None
        claims.append((rel, record, owner))

    now = datetime.datetime.now(datetime.timezone.utc)
    for candidate in candidates:
        hit = blocking_claim(candidate, claims, data.get("session_id"), timeout, now)
        if hit:
            record_path, owner = hit
            _mpi.deny(BLOCK_MSG.format(path=candidate, record=record_path, owner=owner))
    sys.exit(0)


def _selftest():
    now = datetime.datetime(2026, 8, 9, 12, 0, tzinfo=datetime.timezone.utc)
    fresh = {"status": "active", "heartbeat_at": "2026-08-09T11:30:00Z",
             "claude_session_id": "peer", "id": "peer-uuid"}
    stale = dict(fresh, heartbeat_at="2026-08-09T02:00:00Z")
    mine = dict(fresh, claude_session_id="me")

    single = {"status": "claimed", "path": "src/App.tsx", "owner_session": "s/peer.json"}
    multi = {"status": "claimed", "paths": ["src/api/", "docs/x.md"],
             "owner_session": "s/peer.json"}
    released = {"status": "released", "path": "src/App.tsx", "owner_session": "s/peer.json"}

    def hit(candidate, claims):
        return blocking_claim(candidate, claims, "me", 120, now)

    assert hit("src/App.tsx", [("c1", single, fresh)])
    assert hit("src/api/routes.py", [("c2", multi, fresh)]), "paths claims must bind too"
    assert not hit("src/other.py", [("c1", single, fresh)])
    assert not hit("src/App.tsx", [("c1", single, mine)]), "my own claim"
    assert not hit("src/App.tsx", [("c1", single, stale)]), "stale heartbeat"
    assert not hit("src/App.tsx", [("c1", released, fresh)]), "not an active lock"
    assert not hit("src/App.tsx", [("c1", single, None)]), "unattributable is advisory"
    assert not _live({"status": "closed", "heartbeat_at": "2026-08-09T11:59:00Z"}, 120, now)
    print("guard-claim selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
