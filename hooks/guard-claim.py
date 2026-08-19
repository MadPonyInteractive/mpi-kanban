#!/usr/bin/env python3
"""PreToolUse guard: keep two live agents off each other's uncommitted work.

Two rules, and the second one only wakes up when it can earn its cost.

1. CONTESTED: refuse a write to a path covered by an `active_file_claims`
   record with status `claimed`, whose owning session is live (`status:
   active`, heartbeat inside the index timeout) and is NOT this Claude session.

2. UNCLAIMED: while at least one OTHER session is live, refuse a write to a
   path this session holds no claim on. Alone in the workspace there is nobody
   to collide with, so this rule costs a solo session nothing -- which is the
   point. The v1.0 lesson was that a coordination step charged to every session
   gets dropped; a step charged only to the sessions that need it survives.

   Rule 2 uses its own PEER_TIMEOUT_MINUTES, not the index's claim timeout. A
   claim should survive a long pause, but a PEER should not: a session killed
   with the X button before `session-end.py` could run leaves an `active`
   record behind, and every minute that record stays "live" is charged to
   sessions that are genuinely alone -- the exact inversion this rule exists to
   avoid. Two renewal intervals is enough margin for a working peer.

   KNOWN GAP: sub-agents dispatched from one session share the parent's
   `session_id` in the hook payload -- established 2026-08-19 by a peer agent's
   probe (a worker's tool call read AND mutated the parent's own `state/hooks/`
   record), not independently re-verified here. Both rules key
   identity on that id, so neither binds BETWEEN same-parent workers: rule 1
   reads a sibling's claim as "my own claim", and rule 2 sees zero peers. Both
   rules do bind between separate Claude sessions, which is what they cover.
   Closing this needs a payload field that distinguishes a worker from its
   parent, and no such field is currently known.

Rule 1 alone was decoration: a project running eight days with zero claims
never had a contested path, so the guard never fired, and the drop was silent.
Rule 2 makes an empty `state/files/` impossible to reach quietly.

Registration is no longer the agent's job either. `ensure_session()` writes
this session's record on the first guarded write, so rule 2 always has a truth
to read.

What it deliberately allows:
  * a claim this session owns
  * a claim whose owner session is stale, closed, or unreadable
  * any write under `.agents/` -- claiming is itself a write, so guarding it
    would deadlock
  * a path outside this workspace
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

# `ensure_session` renews on any guarded write, at most every 15 minutes, so a
# peer that is actually working beats at least that often. Two intervals of
# margin bounds what a hard kill can cost the next session.
PEER_TIMEOUT_MINUTES = 30

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

UNCLAIMED_MSG = """BLOCKED: `{path}` is not claimed, and another session is writing here.

  live peer   {peer}

With two agents live in one workspace a claim is the only thing that keeps you
off work that no `git status` will show you. Claim what you are about to edit,
then repeat the edit.

  1. write `.agents/mpi-kanban/state/files/<uuid>.json`

     {{"schema": "mpi-kanban/file-claim/v1", "id": "<uuid>",
      "paths": ["{path}"], "status": "claimed", "claim_kind": "write",
      "owner_session": "{session}",
      "heartbeat_at": "<ISO-8601>"}}

  2. append that record path to `active_file_claims` in
     `.agents/mpi-kanban/state/index.json`

Release it when the work lands (`status: complete`). Full lifecycle:
`${{CLAUDE_PLUGIN_ROOT}}/skills/mpi-lib/coordination-ops/lifecycle.md`."""


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
        if not _mpi.live_session(owner, timeout_minutes, now):
            continue
        return record_path, record.get("owner_session") or owner.get("id") or "unknown"
    return None


def guarded(candidate):
    """Is this a path rule 2 should ask for a claim on?"""
    candidate = (candidate or "").replace(os.sep, "/")
    # Spelled out rather than `os.path.isabs`, which stopped calling `/etc/x`
    # absolute on Windows in Python 3.13.
    outside = (not candidate or candidate.startswith("../")
               or candidate.startswith("/") or candidate[1:2] == ":")
    if outside:
        return False
    return not candidate.startswith(".agents/")


def owns_claim(candidate, claims, my_session_id):
    """Does this session already hold a live claim covering the path?"""
    for _record_path, record, owner in claims:
        if not isinstance(record, dict) or record.get("status") != "claimed":
            continue
        if not isinstance(owner, dict):
            continue
        if owner.get("claude_session_id") != my_session_id:
            continue
        if any(_mpi.claim_covers(entry, candidate) for entry in _mpi.claim_paths(record)):
            return True
    return False


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
    session_id = data.get("session_id")
    mine = _mpi.ensure_session(root, session_id, now)

    for candidate in candidates:
        hit = blocking_claim(candidate, claims, session_id, timeout, now)
        if hit:
            record_path, owner = hit
            _mpi.deny(BLOCK_MSG.format(path=candidate, record=record_path, owner=owner))

    peers = _mpi.live_peers(root, session_id, PEER_TIMEOUT_MINUTES, now)
    if not peers:
        sys.exit(0)  # alone: nobody to collide with, so nothing to pay for
    for candidate in candidates:
        if not guarded(candidate) or owns_claim(candidate, claims, session_id):
            continue
        _mpi.deny(UNCLAIMED_MSG.format(path=candidate, peer=peers[0],
                                       session=mine or "<this session>"))
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

    # rule 2: what still needs a claim, and what this session already covers
    assert guarded("src/App.tsx")
    assert not guarded(".agents/mpi-kanban/state/files/x.json"), "claiming is a write too"
    assert not guarded("C:/elsewhere/App.tsx") and not guarded("/etc/hosts")
    assert not guarded("../sibling/App.tsx")
    assert owns_claim("src/App.tsx", [("c1", single, mine)], "me")
    assert owns_claim("src/api/routes.py", [("c2", multi, mine)], "me"), "subtree covers"
    assert not owns_claim("src/App.tsx", [("c1", single, fresh)], "me"), "a peer's claim"
    assert not owns_claim("src/other.py", [("c1", single, mine)], "me")
    assert not owns_claim("src/App.tsx", [("c1", released, mine)], "me"), "not held"

    # the two windows are deliberately different lengths
    assert PEER_TIMEOUT_MINUTES < 120, "a dead peer must expire before a claim does"
    beat45 = dict(fresh, heartbeat_at="2026-08-09T11:15:00Z")
    assert _mpi.live_session(beat45, 120, now), "still owns its claim"
    assert not _mpi.live_session(beat45, PEER_TIMEOUT_MINUTES, now), "no longer a peer"
    print("guard-claim selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
