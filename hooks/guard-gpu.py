#!/usr/bin/env python3
"""PreToolUse guard: refuse a GPU command that is not holding a GPU lease.

The lease itself is `skills/mpi-lib/scripts/gpu_lease.py`. This binds it. A
lease an agent takes only when it remembers to is the file-claim failure again:
claims sat on disk for six weeks binding nothing because claiming was prose.

Enforcement is OPT-IN per project. Without a `gpu_command_patterns` list in
`.agents/mpi-kanban.local.md` this hook exits 0 and does nothing -- the plugin is
installed globally, and blocking every `pytest` in every adopted repo on the
chance it touches a GPU would be worse than the collision it prevents.

  ---
  gpu_command_patterns:
    - python .*(train|sweep|generate)
    - pytest .*-m gpu
  ---

Patterns are regexes matched against the raw command. A command already routed
through `gpu_lease.py` passes.

Deliberately NOT checked: whether a slot is free right now. Free at the moment
of the check is not free three seconds later when the command actually reaches
the device, so the rule is always wrap, never wrap-if-busy.

Exit 2 blocks the call and returns the stderr text to the agent.

Run self-check:  python guard-gpu.py --selftest
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mpi  # noqa: E402

CONFIG = ".agents/mpi-kanban.local.md"

BLOCK_MSG = """BLOCKED: this command uses the GPU without holding a lease.

  matched   {pattern}

Another agent -- in this repo or any other on this machine -- may be mid-sweep on
the same device right now. Two jobs on one card do not fail, they quietly return
results neither of you can trust.

Wrap it:

  python "${{CLAUDE_PLUGIN_ROOT}}/skills/mpi-lib/scripts/gpu_lease.py" run -- {command}

That takes a free device, sets `CUDA_VISIBLE_DEVICES` for the child, and waits
when every device is busy. Run it as a BACKGROUND Bash call so the waiting costs
you no tokens; the harness wakes you when it exits.

  python "${{CLAUDE_PLUGIN_ROOT}}/skills/mpi-lib/scripts/gpu_lease.py" status

names who is holding what. Never work around the lease by running the command
anyway -- a collision is invisible in the output."""


def configured_patterns(text):
    """`gpu_command_patterns` from the config frontmatter, as a list.

    ponytail: a five-line block-list reader, not a YAML parser. It reads the one
    shape the schema documents; anything else reads as unconfigured, which
    disables the guard rather than breaking the agent.
    """
    if not text:
        return []
    parts = text.split("---")
    if len(parts) < 3 or text.lstrip()[:3] != "---":
        return []
    found, collecting = [], False
    for line in parts[1].splitlines():
        if re.match(r"^\s*gpu_command_patterns\s*:\s*$", line):
            collecting = True
            continue
        if collecting:
            item = re.match(r"^\s+-\s+(.*\S)\s*$", line)
            if not item:
                break
            found.append(item.group(1).strip("'\""))
    return found


def offending(command, patterns):
    """The first pattern this unleased command matches, or None."""
    if not command or "gpu_lease.py" in command:
        return None
    for pattern in patterns:
        try:
            if re.search(pattern, command):
                return pattern
        except re.error:
            continue  # a bad regex disables itself, it does not block the agent
    return None


def main():
    data = _mpi.payload()
    if not data:
        sys.exit(0)
    root = _mpi.project_root(data)
    if not _mpi.adopted(root):
        sys.exit(0)
    if data.get("tool_name") != "Bash":
        sys.exit(0)

    try:
        with open(os.path.join(root, CONFIG), encoding="utf-8-sig") as handle:
            patterns = configured_patterns(handle.read())
    except OSError:
        sys.exit(0)
    if not patterns:
        sys.exit(0)

    command = (data.get("tool_input") or {}).get("command")
    hit = offending(command, patterns)
    if hit:
        _mpi.deny(BLOCK_MSG.format(pattern=hit, command=command))
    sys.exit(0)


def _selftest():
    config = "\n".join([
        "---",
        "rules_dir: .agents/rules",
        "gpu_command_patterns:",
        "  - python .*(train|sweep)",
        '  - "pytest .*-m gpu"',
        "critical_snapshot_file: AGENTS.md",
        "---",
        "",
        "# notes",
    ])
    patterns = configured_patterns(config)
    assert patterns == ["python .*(train|sweep)", "pytest .*-m gpu"], patterns
    assert configured_patterns("---\nrules_dir: x\n---\n") == [], "absent means off"
    assert configured_patterns("") == []
    assert configured_patterns("# no frontmatter\ngpu_command_patterns:\n  - x\n") == []

    assert offending("python train.py --steps 10", patterns)
    assert offending("pytest tests -m gpu", patterns)
    assert not offending("pytest tests -m unit", patterns)
    assert not offending("git status", patterns)
    assert not offending("", patterns)
    assert not offending(
        'python "/plugin/skills/mpi-lib/scripts/gpu_lease.py" run -- python train.py',
        patterns), "the wrapped form must pass"
    assert not offending("python train.py", ["(unclosed"]), "a bad regex disables itself"
    print("guard-gpu selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
