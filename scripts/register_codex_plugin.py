"""Register this checkout in a Codex local marketplace.

Compatibility target: Python 3.8+ using only the standard library.
"""

from __future__ import print_function

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CODEX_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
DEFAULT_MARKETPLACE = Path.home() / ".agents" / "plugins" / "marketplace.json"


def read_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def marketplace_root(marketplace_path):
    """Return root for source.path resolution.

    For <root>/.agents/plugins/marketplace.json, Codex resolves source paths
    from <root>, not from the marketplace file directory.
    """
    parts = marketplace_path.parts
    if len(parts) >= 3 and parts[-3:] == (".agents", "plugins", "marketplace.json"):
        return marketplace_path.parents[2]
    return marketplace_path.parent


def to_posix_path(path):
    return path.replace(os.sep, "/")


def source_path(plugin_path, marketplace_path):
    root = marketplace_root(marketplace_path)
    plugin_path = plugin_path.resolve()
    root = root.resolve()

    try:
        relative = os.path.relpath(str(plugin_path), str(root))
    except ValueError:
        return to_posix_path(str(plugin_path))

    relative = to_posix_path(relative)
    if relative == ".":
        return "."
    if relative.startswith("../"):
        return relative
    return "./" + relative


def load_or_create_marketplace(path, name, display_name):
    if path.exists():
        data = read_json(path)
    else:
        data = {
            "name": name,
            "interface": {
                "displayName": display_name
            },
            "plugins": []
        }

    if not isinstance(data, dict):
        raise RuntimeError("Marketplace JSON root must be an object: {0}".format(path))
    data.setdefault("name", name)
    interface = data.setdefault("interface", {})
    if isinstance(interface, dict):
        interface.setdefault("displayName", display_name)
    else:
        raise RuntimeError("Marketplace interface must be an object: {0}".format(path))
    plugins = data.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise RuntimeError("Marketplace plugins must be a list: {0}".format(path))
    return data


def build_entry(plugin_name, plugin_path, marketplace_path):
    return {
        "name": plugin_name,
        "source": {
            "source": "local",
            "path": source_path(plugin_path, marketplace_path)
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL"
        },
        "category": "Productivity"
    }


def upsert_plugin(data, entry):
    plugins = data["plugins"]
    for index, existing in enumerate(plugins):
        if isinstance(existing, dict) and existing.get("name") == entry["name"]:
            plugins[index] = entry
            return "updated"
    plugins.append(entry)
    return "added"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Register Mpi-Kanban in a Codex local marketplace."
    )
    parser.add_argument(
        "--marketplace",
        default=str(DEFAULT_MARKETPLACE),
        help="Marketplace JSON path. Default: ~/.agents/plugins/marketplace.json",
    )
    parser.add_argument(
        "--plugin-path",
        default=str(ROOT),
        help="Plugin checkout path to register. Default: this repository.",
    )
    parser.add_argument(
        "--marketplace-name",
        default="mad-pony-interactive",
        help="Marketplace name to use when creating a new file.",
    )
    parser.add_argument(
        "--display-name",
        default="MadPonyInteractive",
        help="Marketplace display name to use when creating a new file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the registration entry without writing marketplace.json.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    marketplace_path = Path(args.marketplace).expanduser().resolve()
    plugin_path = Path(args.plugin_path).expanduser().resolve()
    manifest_path = plugin_path / ".codex-plugin" / "plugin.json"

    if not manifest_path.exists():
        raise RuntimeError("Missing Codex plugin manifest: {0}".format(manifest_path))

    manifest = read_json(manifest_path)
    plugin_name = manifest.get("name")
    if not plugin_name:
        raise RuntimeError("Codex plugin manifest is missing 'name': {0}".format(manifest_path))

    data = load_or_create_marketplace(
        marketplace_path,
        args.marketplace_name,
        args.display_name,
    )
    entry = build_entry(plugin_name, plugin_path, marketplace_path)
    action = upsert_plugin(data, entry)

    if args.dry_run:
        print(json.dumps(entry, indent=2))
        print("Dry run: marketplace not written.")
        return 0

    write_json(marketplace_path, data)
    print("Codex marketplace {0}: {1}".format(action, marketplace_path))
    print("Plugin: {0}".format(plugin_path))
    print("Source path: {0}".format(entry["source"]["path"]))
    print("Restart or reload Codex so it reads the updated marketplace.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("register_codex_plugin.py: {0}".format(exc), file=sys.stderr)
        sys.exit(1)
