"""Copy all contents of this codebase into C:\\AI\\Mpi\\Plugins\\Mpi-Kanban."""
import os
import shutil
import stat
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
DST = Path(r"C:\AI\Mpi\Plugins\Mpi-Kanban")
SELF = Path(__file__).resolve()


def on_rm_error(func, path, exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)

    for item in SRC.iterdir():
        if item.resolve() == SELF:
            continue
        target = DST / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target, onexc=on_rm_error)
            shutil.copytree(item, target)
        else:
            if target.exists():
                os.chmod(target, stat.S_IWRITE)
            shutil.copy2(item, target)
    print(f"Copied all contents of {SRC} -> {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
