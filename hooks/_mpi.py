"""Shared helpers for the Mpi-Kanban PreToolUse guards.

Every guard is a no-op in a project that has no `.agents/mpi-kanban/board.json`:
the plugin is installed globally, so a hook that fires in an unadopted repo is a
bug, not enforcement.
"""
import datetime
import json
import os
import shlex
import sys

BOARD = ".agents/mpi-kanban/board.json"
STATE = ".agents/mpi-kanban/state"
SESSIONS = STATE + "/sessions"
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


# The desktop app drives a `PowerShell` tool that is SEPARATE from `Bash`, and
# names it the primary shell on Windows. A guard that tests `== "Bash"` exempts
# it silently, exactly as a guard registered only on the edit tools exempted
# `sed -i` before 1.0.1. Add a name here only alongside the `matcher` in
# `hooks.json`; the two have to agree or the guard is off on one side.
SHELL_TOOLS = ("Bash", "PowerShell")


def is_shell(data):
    """True when this tool call carries a shell command."""
    return (data.get("tool_name") in SHELL_TOOLS
            or "command" in (data.get("tool_input") or {}))


SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}
# Commands whose file operands are written, not read.
WRITERS = {"sed", "tee", "cp", "mv", "truncate", "install"}
# PowerShell cmdlets that write, lower-cased, aliases included. Value: which
# named parameter carries the written path, and which positional slot does.
PS_WRITERS = {
    "set-content": ("path", 0), "sc": ("path", 0),
    "add-content": ("path", 0), "ac": ("path", 0),
    "out-file": ("path", 0),
    "new-item": ("path", 0), "ni": ("path", 0),
    "copy-item": ("destination", 1), "cpi": ("destination", 1), "copy": ("destination", 1),
    "move-item": ("destination", 1), "mi": ("destination", 1), "move": ("destination", 1),
}
PS_PATH_PARAMS = {"path": {"-path", "-literalpath", "-filepath", "-lp", "-pspath"},
                  "destination": {"-destination"}}
# Named parameters that take a value, so the token after them is not positional.
# Anything else is read as a switch: a wrong guess there lets a write through,
# the safe direction, rather than blocking one on a bogus path.
PS_VALUE_PARAMS = {"-value", "-encoding", "-itemtype", "-type", "-name", "-width",
                   "-inputobject", "-filter", "-include", "-exclude", "-stream",
                   "-credential", "-delimiter", "-target"}


def _relative(target, root):
    """`target` as a workspace-relative POSIX path, or None if it escapes root.

    A target that starts with `$`, `~` or `%` is a variable or a home path the
    hook cannot expand; read literally it becomes a bogus repo path that no
    claim covers, so it is unknown, not guarded.
    """
    if not target or target.startswith("/dev/") or target[0] in "$~%":
        return None
    if not os.path.isabs(target):
        target = os.path.join(root, target)
    try:
        rel = os.path.relpath(target, root)
    except ValueError:  # different drive on Windows
        return None
    rel = rel.replace(os.sep, "/")
    return None if rel.startswith("../") or rel == ".." else rel


def outside_workspace(candidate):
    """Is this path outside the project root?

    `written_paths` deliberately reports the absolute path for an Edit outside
    the root, so both guards need one shared way to spot one. Spelled out
    rather than `os.path.isabs`, which stopped calling `/etc/x` absolute on
    Windows in Python 3.13.
    """
    candidate = (candidate or "").replace(os.sep, "/")
    return (not candidate or candidate.startswith("../")
            or candidate.startswith("/") or candidate[1:2] == ":")


def _ps_target(tokens):
    """The path a PowerShell writer cmdlet writes, or None."""
    param, slot = PS_WRITERS[tokens[0].lower()]
    positional, i = [], 1
    while i < len(tokens):
        token = tokens[i]
        if token in (">", ">>"):
            i += 2
            continue
        if token.startswith("-") and len(token) > 1:
            name, colon, value = token.partition(":")
            name = name.lower()
            if name in PS_PATH_PARAMS[param]:
                if colon:
                    return value or None
                return tokens[i + 1] if i + 1 < len(tokens) else None
            i += 1 if colon or name not in PS_VALUE_PARAMS else 2
            continue
        positional.append(token)
        i += 1
    return positional[slot] if len(positional) > slot else None


def bash_targets(command, powershell=False):
    """Raw paths a shell command writes to.

    ponytail: pattern-matched, not parsed. It sees `>`/`>>` redirects, `sed -i`,
    `tee`, `cp`, `mv`, `truncate` and `install`, and the PowerShell cmdlets in
    `PS_WRITERS` (MPI-47: registered on PowerShell since 1.5.0, they saw none
    of its own writers before that). It does NOT see a write hidden
    inside `python -c`, an interpreter script, a Makefile or a `$(...)`
    substitution -- those stay unguarded, and the answer there is to widen this
    list, not to parse the shell. False negatives are the safe direction: a
    missed write is the behaviour that shipped in 1.0.0, a false block is a new
    way to stop the agent working.
    """
    found = []
    for tokens in _segments(command, powershell):
        i = 0
        redirected = set()
        while i < len(tokens):
            if tokens[i] in (">", ">>") and i + 1 < len(tokens):
                found.append(tokens[i + 1])
                redirected.add(i + 1)
                i += 2
                continue
            i += 1
        if tokens[0].lower() in PS_WRITERS:
            target = _ps_target(tokens)
            if target:
                found.append(target)
            continue
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


def _segments(command, powershell=False):
    """The command's tokens, split at `&&`, `||`, `;` and `|`.

    `shlex` with `punctuation_chars` is what makes this safe: it keeps a quoted
    `'s|a|b|'` or a `grep 'x >> y'` intact, which a regex split over the raw
    string cannot, and it hands back `>` and `>>` as their own tokens.

    PowerShell is lexed non-POSIX: its escape is the backtick, and POSIX mode
    eats the backslashes of `skills\\mpi-lib\\x.py`, turning a real path into a
    bogus one that no claim covers. Non-POSIX keeps the quotes, so strip them.
    """
    lexer = shlex.shlex(command or "", posix=not powershell, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:  # an unbalanced quote: read nothing rather than guess
        return []
    if powershell:
        tokens = [t[1:-1] if len(t) > 1 and t[0] == t[-1] and t[0] in "'\"" else t
                  for t in tokens]
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
        for raw in bash_targets(tool_input.get("command"),
                                data.get("tool_name") == "PowerShell"):
            rel = _relative(raw, root)
            if rel and rel not in seen:
                seen.append(rel)
        return seen
    return []


def parse_stamp(value):
    """An ISO-8601 stamp as an aware datetime, or None when it is unusable."""
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=datetime.timezone.utc)


def live_session(record, timeout_minutes, now):
    """Is this session record still running?"""
    if not isinstance(record, dict) or record.get("status") != "active":
        return False
    beat = parse_stamp(record.get("heartbeat_at"))
    if beat is None:
        return False
    return (now - beat) <= datetime.timedelta(minutes=timeout_minutes)


def ensure_session(root, session_id, now, renew_after_minutes=15):
    """Create or renew this Claude session's coordination record.

    Registration used to be prose in `mpi-continue`, so it stopped happening:
    the project that uses the pack hardest went eight days with zero session
    records and zero file claims, and nothing noticed. A hook cannot forget.

    The record is named by the Claude session id, so there is one per session
    however many times this runs, and no index write to race another process.
    """
    if not session_id:
        return None
    rel = "%s/%s.json" % (SESSIONS, session_id)
    path = os.path.join(root, rel)
    record = read_json(path)
    if not isinstance(record, dict):
        record = {"schema": "mpi-kanban/session/v1", "id": session_id,
                  "role": "implementer", "claude_session_id": session_id,
                  "started_at": _stamp(now),
                  "allowed_actions": ["read", "edit", "verify", "implement"]}
    elif live_session(record, renew_after_minutes, now):
        return rel  # ponytail: a beat this fresh does not need rewriting
    record["status"] = "active"
    record["heartbeat_at"] = _stamp(now)
    write_json(path, record)
    return rel


def live_peers(root, session_id, timeout_minutes, now):
    """Paths of OTHER sessions currently writing in this workspace.

    Read from the directory, not from `index.json`: two Claude windows renewing
    the same index would race, and the directory is the same few files either
    way.
    """
    found = []
    directory = os.path.join(root, SESSIONS)
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return found
    for name in names:
        if not name.endswith(".json"):
            continue
        record = read_json(os.path.join(directory, name))
        if not isinstance(record, dict):
            continue
        if record.get("claude_session_id") == session_id:
            continue
        if live_session(record, timeout_minutes, now):
            found.append(SESSIONS + "/" + name)
    return found


def session_state(root, session_id):
    """Per-Claude-session guard state. Keyed by the hook payload's session_id."""
    path = os.path.join(root, HOOK_STATE, f"{session_id}.json")
    return path, (read_json(path) or {})


def write_json(path, obj):
    """Atomic write, so a reader never sees a half-written record."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2)
    os.replace(tmp, path)


def write_session_state(path, state):
    write_json(path, state)


def _stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


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
    assert bash("echo x > $TEMP/a.txt") == [], "a variable is unknown, not a repo path"
    assert bash("cp a.py ~/b.py") == [] and bash("echo x > %TEMP%\\a.txt") == []

    def ps(command):
        return written_paths({"cwd": root, "tool_name": "PowerShell",
                              "tool_input": {"command": command}})

    # PowerShell's own writers (MPI-47)
    assert ps("Set-Content -Path src\\a.py -Value 'x'") == ["src/a.py"], "backslashes survive"
    assert ps("Set-Content src/a.py 'x'") == ["src/a.py"], "positional path"
    assert ps("set-content -Value x -Encoding utf8 'a b.py'") == ["a b.py"], "case, quotes"
    assert ps("Add-Content -LiteralPath:notes.md -Value x") == ["notes.md"], "colon form"
    assert ps("'x' | Out-File -FilePath out.txt -Encoding utf8") == ["out.txt"]
    assert ps("Get-Content a | Out-File out.txt") == ["out.txt"]
    assert ps("New-Item -ItemType File -Path src/new.py -Force") == ["src/new.py"]
    assert ps("Copy-Item src/a.py src/b.py") == ["src/b.py"], "only the destination"
    assert ps("Copy-Item -Path src/a.py -Destination src/b.py") == ["src/b.py"]
    assert ps("Move-Item -Destination dst.py -Path src.py") == ["dst.py"]
    assert ps("cpi a.py b.py; mi c.py d.py") == ["b.py", "d.py"], "aliases"
    assert ps("Set-Content -Path $env:TEMP\\x.txt -Value 1") == []
    assert ps("Get-Content src/a.py") == [] and ps("Copy-Item a.py") == []
    assert ps("echo x > notes.md") == ["notes.md"], "redirects still count"

    # Edit/Write keep naming their own target
    assert written_paths({"cwd": root,
                          "tool_input": {"file_path": os.path.join(root, "src", "a.py")}}) \
        == ["src/a.py"]

    now = datetime.datetime(2026, 8, 19, 12, 0, tzinfo=datetime.timezone.utc)
    assert live_session({"status": "active", "heartbeat_at": "2026-08-19T11:30:00Z"}, 120, now)
    assert not live_session({"status": "closed", "heartbeat_at": "2026-08-19T11:59:00Z"}, 120, now)
    assert not live_session({"status": "active", "heartbeat_at": "2026-08-19T02:00:00Z"}, 120, now)
    assert not live_session({"status": "active"}, 120, now), "no beat is not alive"
    assert parse_stamp("2026-08-19T11:30:00Z") == parse_stamp("2026-08-19T11:30:00+00:00")
    assert parse_stamp("not a date") is None
    assert ensure_session(root, None, now) is None, "no session id, no record"
    print("_mpi selftest OK")


if __name__ == "__main__":
    _selftest()
