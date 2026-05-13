"""Validate the Mpi-Kanban Claude Code plugin layout before release.

Checks (fail-fast):
  - .claude-plugin/plugin.json: required fields, kebab-case name
  - .claude-plugin/marketplace.json: required fields, plugin entry present
  - plugin.json name matches the entry in marketplace.json
  - Each skills/*/ contains a SKILL.md with valid YAML frontmatter
  - SKILL.md `name` field matches its parent directory name (kebab-case)
  - SKILL.md `description` field is non-empty
  - No symlinks anywhere under the repo (breaks install on Windows)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    block = text[4:end]
    data: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def validate_plugin_json() -> dict:
    path = ROOT / ".claude-plugin" / "plugin.json"
    if not path.exists():
        fail(f"missing: {path.relative_to(ROOT)}")
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in ("name", "version", "description"):
        if not data.get(field):
            fail(f"plugin.json missing required field: {field}")
    name = data.get("name", "")
    if name and not KEBAB.match(name):
        fail(f"plugin.json name '{name}' is not kebab-case")
    return data


def validate_marketplace_json(plugin_name: str) -> None:
    path = ROOT / ".claude-plugin" / "marketplace.json"
    if not path.exists():
        fail(f"missing: {path.relative_to(ROOT)}")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in ("name", "owner", "plugins"):
        if not data.get(field):
            fail(f"marketplace.json missing required field: {field}")
    market_name = data.get("name", "")
    if market_name and not KEBAB.match(market_name):
        fail(f"marketplace.json name '{market_name}' is not kebab-case")
    entries = data.get("plugins", [])
    if not any(entry.get("name") == plugin_name for entry in entries):
        fail(
            f"marketplace.json does not list plugin '{plugin_name}' "
            f"(found: {[e.get('name') for e in entries]})"
        )


def validate_skills() -> None:
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        fail("missing skills/ directory")
        return
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            fail(f"{skill_dir.name}: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        front = parse_frontmatter(text)
        if front is None:
            fail(f"{skill_dir.name}/SKILL.md: invalid or missing YAML frontmatter")
            continue
        name = front.get("name", "")
        if name != skill_dir.name:
            fail(
                f"{skill_dir.name}/SKILL.md: frontmatter name '{name}' "
                f"does not match folder name"
            )
        if name and not KEBAB.match(name):
            fail(f"{skill_dir.name}/SKILL.md: name '{name}' is not kebab-case")
        if not front.get("description"):
            fail(f"{skill_dir.name}/SKILL.md: empty description")


def check_no_symlinks() -> None:
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            fail(f"symlink found (breaks install on Windows): {path.relative_to(ROOT)}")


def main() -> int:
    plugin_data = validate_plugin_json()
    validate_marketplace_json(plugin_data.get("name", ""))
    validate_skills()
    check_no_symlinks()

    if errors:
        print("Plugin validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Plugin validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
