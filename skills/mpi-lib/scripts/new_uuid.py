"""Generate UUIDv4 values for MPI Kanban coordination records."""
from __future__ import annotations

import argparse
import uuid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate lowercase UUIDv4 values, one per line."
    )
    parser.add_argument(
        "count",
        nargs="?",
        default=1,
        type=int,
        help="number of UUIDs to generate",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise SystemExit("count must be at least 1")
    for _ in range(args.count):
        print(uuid.uuid4())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

