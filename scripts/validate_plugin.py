"""Validate the Mpi-Kanban universal Agent Skills pack before release."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
TASK_ID = re.compile(r"^MPI-[1-9][0-9]*$")
TASK_COLUMNS = ("todo", "doing", "done")
TASK_REQUIRED_FIELDS = {"schema", "id", "title", "column", "created_at", "updated_at", "links"}

REMOVED_PATHS = (
    ".claude-plugin",
    ".codex-plugin",
    ".agents/plugins",
    "plugins/MadPonyInteractive/mpi-kanban",
    "scripts/build_kilo_skills.py",
    "scripts/register_codex_plugin.py",
    "docs/kilocode-install.md",
    "docs/kilocode-marketplace-submission.md",
    "templates/kilo.jsonc",
    "update_live.py",
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


def validate_mpi_lib_present() -> None:
    mpi_lib = ROOT / "skills" / "mpi-lib"
    if not (mpi_lib / "SKILL.md").exists():
        fail("missing skills/mpi-lib/SKILL.md")
        return

    required = (
        "coordination-ops/lifecycle.md",
        "coordination-ops/statuses.md",
        "interop-ops/modes.md",
        "task-board-ops/_schema.md",
        "task-board-ops/read.md",
        "task-board-ops/mutate.md",
        "task-board-ops/migrate.md",
        "task-board-ops/validate.md",
        "kanban-ops/find.md",
        "project-knowledge/indexing.md",
        "docs/coordination/README.md",
        "templates/board.json",
        "templates/task.json",
        "templates/kanban.md",
    )
    for rel in required:
        if not (mpi_lib / rel).exists():
            fail(f"mpi-lib missing required reference: {rel}")

    for skill_dir in skill_dirs():
        if skill_dir.name == "mpi-lib":
            continue
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        if "## Locating shared references" not in text or "<mpi-lib-root>" not in text:
            fail(f"{skill_dir.name}/SKILL.md: missing mpi-lib discovery block")


def validate_kanban_templates() -> None:
    expected = [
        "## BACKLOG",
        "## PLANNING",
        "## IMPLEMENTING",
        "## VALIDATING",
        "## COMPLETED",
    ]
    template_paths = [
        ROOT / "skills" / "mpi-lib" / "templates" / "kanban.md",
        ROOT / "skills" / "mpi-init" / "templates" / "kanban.md",
    ]
    for path in template_paths:
        if not path.exists():
            fail(f"missing kanban template: {path.relative_to(ROOT)}")
            continue
        headings = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("## ")
        ]
        if headings != expected:
            fail(
                f"{path.relative_to(ROOT)} must use columns in order: "
                + " -> ".join(expected)
            )


def load_json(path: Path, label: str) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{label} is invalid JSON: {exc}")
    except OSError as exc:
        fail(f"{label} could not be read: {exc}")
    return None


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
        if not isinstance(task.get("links"), dict):
            fail("templates/task.json links must be an object")


def validate_event_log(path: Path, label: str, *, require_task_id: bool = False) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"{label} could not be read: {exc}")
        return
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"{label}:{index} malformed JSONL event: {exc}")
            continue
        if not isinstance(event, dict):
            fail(f"{label}:{index} event must be a JSON object")
            continue
        if event.get("schema") != "mpi-kanban/event/v1":
            fail(f"{label}:{index} event schema must be mpi-kanban/event/v1")
        if not event.get("type"):
            fail(f"{label}:{index} event missing type")
        if not event.get("at"):
            fail(f"{label}:{index} event missing at")
        if require_task_id and not event.get("id"):
            fail(f"{label}:{index} task event missing id")


def linked_path_is_inside(task_dir: Path, link_value: object) -> Path | None:
    if not isinstance(link_value, str) or not link_value:
        return None
    if Path(link_value).is_absolute():
        return None
    target = (task_dir / link_value).resolve()
    try:
        target.relative_to(task_dir.resolve())
    except ValueError:
        return None
    return target


def validate_task_board_tree() -> None:
    board_root = ROOT / ".agents" / "mpi-kanban"
    board_path = board_root / "board.json"
    if not board_path.exists():
        return

    board = load_json(board_path, ".agents/mpi-kanban/board.json")
    if not isinstance(board, dict):
        return
    if board.get("schema") != "mpi-kanban/board/v1":
        fail(".agents/mpi-kanban/board.json schema must be mpi-kanban/board/v1")
    next_id = board.get("next_id")
    if not isinstance(next_id, int) or next_id < 1:
        fail(".agents/mpi-kanban/board.json next_id must be a positive integer")

    columns = board.get("columns")
    if not isinstance(columns, dict) or tuple(columns.keys()) != TASK_COLUMNS:
        fail(".agents/mpi-kanban/board.json columns must be exactly todo, doing, done")
        return

    listed: dict[str, str] = {}
    max_suffix = 0
    for column in TASK_COLUMNS:
        ids = columns.get(column)
        if not isinstance(ids, list):
            fail(f".agents/mpi-kanban/board.json column {column} must be a list")
            continue
        for task_id in ids:
            if not isinstance(task_id, str) or not TASK_ID.match(task_id):
                fail(f".agents/mpi-kanban/board.json contains invalid task id in {column}: {task_id!r}")
                continue
            if task_id in listed:
                fail(f"task id {task_id} appears in both {listed[task_id]} and {column}")
            listed[task_id] = column
            max_suffix = max(max_suffix, int(task_id.split("-", 1)[1]))

    if isinstance(next_id, int) and next_id <= max_suffix:
        fail(".agents/mpi-kanban/board.json next_id must be greater than all existing task IDs")

    tasks_root = board_root / "tasks"
    for task_id, column in listed.items():
        task_dir = tasks_root / task_id
        task_json = task_dir / "task.json"
        if not task_json.exists():
            fail(f"listed task {task_id} is missing {task_json.relative_to(ROOT)}")
            continue
        task = load_json(task_json, str(task_json.relative_to(ROOT)))
        if not isinstance(task, dict):
            continue
        if task.get("schema") != "mpi-kanban/task-card/v1":
            fail(f"{task_json.relative_to(ROOT)} schema must be mpi-kanban/task-card/v1")
        missing = TASK_REQUIRED_FIELDS - set(task)
        if missing:
            fail(f"{task_json.relative_to(ROOT)} missing required fields: {sorted(missing)}")
        if task.get("id") != task_id:
            fail(f"{task_json.relative_to(ROOT)} id must match folder/listed id {task_id}")
        if task.get("column") != column:
            fail(f"{task_json.relative_to(ROOT)} column must match board column {column}")
        links = task.get("links")
        if not isinstance(links, dict):
            fail(f"{task_json.relative_to(ROOT)} links must be an object")
            continue
        for key, value in links.items():
            target = linked_path_is_inside(task_dir, value)
            if target is None:
                fail(f"{task_json.relative_to(ROOT)} link {key!r} must be a relative path inside the task folder")
                continue
            if target.exists() and target.name == "events.jsonl":
                validate_event_log(target, str(target.relative_to(ROOT)), require_task_id=True)
            if target.exists() and target.name.endswith(".json"):
                load_json(target, str(target.relative_to(ROOT)))
        checklist = linked_path_is_inside(task_dir, links.get("checklist"))
        validation = linked_path_is_inside(task_dir, links.get("validation"))
        brief = linked_path_is_inside(task_dir, links.get("brief"))
        attention = task.get("attention")
        if column == "doing" and checklist is not None and not checklist.exists():
            fail(f"{task_json.relative_to(ROOT)} is in doing but missing linked checklist.md")
        if column == "done" and validation is not None and not validation.exists():
            fail(f"{task_json.relative_to(ROOT)} is in done but missing linked validation.md")
        if isinstance(attention, dict) and attention.get("state") == "required" and brief is not None and not brief.exists():
            fail(f"{task_json.relative_to(ROOT)} requires attention but missing linked brief.md")

    if tasks_root.exists():
        for child in tasks_root.iterdir():
            if child.is_dir() and (child / "task.json").exists() and child.name not in listed:
                fail(f"orphaned task folder not listed in board.json: {child.relative_to(ROOT)}")

    validate_event_log(board_root / "events.jsonl", ".agents/mpi-kanban/events.jsonl")


def validate_interop_state() -> None:
    path = ROOT / ".agents" / "mpi-kanban" / "state" / "interop.json"
    if not path.exists():
        fail("missing .agents/mpi-kanban/state/interop.json")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "mpi-kanban/interop/v1":
        fail("interop.json must use schema mpi-kanban/interop/v1")
    if data.get("source_of_truth") not in {"file", "nimbalyst"}:
        fail("interop.json source_of_truth must be file or nimbalyst")
    detected = data.get("last_detected_environment")
    if not isinstance(detected, dict):
        fail("interop.json last_detected_environment must be an object")
    elif detected.get("kind") not in {"generic", "nimbalyst", "unknown"}:
        fail("interop.json last_detected_environment.kind must be generic, nimbalyst, or unknown")
    if not isinstance(data.get("id_mappings"), list):
        fail("interop.json id_mappings must be a list")


def validate_no_stale_runtime_refs() -> None:
    patterns = (
        "$" + "{CLAUDE_PLUGIN_ROOT}",
        "/" + "mpi-kanban:",
        "Codex" + " users",
        "Claude Code" + " users",
        "plugin" + " root",
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


def validate_skills_sh_json(skill_names: set[str]) -> None:
    path = ROOT / "skills.sh.json"
    if not path.exists():
        fail("missing skills.sh.json")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = data.get("groupings")
    if not isinstance(groups, list) or not groups:
        fail("skills.sh.json must define non-empty groupings")
        return
    listed: set[str] = set()
    for group in groups:
        skills = group.get("skills") if isinstance(group, dict) else None
        if not isinstance(skills, list) or not skills:
            fail("skills.sh.json groupings[*].skills must be non-empty lists")
            continue
        listed.update(str(skill) for skill in skills)
    missing = skill_names - listed
    extra = listed - skill_names
    if missing:
        fail(f"skills.sh.json missing skills: {sorted(missing)}")
    if extra:
        fail(f"skills.sh.json lists unknown skills: {sorted(extra)}")


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
    validate_mpi_lib_present()
    validate_kanban_templates()
    validate_task_board_templates()
    validate_task_board_tree()
    validate_interop_state()
    validate_no_stale_runtime_refs()
    validate_skills_sh_json(skill_names)
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
