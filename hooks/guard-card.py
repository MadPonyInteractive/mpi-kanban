#!/usr/bin/env python3
"""PreToolUse guard: one card per session, and no code edit without one.

Two symmetric rules, both delivered where the decision happens rather than in a
skill that has to be invoked first:

1. No card in `doing` and the session is about to edit code -> block ONCE, with
   the card contract inline and the file named, so ownership is seeded from the
   real first touch instead of a guess at card-creation time.
2. A card was already created this session and another `tasks/<id>/task.json` is
   being created -> block, so the finding is folded into the active card.

Rule 2 is the `## Discovered work` rule, moved out of a skill that carried 2% of
usage and into the write itself. Both fire once per session: the point is to
seed the card, not to fight the agent.

Exit 2 blocks the call and returns the stderr text to the agent.

Run self-check:  python guard-card.py --selftest
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mpi  # noqa: E402

NEW_CARD = re.compile(r"^\.agents/mpi-kanban/tasks/[^/]+/task\.json$")

CARD_CONTRACT = """BLOCKED once: this session is editing `{path}` with no card in `doing`.

Create the card first, then repeat this edit -- it will not be blocked again.

Card contract (the VS Code board renders anything else as an invalid card):

  columns    todo | doing | done
  maturity   todo   -> idea, planned, research, needs-decision, blocked, deferred
             doing  -> in-progress, validating
             done   -> complete, rejected

  .agents/mpi-kanban/tasks/<id>/task.json, id from board.json `next_id`,
  column `doing`, maturity `in-progress`, and `files.json` seeded with
  `{path}` -- the file you are actually touching.

If this edit is a one-line fix the user asked for directly and no card is
wanted, say so in one line and repeat the edit."""

SECOND_CARD = """BLOCKED: this session already created card {first}.

You are creating a second card at `{path}`. Card sprawl is the failure mode
here: one unit of work, many half-cards, none of them finished.

Fold the finding into {first} -- its checklist, its plan, or its description.
Create a separate card only when the user asked for one in this request, or when
the work is genuinely unrelated to {first}; if so, say which in one line and
repeat the write."""


def decide(rel_path, doing_cards, state):
    """Return (reason, state_update) -- reason None means allow.

    Pure, so the self-check below covers the branching without a live board.
    """
    if rel_path is None:
        return None, None
    if NEW_CARD.match(rel_path):
        first = state.get("card_created")
        if first and first not in rel_path:
            if state.get("second_card_prompted") == rel_path:
                return None, None
            return (SECOND_CARD.format(first=first, path=rel_path),
                    {"second_card_prompted": rel_path})
        if not first:
            card_id = rel_path.split("/")[3]
            return None, {"card_created": card_id}
        return None, None
    if rel_path.startswith(".agents/"):
        return None, None
    if doing_cards or state.get("card_prompted"):
        return None, None
    return CARD_CONTRACT.format(path=rel_path), {"card_prompted": True}


def main():
    data = _mpi.payload()
    if not data:
        sys.exit(0)
    root = _mpi.project_root(data)
    if not _mpi.adopted(root):
        sys.exit(0)

    board = _mpi.read_json(os.path.join(root, _mpi.BOARD)) or {}
    doing = (board.get("columns") or {}).get("doing") or []
    path, state = _mpi.session_state(root, data.get("session_id", "unknown"))

    reason, update = decide(_mpi.edited_path(data), doing, state)
    if update:
        state.update(update)
        _mpi.write_session_state(path, state)
    if reason:
        _mpi.deny(reason)
    sys.exit(0)


def _selftest():
    card = ".agents/mpi-kanban/tasks/MPI-9/task.json"

    # 1. code edit, no card in doing -> blocked once, then allowed
    reason, update = decide("src/app.py", [], {})
    assert reason and "no card in `doing`" in reason
    assert update == {"card_prompted": True}
    assert decide("src/app.py", [], {"card_prompted": True}) == (None, None)

    # 2. code edit with a card in doing -> allowed
    assert decide("src/app.py", ["MPI-9"], {}) == (None, None)

    # 3. coordination state is never blocked
    assert decide(".agents/mpi-kanban/board.json", [], {}) == (None, None)

    # 4. first card of the session is recorded, second is blocked
    reason, update = decide(card, [], {})
    assert reason is None and update == {"card_created": "MPI-9"}
    second = ".agents/mpi-kanban/tasks/MPI-10/task.json"
    reason, update = decide(second, [], {"card_created": "MPI-9"})
    assert reason and "already created card MPI-9" in reason
    assert update == {"second_card_prompted": second}

    # 4b. the message promises the write can be repeated, so the retry passes
    assert decide(second, [], {"card_created": "MPI-9",
                               "second_card_prompted": second}) == (None, None)
    reason, _ = decide(".agents/mpi-kanban/tasks/MPI-11/task.json", [],
                       {"card_created": "MPI-9", "second_card_prompted": second})
    assert reason and "already created card MPI-9" in reason

    # 5. rewriting the same card is not a second card
    assert decide(card, [], {"card_created": "MPI-9"}) == (None, None)

    print("guard-card selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
