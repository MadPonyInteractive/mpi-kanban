#!/usr/bin/env python3
"""PreToolUse guard: refuse the two shell forms that fail silently on Windows.

838 `Command Failed` events in the measured data, a large share of them this
class. Both forms are *quoting* failures, not logic failures, which is why they
are so expensive: the command parses, runs, exits 0, and does the wrong thing.

What it blocks:

1. **Heredocs** (`cmd <<EOF` ... `EOF`). Git Bash on Windows mangles quoting in
   a heredoc and HALVES backslashes even inside a quoted delimiter, so a regex
   or a Windows path arrives silently altered. Code written that way parses
   cleanly and never fires.
2. **Backslash-newline line continuations.** The same halving, plus the shell
   and the tool layer disagree about where the command ends.

What it deliberately allows:

  * any single-line command, including one containing `<<`
  * `<<<` herestrings
  * a multi-line SINGLE-QUOTED `python -c '...'`, which is the sanctioned form
  * every command in a project with no `board.json`

Detection is deliberately narrow. A heredoc opener is only recognised when the
delimiter ends its line AND the command spans lines -- a real heredoc always
does both. That is what keeps `grep 'cout << x'` and `python -c 'print(a << 2)'`
out of the blast radius.

Exit 2 blocks the call and returns the stderr text to the agent.

Run self-check:  python guard-shell.py --selftest
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mpi  # noqa: E402

# `<<` (never `<<<`), optional `-`, an optionally quoted word, then end of line.
HEREDOC = re.compile(r"(?<!<)<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[ \t]*$", re.M)
CONTINUATION = re.compile(r"\\[ \t]*\r?\n")

HEREDOC_MSG = """BLOCKED: this command opens a heredoc (`<<{delim}`).

Git Bash on Windows mangles quoting inside a heredoc and halves backslashes even
with a quoted delimiter. The command still exits 0, so the damage is invisible:
a regex arrives matching nothing, a Windows path arrives broken.

Do this instead:
  * write the file with the Write tool and run it by path:
        python C:/.../scratchpad/edit.py
  * or pass it inline, SINGLE-quoted, on one logical line:
        python -c 'import re; ...'

Never rebuild the heredoc with different quoting -- the halving is in the shell,
not in your quoting."""

CONTINUATION_MSG = """BLOCKED: this command uses a backslash-newline continuation.

Backslashes are halved across the line break on this platform, so the flag or
path after the break is not the one you wrote.

Do this instead:
  * put the whole command on one line
  * or write a script with the Write tool and run it by path

One command per call, so a failure is attributable to it."""


def decide(command):
    """Return a block reason for a shell command, or None to allow."""
    if not isinstance(command, str) or "\n" not in command:
        return None  # a single-line command can be neither of these forms
    if CONTINUATION.search(command):
        return CONTINUATION_MSG
    opener = HEREDOC.search(command)
    if opener:
        return HEREDOC_MSG.format(delim=opener.group(2))
    return None


def main():
    data = _mpi.payload()
    if not data:
        sys.exit(0)
    if not _mpi.adopted(_mpi.project_root(data)):
        sys.exit(0)
    reason = decide((data.get("tool_input") or {}).get("command"))
    if reason:
        _mpi.deny(reason)
    sys.exit(0)


def _selftest():
    assert decide("cat <<EOF\nhello\nEOF")
    assert decide("cat <<'EOF'\nhello\nEOF"), "a quoted delimiter halves too"
    assert decide('cat <<-"EOF"\nhello\nEOF')
    assert decide("python - <<PY\nprint(1)\nPY")
    assert decide("grep -r foo \\\n  --include=*.py .")

    assert decide("cat <<EOF") is None, "single line cannot be a real heredoc"
    assert decide("git commit -m 'shift << 2'") is None
    assert decide("echo a\npython -c 'print(1 << 3)'") is None, "<< inside code"
    assert decide("grep 'cout << x' src/a.cpp\necho done") is None
    assert decide("python -c 'import re\nprint(re.escape(\"a\\\\b\"))'") is None
    assert decide("cmd <<< 'herestring'") is None
    assert decide("echo one\necho two") is None
    assert decide(None) is None
    print("guard-shell selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
