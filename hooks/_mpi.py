"""Shared helpers for the Mpi-Kanban PreToolUse guards.

Every guard is a no-op in a project that has no `.agents/mpi-kanban/board.json`:
the plugin is installed globally, so a hook that fires in an unadopted repo is a
bug, not enforcement.
"""
import json
import os
import shlex
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


SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}
# Commands whose file operands are written, not read.
WRITERS = {"sed", "tee", "cp", "mv", "truncate", "install"}


def _relative(target, root):
    """`target` as a workspace-relative POSIX path, or None if it escapes root."""
    if not target or target.startswith("/dev/"):
        return None
    if not os.path.isabs(target):
        target = os.path.join(root, target)
    try:
        rel = os.path.relpath(target, root)
    except ValueError:  # different drive on Windows
        return None
    rel = rel.replace(os.sep, "/")
    return None if rel.startswith("../") or rel == ".." else rel


def bash_targets(command):
    """Raw paths a shell command writes to.

    ponytail: pattern-matched, not parsed. It sees `>`/`>>` redirects, `sed -i`,
    `tee`, `cp`, `mv`, `truncate` and `install`. It does NOT see a write hidden
    inside `python -c`, an interpreter script, a Makefile or a `$(...)`
    substitution -- those stay unguarded, and the answer there is to widen this
    list, not to parse the shell. False negatives are the safe direction: a
    missed write is the behaviour that shipped in 1.0.0, a false block is a new
    way to stop the agent working.
    """
    found = []
    for tokens in _segments(command):
        i = 0
        redirected = set()
        while i < len(tokens):
            if tokens[i] in (">", ">>") and i + 1 < len(tokens):
                found.append(tokens[i + 1])
                redirected.add(i + 1)
                i += 2
                continue
            i += 1
        verb = os.path.basename(tokens[0])
        if verb not in WRITERS:
            continue
        operands = [t for n, t in enumerate(tokens)
                    if n and n not in redirected and not t.startswith("-")
                    and t not in (">", ">>")]
        if verb == "sed":
            if not any(t.startswith("-i") or t.startswith("--in-place") for t in tokens[1:]):
                continue
            operands = operands[1:]  # the first operand is the script
        elif verb in ("cp", "mv", "install"):
            operands = operands[-1:]  # only the destination is written
        found.extend(operands)
    return found


def _segments(command):
    """The command's tokens, split at `&&`, `||`, `;` and `|`.

    `shlex` with `punctuation_chars` is what makes this safe: it keeps a quoted
    `'s|a|b|'` or a `grep 'x >> y'` intact, which a regex split over the raw
    string cannot, and it hands back `>` and `>>` as their own tokens.
    """
    lexer = shlex.shlex(command or "", posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:  # an unbalanced quote: read nothing rather than guess
        return []
    segments, current = [], []
    for token in tokens:
        if token in SEPARATORS:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    return segments


def written_paths(data):
    """Every workspace-relative path this tool call writes to.

    Edit/Write/NotebookEdit name their target outright. A Bash call has to be
    read out of the command, because the guards that matter -- the card and the
    claim -- are worth nothing if `sed -i` walks around them.
    """
    root = project_root(data)
    tool_input = data.get("tool_input") or {}
    target = tool_input.get("file_path")
    if target:
        rel = _relative(target, root)
        # An Edit tool call outside the project is still the agent's own edit;
        # keep the old behaviour of reporting it rather than dropping it.
        return [rel or target.replace(os.sep, "/")]
    if data.get("tool_name") == "Bash" or "command" in tool_input:
        seen = []
        for raw in bash_targets(tool_input.get("command")):
            rel = _relative(raw, root)
            if rel and rel not in seen:
                seen.append(rel)
        return seen
    return []


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

    root = os.path.join(os.sep, "repo")

    def bash(command):
        return written_paths({"cwd": root, "tool_name": "Bash",
                              "tool_input": {"command": command}})

    # the bypass this exists to close
    assert bash("sed -i 's/a/b/' src/app.py") == ["src/app.py"]
    assert bash("cd /repo && sed -i.bak 's|a|b|' a.py b.py") == ["a.py", "b.py"]
    assert bash("sed -n '1,5p' src/app.py") == [], "a read is not a write"
    assert bash("echo hi > notes.md") == ["notes.md"]
    assert bash("echo hi >> notes.md") == ["notes.md"]
    assert bash("echo hi > notes.md") == bash("echo hi >notes.md")
    assert bash("cat x | tee out.txt") == ["out.txt"]
    assert bash("cp src/a.py src/b.py") == ["src/b.py"], "only the destination"
    assert bash("mv 'a b.py' 'c d.py'") == ["c d.py"], "quoted operands"
    assert bash("git status --short") == []
    assert bash("grep -n 'x >> y' src/app.py") == [], "a shift inside quotes"
    assert bash("python scripts/x.py > /dev/null") == []
    assert bash("python scripts/x.py 2>&1 | head") == []
    assert bash("sed -i 's/a/b/' /elsewhere/app.py") == [], "outside the project"
    assert bash("") == []

    # Edit/Write keep naming their own target
    assert written_paths({"cwd": root,
                          "tool_input": {"file_path": os.path.join(root, "src", "a.py")}}) \
        == ["src/a.py"]
    print("_mpi selftest OK")


if __name__ == "__main__":
    _selftest()
