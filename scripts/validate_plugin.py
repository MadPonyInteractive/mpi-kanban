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
        "kanban-ops/find.md",
        "project-knowledge/indexing.md",
        "docs/coordination/README.md",
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
