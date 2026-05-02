"""Copy contents of this codebase into C:\\AI\\Mpi\\Plugins\\Mpi-Kanban."""
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
DST = Path(r"C:\AI\Mpi\Plugins\Mpi-Kanban")

IGNORE_NAMES = {".git", "__pycache__", "node_modules", ".venv", "venv"}
IGNORE_SUFFIX = {".pyc"}


def should_ignore(p: Path) -> bool:
    return p.name in IGNORE_NAMES or p.suffix in IGNORE_SUFFIX


def main() -> int:
    if not DST.exists():
        print(f"Destination missing: {DST}")
        return 1

    for item in SRC.iterdir():
        if item.resolve() == Path(__file__).resolve():
            continue
        if should_ignore(item):
            continue
        target = DST / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target, ignore=shutil.ignore_patterns(*IGNORE_NAMES, "*.pyc"))
        else:
            shutil.copy2(item, target)
    print(f"Copied contents of {SRC} -> {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
