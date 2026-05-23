"""Validate the Mpi-Kanban dual Claude/Codex plugin layout before release.

Checks (fail-fast):
  - .claude-plugin/plugin.json: required fields, kebab-case name
  - .claude-plugin/marketplace.json: required fields, plugin entry present
  - .codex-plugin/plugin.json: required fields, shared skill path, interface
  - Claude and Codex manifests stay synchronized for public identity fields
  - plugin.json name matches the entry in marketplace.json
  - Each skills/*/ contains a SKILL.md with valid YAML frontmatter
  - SKILL.md `name` field matches its parent directory name (kebab-case)
  - SKILL.md `description` field is non-empty
  - No symlinks anywhere under the repo (breaks install on Windows)
  - Kilo target adapter assets (docs/kilocode-install.md, templates/kilo.jsonc,
    scripts/build_kilo_skills.py) exist and parse
  - SKILL.md name <=64 chars, description <=1024 chars (Kilo schema; harmless
    for Claude/Codex)
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


IDENTITY_FIELDS = ("name", "version", "description", "author", "repository", "license", "keywords")
CODEX_BUNDLE_DIR = ROOT / "plugins" / "MadPonyInteractive" / "mpi-kanban"
CODEX_BUNDLE_JSON = CODEX_BUNDLE_DIR / "plugins.json"
CODEX_BUNDLE_ICON = CODEX_BUNDLE_DIR / "icon.svg"

KILO_INSTALL_DOC = ROOT / "docs" / "kilocode-install.md"
KILO_SUBMISSION_DOC = ROOT / "docs" / "kilocode-marketplace-submission.md"
KILO_TEMPLATE = ROOT / "templates" / "kilo.jsonc"
KILO_GENERATOR = ROOT / "scripts" / "build_kilo_skills.py"
KILO_NAME_MAX = 64
KILO_DESC_MAX = 1024


def validate_claude_plugin_json() -> dict:
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


def validate_codex_plugin_json() -> dict:
    path = ROOT / ".codex-plugin" / "plugin.json"
    if not path.exists():
        fail(f"missing: {path.relative_to(ROOT)}")
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in ("name", "version", "description", "skills", "interface"):
        if not data.get(field):
            fail(f".codex-plugin/plugin.json missing required field: {field}")
    name = data.get("name", "")
    if name and not KEBAB.match(name):
        fail(f".codex-plugin/plugin.json name '{name}' is not kebab-case")
    if data.get("skills") != "./skills/":
        fail(".codex-plugin/plugin.json skills must point to ./skills/")
    interface = data.get("interface", {})
    if not isinstance(interface, dict):
        fail(".codex-plugin/plugin.json interface must be an object")
    else:
        for field in ("displayName", "shortDescription", "developerName", "category"):
            if not interface.get(field):
                fail(f".codex-plugin/plugin.json interface missing field: {field}")
        prompts = interface.get("defaultPrompt", [])
        if prompts and (not isinstance(prompts, list) or len(prompts) > 3):
            fail(".codex-plugin/plugin.json interface.defaultPrompt must be a list of at most 3 prompts")
    return data


def validate_manifest_sync(claude_data: dict, codex_data: dict) -> None:
    if not claude_data or not codex_data:
        return
    for field in IDENTITY_FIELDS:
        if claude_data.get(field) != codex_data.get(field):
            fail(f"manifest identity drift on field: {field}")


def validate_codex_marketplace_bundle(codex_data: dict) -> None:
    if not codex_data:
        return
    if not CODEX_BUNDLE_DIR.is_dir():
        fail(f"missing Codex marketplace bundle directory: {CODEX_BUNDLE_DIR.relative_to(ROOT)}")
        return
    if not CODEX_BUNDLE_JSON.exists():
        fail(f"missing: {CODEX_BUNDLE_JSON.relative_to(ROOT)}")
        return
    if not CODEX_BUNDLE_ICON.exists():
        fail(f"missing: {CODEX_BUNDLE_ICON.relative_to(ROOT)}")

    data = json.loads(CODEX_BUNDLE_JSON.read_text(encoding="utf-8"))
    for field in ("name", "version", "description", "author", "repository", "license", "keywords", "interface"):
        if not data.get(field):
            fail(f"Codex marketplace bundle missing required field: {field}")

    for field in (*IDENTITY_FIELDS, "homepage"):
        if data.get(field) != codex_data.get(field):
            fail(f"Codex marketplace bundle identity drift on field: {field}")

    bundle_interface = data.get("interface", {})
    codex_interface = codex_data.get("interface", {})
    if bundle_interface != codex_interface:
        fail("Codex marketplace bundle interface drift from .codex-plugin/plugin.json")

    composer_icon = bundle_interface.get("composerIcon")
    if composer_icon != "plugins/MadPonyInteractive/mpi-kanban/icon.svg":
        fail("Codex marketplace bundle interface.composerIcon must point at plugins/MadPonyInteractive/mpi-kanban/icon.svg")
    if CODEX_BUNDLE_ICON.exists():
        icon_text = CODEX_BUNDLE_ICON.read_text(encoding="utf-8").lstrip()
        if not icon_text.startswith("<svg"):
            fail("Codex marketplace bundle icon must be an SVG file")


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


def validate_kilo_assets() -> None:
    """Additive Kilo target adapter checks.

    Verifies that the Phase 6 install surface is present and the kilo.jsonc
    template parses as JSON after stripping comments. Does not regenerate
    `skills-kilo/` (gitignored, rebuilt at release time by the maintainer).
    """
    for path in (KILO_INSTALL_DOC, KILO_SUBMISSION_DOC, KILO_TEMPLATE, KILO_GENERATOR):
        if not path.exists():
            fail(f"missing Kilo adapter asset: {path.relative_to(ROOT)}")

    if KILO_TEMPLATE.exists():
        text = KILO_TEMPLATE.read_text(encoding="utf-8")
        stripped = re.sub(r"//.*", "", text)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.S)
        stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            fail(f"templates/kilo.jsonc does not parse as JSONC: {exc}")
        else:
            skills_block = data.get("skills")
            if not isinstance(skills_block, dict) or not skills_block.get("paths"):
                fail("templates/kilo.jsonc must define skills.paths")


def validate_kilo_skill_limits() -> None:
    """Additive Kilo-schema checks against the canonical skill tree.

    Kilo enforces name <=64 chars and description <=1024 chars on SKILL.md
    frontmatter. The limits are harmless for Claude/Codex; checking them on
    `skills/` keeps the canonical source Kilo-portable.
    """
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        return
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        front = parse_frontmatter(skill_md.read_text(encoding="utf-8")) or {}
        name = front.get("name", "")
        desc = front.get("description", "")
        if len(name) > KILO_NAME_MAX:
            fail(f"{skill_dir.name}/SKILL.md: name exceeds {KILO_NAME_MAX} chars (Kilo)")
        if len(desc) > KILO_DESC_MAX:
            fail(f"{skill_dir.name}/SKILL.md: description exceeds {KILO_DESC_MAX} chars (Kilo)")


def check_no_symlinks() -> None:
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            fail(f"symlink found (breaks install on Windows): {path.relative_to(ROOT)}")


def main() -> int:
    plugin_data = validate_claude_plugin_json()
    codex_data = validate_codex_plugin_json()
    validate_manifest_sync(plugin_data, codex_data)
    validate_codex_marketplace_bundle(codex_data)
    validate_marketplace_json(plugin_data.get("name", ""))
    validate_skills()
    validate_kilo_assets()
    validate_kilo_skill_limits()
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
