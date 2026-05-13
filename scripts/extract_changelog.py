"""Extract the section for a specific version from CHANGELOG.md.

Used by the release workflow to populate GitHub Release notes. Expects
CHANGELOG.md to follow the Keep a Changelog format with H2 headings like:

    ## [0.4.2] - 2026-05-13
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: extract_changelog.py <version>", file=sys.stderr)
        return 2
    version = sys.argv[1]

    if not CHANGELOG.exists():
        print(f"Release {version}", end="")
        return 0

    text = CHANGELOG.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        print(f"Release {version}", end="")
        return 0
    print(match.group(1).strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
