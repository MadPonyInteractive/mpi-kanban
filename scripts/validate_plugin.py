"""Validate the Mpi-Kanban universal Agent Skills pack before release."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The live-board rules ship with the pack; import them rather than keeping a
# second copy here, so the maturity enum has one code-level source of truth.
sys.path.insert(0, str(ROOT / "skills" / "mpi-lib" / "scripts"))
try:
    import validate_board as board_rules
except ImportError as exc:  # pragma: no cover - a missing shipped script is a pack failure
    print(f"skills/mpi-lib/scripts/validate_board.py could not be imported: {exc}", file=sys.stderr)
    sys.exit(1)

TASK_COLUMNS = board_rules.TASK_COLUMNS
TASK_MATURITIES = board_rules.TASK_MATURITIES
TASK_MATURITY_BY_COLUMN = board_rules.TASK_MATURITY_BY_COLUMN
TASK_REQUIRED_FIELDS = board_rules.TASK_REQUIRED_FIELDS

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024

# A SKILL.md body is loaded in full every time the skill triggers, so length is
# a per-invocation token cost, not a one-off. 200 lines is the budget; anything
# longer belongs behind a pointer in skills/mpi-lib/. The overrides below are
# skills that were already over when the budget landed - they are a ratchet, so
# each may shrink but never grow, and lowering an entry is the way to pay one
# down. Do not add a new name here; split the skill instead.
SKILL_LINE_BUDGET = 200
SKILL_LINE_GRANDFATHERED = {
    "mpi-continue": 601,
    "mpi-end-session": 394,
    "mpi-project-refresh": 335,
    "mpi-init": 306,
    "mpi-execute-parallel": 277,
}
INVALID_MATURITY_EXAMPLES = {
    "active",
    "accepted",
    "done",
    "implementing",
    "implementation",
    "validated",
    "validation",
    "spec",
}
MESSAGE_STATUSES = {"open", "acknowledged", "replied", "resolved", "superseded", "closed"}
OPEN_MESSAGE_STATUSES = {"open", "acknowledged", "replied"}
MESSAGE_SELECTORS = {"session", "agent", "role", "task", "file", "workspace", "user"}
ACTIVE_KANBAN_REF = re.compile(
    r"\b(read|edit|update|continue|use|open|boot|load|mutate|write)\b.{0,80}"
    r"(\.agents/mpi-kanban/kanban\.md|\.claude/mpi-kanban/kanban\.md)",
    re.IGNORECASE,
)
LEGACY_CONTEXT = re.compile(
    r"\b(legacy|snapshot|migration|migrate|compatibility|tombstone|superseded|"
    r"not the primary|not a live|not as canonical|do not edit)\b",
    re.IGNORECASE,
)

PLUGIN_ROOT = "$" + "{CLAUDE_PLUGIN_ROOT}"
PLUGIN_LIB = PLUGIN_ROOT + "/skills/mpi-lib"
MANIFEST = ".claude-plugin/plugin.json"
MARKETPLACE = ".claude-plugin/marketplace.json"
SCRIPT_REF = r"hooks/[A-Za-z0-9_./-]+[.]py"
HOOK_EVENTS = {
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "PostCompact",
    "Notification",
}

REMOVED_PATHS = (
    "skills.sh.json",
    ".codex-plugin",
    ".agents/plugins",
    "plugins/MadPonyInteractive/mpi-kanban",
    "scripts/build_kilo_skills.py",
    "scripts/register_codex_plugin.py",
    "docs/kilocode-install.md",
    "docs/kilocode-marketplace-submission.md",
    "templates/kilo.jsonc",
    "update_live.py",
    "skills/mpi-nimbalyst-sync",
    "skills/mpi-lib/interop-ops",
    "skills/mpi-lib/templates/interop.json",
    "skills/mpi-lib/kanban-ops",
    "skills/mpi-lib/templates/kanban.md",
    "docs/coordination",
    "skills/mpi-init/templates/kanban.md",
    "docs/nimbalyst-interop.md",
)

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def parse_frontmatter(text: str) -> dict[str, object] | None:
    text = text.lstrip("\ufeff")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    block = text[4:end]
    data: dict[str, object] = {}
    current_parent: str | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") and current_parent:
            key, _, value = line.strip().partition(":")
            parent = data.setdefault(current_parent, {})
            if isinstance(parent, dict):
                parent[key.strip()] = value.strip().strip('"')
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        current_parent = key.strip()
        value = value.strip()
        if value:
            data[current_parent] = value.strip('"')
    return data


def skill_dirs() -> list[Path]:
    skills = ROOT / "skills"
    if not skills.is_dir():
        fail("missing skills/ directory")
        return []
    return sorted(path for path in skills.iterdir() if path.is_dir())


def validate_skills() -> set[str]:
    names: set[str] = set()
    for skill_dir in skill_dirs():
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            fail(f"{skill_dir.name}: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        front = parse_frontmatter(text)
        if front is None:
            fail(f"{skill_dir.name}/SKILL.md: invalid or missing YAML frontmatter")
            continue

        name = str(front.get("name", ""))
        description = str(front.get("description", ""))
        names.add(name)

        if name != skill_dir.name:
            fail(f"{skill_dir.name}/SKILL.md: frontmatter name '{name}' does not match folder name")
        if not KEBAB.match(name):
            fail(f"{skill_dir.name}/SKILL.md: name '{name}' is not kebab-case")
        if len(name) > NAME_MAX:
            fail(f"{skill_dir.name}/SKILL.md: name exceeds {NAME_MAX} characters")
        if not description:
            fail(f"{skill_dir.name}/SKILL.md: empty description")
        if len(description) > DESCRIPTION_MAX:
            fail(f"{skill_dir.name}/SKILL.md: description exceeds {DESCRIPTION_MAX} characters")

        if skill_dir.name != "mpi-lib" and not description.startswith("MPI workflow pack - "):
            fail(f"{skill_dir.name}/SKILL.md: description must start with 'MPI workflow pack - '")

    return names


def validate_skill_sizes() -> None:
    """Skill bodies are a recurring token cost; hold the line on their length."""
    for skill_dir in skill_dirs():
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        lines = len(skill_md.read_text(encoding="utf-8").splitlines())
        name = skill_dir.name
        if name in SKILL_LINE_GRANDFATHERED:
            allowed = SKILL_LINE_GRANDFATHERED[name]
            if lines > allowed:
                fail(
                    f"{name}/SKILL.md: {lines} lines exceeds its grandfathered "
                    f"ceiling of {allowed}. Move detail behind a pointer in "
                    "skills/mpi-lib/ rather than raising the ceiling."
                )
            elif lines < allowed:
                fail(
                    f"{name}/SKILL.md: {lines} lines is under its grandfathered "
                    f"ceiling of {allowed}. Lower SKILL_LINE_GRANDFATHERED to "
                    f"{lines} so the ratchet holds."
                )
        elif lines > SKILL_LINE_BUDGET:
            fail(
                f"{name}/SKILL.md: {lines} lines exceeds the {SKILL_LINE_BUDGET}-line "
                "budget. Split it, or move reference detail into skills/mpi-lib/."
            )


def validate_mpi_lib_present() -> None:
    mpi_lib = ROOT / "skills" / "mpi-lib"
    if not (mpi_lib / "SKILL.md").exists():
        fail("missing skills/mpi-lib/SKILL.md")
        return

    required = (
        "coordination-ops/lifecycle.md",
        "coordination-ops/statuses.md",
        "task-board-ops/_schema.md",
        "task-board-ops/read.md",
        "task-board-ops/mutate.md",
        "task-board-ops/migrate.md",
        "task-board-ops/validate.md",
        "project-knowledge/indexing.md",
        "scripts/validate_board.py",
        "scripts/task_ops.py",
        "scripts/new_uuid.py",
        "docs/coordination/README.md",
        "templates/board.json",
        "templates/task.json",
        "templates/project-profile.md",
        "templates/project-knowledge-index.md",
        "templates/rule.md",
        "templates/behaviour-rules.md",
        "templates/worker-agent.md",
    )
    for rel in required:
        if not (mpi_lib / rel).exists():
            fail(f"mpi-lib missing required reference: {rel}")



def validate_pack_version() -> None:
    """The mpi-lib version stamp is what a project compares against.

    It sat at 0.8.4 through two releases because nothing checked it, which is
    exactly the silent staleness the stamp exists to detect.
    """
    manifest = load_json(ROOT / MANIFEST, "plugin.json")
    stamped = manifest.get("version") if isinstance(manifest, dict) else None
    if not stamped:
        fail(f"{MANIFEST}: missing version stamp")
        return

    changelog = ROOT / "CHANGELOG.md"
    if not changelog.exists():
        fail("missing CHANGELOG.md; cannot check the mpi-lib version stamp")
        return
    released = re.search(
        r"^## \[(\d+\.\d+\.\d+)\]", changelog.read_text(encoding="utf-8"), re.MULTILINE
    )
    if not released:
        fail("CHANGELOG.md: no released `## [x.y.z]` heading found")
        return
    if stamped != released.group(1):
        fail(
            f"{MANIFEST} version is {stamped} but the latest "
            f"CHANGELOG release is {released.group(1)}; bump the stamp or the pack "
            "ships claiming to be an older release"
        )

    # The stamp is only useful if a project records one to compare it against.
    wiring = {
        "skills/mpi-lib/templates/project-profile.md": "pack_version:",
        "skills/mpi-init/SKILL.md": "pack_version",
        "skills/mpi-project-refresh/SKILL.md": "pack_version",
    }
    for rel, needle in wiring.items():
        path = ROOT / rel
        if not path.exists() or needle not in path.read_text(encoding="utf-8"):
            fail(f"{rel}: missing `{needle}`; stale-install detection is not wired up")


def load_json(path: Path, label: str) -> object | None:
    return board_rules.load_json(errors, path, label)


def validate_task_board_templates() -> None:
    board_path = ROOT / "skills" / "mpi-lib" / "templates" / "board.json"
    task_path = ROOT / "skills" / "mpi-lib" / "templates" / "task.json"

    board = load_json(board_path, str(board_path.relative_to(ROOT)))
    if not isinstance(board, dict):
        fail("templates/board.json must be a JSON object")
    else:
        if board.get("schema") != "mpi-kanban/board/v1":
            fail("templates/board.json must use schema mpi-kanban/board/v1")
        if board.get("next_id") != 1:
            fail("templates/board.json next_id must start at 1")
        columns = board.get("columns")
        if not isinstance(columns, dict) or tuple(columns.keys()) != TASK_COLUMNS:
            fail("templates/board.json columns must be exactly todo, doing, done")
        elif any(columns[column] != [] for column in TASK_COLUMNS):
            fail("templates/board.json columns must start empty")

    task = load_json(task_path, str(task_path.relative_to(ROOT)))
    if not isinstance(task, dict):
        fail("templates/task.json must be a JSON object")
    else:
        missing = TASK_REQUIRED_FIELDS - set(task)
        if missing:
            fail(f"templates/task.json missing required fields: {sorted(missing)}")
        if task.get("schema") != "mpi-kanban/task-card/v1":
            fail("templates/task.json must use schema mpi-kanban/task-card/v1")
        if task.get("id") != "MPI-1":
            fail("templates/task.json must use placeholder id MPI-1")
        if task.get("column") not in TASK_COLUMNS:
            fail("templates/task.json column must be todo, doing, or done")
        maturity = task.get("maturity")
        if maturity not in TASK_MATURITIES:
            fail("templates/task.json maturity must be one of idea, planned, research, needs-decision, blocked, deferred, in-progress, validating, complete, rejected")
        elif maturity not in TASK_MATURITY_BY_COLUMN.get(str(task.get("column")), set()):
            fail("templates/task.json maturity must match its column")
        if not isinstance(task.get("links"), dict):
            fail("templates/task.json links must be an object")


def validate_maturity_contract_docs() -> None:
    required_paths = [
        ROOT / "SPEC.md",
        ROOT / "skills" / "mpi-lib" / "task-board-ops" / "_schema.md",
        ROOT / "skills" / "mpi-lib" / "task-board-ops" / "mutate.md",
        ROOT / "skills" / "mpi-lib" / "task-board-ops" / "validate.md",
        ROOT / "skills" / "mpi-lib" / "templates" / "project-profile.md",
        # Inline copies. CLAUDE.md keeps these deliberately duplicated; this is
        # what keeps them honest as they multiply.
        ROOT / "skills" / "mpi-continue" / "SKILL.md",
        ROOT / "skills" / "mpi-execute-parallel" / "SKILL.md",
    ]
    enum_values = TASK_MATURITIES
    for path in required_paths:
        if not path.exists():
            fail(f"missing maturity contract doc: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for value in enum_values:
            if value not in text:
                fail(f"{path.relative_to(ROOT)} does not document maturity value {value!r}")
        for value in INVALID_MATURITY_EXAMPLES:
            if value not in lower:
                fail(f"{path.relative_to(ROOT)} does not reject invalid maturity example {value!r}")

    # Any other shipped doc that enumerates the enum must carry all of it. The
    # explicit list above says "these files MUST document it"; this says "and
    # nowhere else may document a stale subset of it". mpi-project-refresh
    # carried the pre-MPI-22 five-value list for a full release without this.
    checked = set(required_paths)
    for path in (ROOT / "skills").rglob("*.md"):
        if path in checked:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # "`idea`, `planned`" is how every real enum listing opens. A legacy
        # column-mapping table mentions single values and must not trip this.
        if "`idea`, `planned`" not in text:
            continue
        missing = [value for value in enum_values if f"`{value}`" not in text]
        if missing:
            fail(
                f"{path.relative_to(ROOT)} enumerates task maturities but omits "
                + ", ".join(repr(value) for value in missing)
            )

    # The board page paints one colour per maturity. A value missing from its map
    # is not a broken page -- it renders as the invalid red, which reads as a bad
    # card rather than a stale copy of the enum. Only a check catches that.
    page = ROOT / "skills" / "mpi-lib" / "scripts" / "board.html"
    if not page.exists():
        fail(f"missing maturity contract doc: {page.relative_to(ROOT)}")
    else:
        text = page.read_text(encoding="utf-8", errors="ignore")
        missing = [value for value in enum_values if f'"{value}":' not in text]
        if missing:
            fail(
                f"{page.relative_to(ROOT)} has no colour for maturity "
                + ", ".join(repr(value) for value in missing)
            )


def validate_task_board_tree() -> None:
    for message in board_rules.validate_board(ROOT):
        fail(message)


def validate_boot_docs() -> None:
    boot_docs = [
        ROOT / "START-HERE.md",
        ROOT / "AGENTS.md",
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
        ROOT / ".agents" / "mpi-kanban" / "project-profile.md",
        ROOT / ".agents" / "mpi-kanban" / "project-knowledge-index.md",
    ]
    for path in boot_docs:
        if not path.exists():
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if ACTIVE_KANBAN_REF.search(line) and not LEGACY_CONTEXT.search(line):
                fail(
                    f"{path.relative_to(ROOT)}:{line_number} appears to route active work through legacy kanban.md"
                )


def validate_coordination_messages() -> None:
    state_root = ROOT / ".agents" / "mpi-kanban" / "state"
    index_path = state_root / "index.json"
    if not index_path.exists():
        return
    index = load_json(index_path, ".agents/mpi-kanban/state/index.json")
    if not isinstance(index, dict):
        return
    open_messages = index.get("open_messages", [])
    if open_messages is None:
        return
    if not isinstance(open_messages, list):
        fail(".agents/mpi-kanban/state/index.json open_messages must be a list")
        return

    pointed = set()
    for value in open_messages:
        if not isinstance(value, str):
            fail(".agents/mpi-kanban/state/index.json open_messages entries must be strings")
            continue
        pointed.add(value)
        path = ROOT / value
        if not path.exists():
            fail(f".agents/mpi-kanban/state/index.json open message is missing: {value}")
            continue
        message = load_json(path, value)
        if isinstance(message, dict) and message.get("status") not in OPEN_MESSAGE_STATUSES:
            fail(f"{value} is listed in open_messages with terminal status {message.get('status')!r}")

    messages_root = state_root / "messages"
    if messages_root.exists():
        for path in messages_root.glob("*.json"):
            label = str(path.relative_to(ROOT))
            message = load_json(path, label)
            if not isinstance(message, dict):
                continue
            if message.get("schema") != "mpi-kanban/message/v1":
                fail(f"{label} schema must be mpi-kanban/message/v1")
            if message.get("id") != path.stem:
                fail(f"{label} id must match filename")
            status = message.get("status")
            if status not in MESSAGE_STATUSES:
                fail(f"{label} status must be one of {sorted(MESSAGE_STATUSES)}")
            recipient = message.get("to")
            if not isinstance(recipient, dict) or recipient.get("selector") not in MESSAGE_SELECTORS:
                fail(f"{label} to.selector must be one of {sorted(MESSAGE_SELECTORS)}")
            for key in ("created_at", "updated_at", "from", "subject", "body", "thread", "recent_events"):
                if key not in message:
                    fail(f"{label} missing required field: {key}")
            pointer = label.replace("\\", "/")
            if status in OPEN_MESSAGE_STATUSES and pointer not in pointed:
                fail(f"{label} has unresolved status {status!r} but is missing from open_messages")
            if status not in OPEN_MESSAGE_STATUSES and pointer in pointed:
                fail(f"{label} has terminal status {status!r} but remains in open_messages")


def validate_no_stale_runtime_refs() -> None:
    patterns = (
        "<mpi-lib" + "-root>",
        "npx skills" + " add",
        "Codex" + " users",
        "~/.agents/skills" + "/mpi-lib",
    )
    active_roots = [ROOT / "skills"]
    active_files = [
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "docs" / "install.md",
    ]
    paths = active_files[:]
    for active_root in active_roots:
        if active_root.exists():
            paths.extend(path for path in active_root.rglob("*") if path.is_file())
    for path in paths:
        if not path.exists() or path.suffix.lower() not in {".md", ".json", ".py", ".yml", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern in text:
                fail(f"stale runtime reference '{pattern}' in {path.relative_to(ROOT)}")


def validate_coordination_wiring() -> None:
    """Guard the two ways coordination silently switched itself off (MPI-26)."""
    skills = ROOT / "skills"
    for path in skills.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"\S*scripts/new_uuid\.py", text):
            if match.group(0) != PLUGIN_LIB + "/scripts/new_uuid.py":
                fail(
                    f"{path.relative_to(ROOT)}: new_uuid.py reference "
                    f"{match.group(0)!r} is not anchored to {PLUGIN_LIB}"
                )

    init = skills / "mpi-init" / "SKILL.md"
    if init.exists() and "mpi-kanban.local.md" not in init.read_text(encoding="utf-8"):
        fail("mpi-init/SKILL.md must create .agents/mpi-kanban.local.md on adopt")
    refresh = skills / "mpi-project-refresh" / "SKILL.md"
    if refresh.exists() and "mpi-kanban.local.md" not in refresh.read_text(encoding="utf-8"):
        fail("mpi-project-refresh/SKILL.md must report a missing mpi-kanban.local.md")


def validate_lib_references() -> None:
    """A skill pointing at a deleted mpi-lib file sends the agent to a dead read."""
    pattern = re.compile(re.escape(PLUGIN_LIB) + r"/([A-Za-z0-9_./-]+)")
    for path in (ROOT / "skills").rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in pattern.finditer(text):
            rel = match.group(1).rstrip(".,;:)`")
            if not (ROOT / "skills" / "mpi-lib" / rel).exists():
                fail(f"{path.relative_to(ROOT)}: references missing mpi-lib/{rel}")


def validate_plugin_manifest(skill_names: set[str]) -> None:
    """The plugin manifest and its marketplace entry are the install contract."""
    manifest = load_json(ROOT / MANIFEST, "plugin.json")
    if isinstance(manifest, dict):
        if manifest.get("name") != "mpi-kanban":
            fail(f'{MANIFEST}: name must be "mpi-kanban"')
        for field in ("description", "version", "license", "repository"):
            if not manifest.get(field):
                fail(f"{MANIFEST}: missing {field}")

    market = load_json(ROOT / MARKETPLACE, "marketplace.json")
    if isinstance(market, dict):
        if not market.get("owner"):
            fail(f"{MARKETPLACE}: missing owner")
        entries = market.get("plugins")
        entries = entries if isinstance(entries, list) else []
        entry = next(
            (e for e in entries if isinstance(e, dict) and e.get("name") == "mpi-kanban"),
            None,
        )
        if entry is None:
            fail(f"{MARKETPLACE}: no mpi-kanban plugin entry")
        else:
            if entry.get("source") != "./":
                fail(f'{MARKETPLACE}: mpi-kanban source must be "./"')
            if "version" in entry:
                fail(
                    f"{MARKETPLACE}: the entry must not carry a version; "
                    "plugin.json is the only stamp"
                )

    if not skill_names:
        fail("no skills found under skills/")


def validate_plugin_hooks() -> None:
    """Hooks and agents are optional on disk, but must be well formed if present."""
    hooks_file = ROOT / "hooks" / "hooks.json"
    if hooks_file.exists():
        config = load_json(hooks_file, "hooks/hooks.json")
        events = config.get("hooks") if isinstance(config, dict) else None
        if not isinstance(events, dict) or not events:
            fail("hooks/hooks.json: missing a non-empty `hooks` object")
            events = {}
        for event, matchers in events.items():
            if event not in HOOK_EVENTS:
                fail(f"hooks/hooks.json: unknown hook event {event!r}")
            for matcher in matchers if isinstance(matchers, list) else []:
                for hook in (matcher or {}).get("hooks", []):
                    command = hook.get("command", "")
                    if hook.get("type") == "command" and PLUGIN_ROOT not in command:
                        fail(
                            f"hooks/hooks.json: {event} command is not anchored to "
                            f"{PLUGIN_ROOT}: {command!r}"
                        )
                    for rel in re.findall(SCRIPT_REF, command):
                        if not (ROOT / rel).exists():
                            fail(f"hooks/hooks.json: {event} references missing {rel}")

    agents_dir = ROOT / "agents"
    if agents_dir.exists():
        for agent in sorted(agents_dir.glob("*.md")):
            frontmatter = parse_frontmatter(agent.read_text(encoding="utf-8")) or {}
            for field in ("name", "description"):
                if not frontmatter.get(field):
                    fail(f"agents/{agent.name}: missing {field}")
            for banned in ("hooks", "mcpServers", "permissionMode"):
                if banned in frontmatter:
                    fail(
                        f"agents/{agent.name}: {banned} is not supported for "
                        "plugin-shipped agents"
                    )
            if frontmatter.get("isolation") not in (None, "worktree"):
                fail(f"agents/{agent.name}: the only valid isolation is worktree")

    # A skill naming an agent that does not ship is a dead reference; the skill
    # silently skips that step instead of failing.
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        # `(?<![\w./])` keeps `.agents/mpi-kanban.local.md` out of the match.
        for rel in re.findall(r"(?<![\w./])agents/[\w-]+\.md", skill.read_text(encoding="utf-8")):
            if not (ROOT / rel).exists():
                fail(f"{skill.parent.name}: references missing {rel}")


def validate_hook_wiring() -> None:
    """Every hook on disk must be registered in hooks.json and smoked.

    A hook file that exists but is not registered enforces nothing while looking
    installed from every angle. This closes the cheap half of that gap. It
    cannot close the other half: which tool calls actually REACH a hook is its
    matcher, and only a live session against the installed plugin proves that -
    `smoke_hooks.py` builds the payload itself, so 1.0.0 shipped two guards
    bypassable by every shell write with the smoke green throughout.
    """
    hooks_dir = ROOT / "hooks"
    if not hooks_dir.exists():
        return
    registered = (hooks_dir / "hooks.json").read_text(encoding="utf-8")
    smoke_file = ROOT / "scripts" / "smoke_hooks.py"
    smoke = smoke_file.read_text(encoding="utf-8") if smoke_file.exists() else ""
    for hook in sorted(hooks_dir.glob("*.py")):
        if hook.name.startswith("_"):
            continue  # shared helpers are not hooks
        if hook.name not in registered:
            fail(f"hooks/{hook.name}: not registered in hooks/hooks.json, so it "
                 "enforces nothing")
        if hook.name not in smoke:
            fail(f"hooks/{hook.name}: no case in scripts/smoke_hooks.py")


def validate_removed_surfaces() -> None:
    for rel in REMOVED_PATHS:
        if (ROOT / rel).exists():
            fail(f"removed packaging surface still exists: {rel}")


def check_no_symlinks() -> None:
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            fail(f"symlink found (breaks install on Windows): {path.relative_to(ROOT)}")


def main() -> int:
    skill_names = validate_skills()
    validate_skill_sizes()
    validate_mpi_lib_present()
    validate_pack_version()
    validate_task_board_templates()
    validate_maturity_contract_docs()
    validate_task_board_tree()
    validate_boot_docs()
    validate_coordination_messages()
    validate_no_stale_runtime_refs()
    validate_coordination_wiring()
    validate_lib_references()
    validate_plugin_manifest(skill_names)
    validate_plugin_hooks()
    validate_hook_wiring()
    validate_removed_surfaces()
    check_no_symlinks()

    if errors:
        print("Skill pack validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Skill pack validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
