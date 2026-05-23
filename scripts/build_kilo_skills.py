"""Build a KiloCode-portable copy of the MPI skill tree.

KiloCode's marketplace pull (`add-remote-skill.ts`) sparse-checks out a single
skill folder, so any sibling reference via `${CLAUDE_PLUGIN_ROOT}/<path>` is
lost. This script resolves every such reference by inlining the target file's
contents into the skill, producing a self-contained tree at `skills-kilo/`
suitable for marketplace submission.

Run:

    python scripts/build_kilo_skills.py

The shared `skills/mpi-*/SKILL.md` source is never modified. The generated
tree is gitignored by default; the marketplace fork commits its own copy.

Design note: this is the first target adapter (KiloCode). The internal steps
(discover -> transform -> resolve -> write -> validate) are deliberately
factored so a follow-up Codex or OpenCode adapter can reuse the structure.
A later refactor may extract a shared `build_agent_skills.py --target ...`
front end; until then, Kilo-specific constants stay isolated near the top of
this module and function names are target-neutral where possible.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path
from typing import Iterable

# --- Kilo target configuration (isolated; extract when adding a second target) ---
ROOT = Path(__file__).resolve().parent.parent
SOURCE_SKILLS_DIR = ROOT / "skills"
TARGET_OUTPUT_DIR = ROOT / "skills-kilo"
TARGET_NAME = "kilo"

# Reference strategy: inline every ${CLAUDE_PLUGIN_ROOT}/<path>.md into the
# skill body. Kilo's sparse marketplace fetch drops siblings; other targets
# may prefer overlay metadata or no inlining at all.
REFERENCE_VARIABLE = "CLAUDE_PLUGIN_ROOT"
REFERENCE_PATTERN = re.compile(
    r"`?\$\{" + REFERENCE_VARIABLE + r"\}/([A-Za-z0-9_./\-]+\.md)`?"
)
PROSE_VARIABLE_PATTERN = re.compile(r"\$\{" + REFERENCE_VARIABLE + r"\}")
PROSE_REPLACEMENT = "the plugin root"

MAX_INLINE_DEPTH = 3
MAX_SKILL_BYTES = 100_000  # generated SKILL.md sanity cap

# Marketplace assumption: the fetcher copies the entire skill directory but
# nothing outside it. Anything referenced from a sibling tree must be inlined
# or marked missing.


# --- Step 1: discover source skills ----------------------------------------

def discover_skills(source_dir: Path) -> list[Path]:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"missing source: {source_dir}")
    return sorted(
        d for d in source_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    )


# --- Step 2 + 3: transform one skill (resolve + inject references) ---------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def resolve_reference(path_rel: str, visited: set[str], depth: int) -> str:
    if depth > MAX_INLINE_DEPTH:
        return f"<!-- inline-depth-exceeded: {path_rel} -->"
    if path_rel in visited:
        return f"<!-- inline-cycle-guard: {path_rel} -->"
    target = ROOT / path_rel
    if not target.is_file():
        return f"<!-- inline-missing: {path_rel} -->"
    visited = visited | {path_rel}
    text = _read(target)
    return REFERENCE_PATTERN.sub(
        lambda m: _inject_block(m.group(1), visited, depth + 1),
        text,
    )


def _inject_block(path_rel: str, visited: set[str], depth: int) -> str:
    body = resolve_reference(path_rel, visited, depth)
    return (
        f"\n\n<!-- inlined: {path_rel} -->\n"
        f"{body.rstrip()}\n"
        f"<!-- end inlined: {path_rel} -->\n\n"
    )


def transform_skill(skill_md: Path) -> tuple[str, int]:
    raw = _read(skill_md)
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return _inject_block(match.group(1), set(), 1)

    body = REFERENCE_PATTERN.sub(replace, raw)
    body = PROSE_VARIABLE_PATTERN.sub(PROSE_REPLACEMENT, body)
    return body, count


# --- Step 4: write target output -------------------------------------------

def _copy_assets(src_dir: Path, dst_dir: Path) -> None:
    for child in src_dir.iterdir():
        if child.name == "SKILL.md":
            continue
        dst_child = dst_dir / child.name
        if child.is_dir():
            shutil.copytree(child, dst_child)
        else:
            shutil.copy2(child, dst_child)


def write_skill(skill_dir: Path, body: str, output_dir: Path) -> Path:
    out_dir = output_dir / skill_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / "SKILL.md"
    out_md.write_text(body, encoding="utf-8")
    _copy_assets(skill_dir, out_dir)
    return out_md


def clean_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)


# --- Step 5: validate generated output -------------------------------------

def validate_generated(skill_md: Path) -> list[str]:
    """Return list of validation issues for one generated SKILL.md."""
    issues: list[str] = []
    body = _read(skill_md)
    if REFERENCE_PATTERN.search(body):
        issues.append(f"{skill_md.name}: residual reference variable")
    if PROSE_VARIABLE_PATTERN.search(body):
        issues.append(f"{skill_md.name}: residual prose mention of variable")
    for marker in ("inline-depth-exceeded", "inline-cycle-guard", "inline-missing"):
        if marker in body:
            issues.append(f"{skill_md.name}: contains {marker} marker")
    if len(body.encode("utf-8")) > MAX_SKILL_BYTES:
        issues.append(f"{skill_md.name}: exceeds {MAX_SKILL_BYTES} bytes")
    return issues


# --- Driver ---------------------------------------------------------------

def _print_summary(rows: Iterable[tuple[str, int, int]]) -> None:
    rows_list = list(rows)
    if not rows_list:
        print("no skills found")
        return
    width = max(len(name) for name, _, _ in rows_list)
    print(f"{'skill'.ljust(width)}  inlined  bytes")
    for name, count, size in rows_list:
        print(f"{name.ljust(width)}  {str(count).rjust(7)}  {size}")


def build(source_dir: Path = SOURCE_SKILLS_DIR, output_dir: Path = TARGET_OUTPUT_DIR) -> int:
    skills = discover_skills(source_dir)
    clean_output_dir(output_dir)

    rows: list[tuple[str, int, int]] = []
    issues: list[str] = []
    for skill_dir in skills:
        skill_md = skill_dir / "SKILL.md"
        body, count = transform_skill(skill_md)
        out_md = write_skill(skill_dir, body, output_dir)
        rows.append((skill_dir.name, count, len(body)))
        issues.extend(validate_generated(out_md))

    _print_summary(rows)

    if issues:
        print(f"\n{TARGET_NAME} build: {len(issues)} validation issues", file=sys.stderr)
        for issue in issues:
            print(f"  {issue}", file=sys.stderr)
        return 2

    print(f"\nwrote {len(rows)} skills to {output_dir.relative_to(ROOT)}/ (target: {TARGET_NAME})")
    return 0


if __name__ == "__main__":
    sys.exit(build())
