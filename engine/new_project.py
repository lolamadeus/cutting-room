"""Create a new cutting-room project.

    python engine/new_project.py "Project title" "C:\\path\\to\\clips" ["D:\\more\\clips" ...]
        [--id my-id] [--kind "Family video"] [--brief "..."] [--target 120 180] [--recursive]

Writes projects/<id>/project.json (edit it to set groups and highlight tags) and an "Open editor" shortcut
(.bat on Windows, .sh elsewhere). Folders are optional: clips can also be listed in project.json "files".
Then run:  python engine/prepare.py <id>
"""
import argparse
import os
import re
import sys
from pathlib import Path

from common import PROJECTS, write_json

TEMPLATE_TAGS = [
    {"id": "cat", "label": "Category", "mode": "single", "board": True, "options": [
        {"id": "a", "label": "Section A", "color": "#ff5a3c"},
        {"id": "b", "label": "Section B", "color": "#3b82f6"},
        {"id": "c", "label": "Section C", "color": "#14b8a6"},
        {"id": "d", "label": "Section D", "color": "#eab308"}]},
    {"id": "role", "label": "Use as", "mode": "single", "options": [
        {"id": "open", "label": "Opener"}, {"id": "hit", "label": "Big moment"},
        {"id": "breath", "label": "Breather"}, {"id": "close", "label": "Closer"}]},
]

BAT = """@echo off
rem Opens this project's editor (starts the cutting-room server if needed).
call "%~dp0..\\..\\Open cutting room.bat" {pid}
"""

SH = """#!/usr/bin/env sh
# Opens this project's editor (starts the cutting-room server if needed).
exec "$(dirname "$0")/../../cutting-room.sh" {pid}
"""


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "project"


def write_launcher(d: Path, pid: str):
    if sys.platform == "win32":
        (d / "Open editor.bat").write_text(BAT.format(pid=pid), encoding="utf-8")
    else:
        f = d / "open-editor.sh"
        f.write_text(SH.format(pid=pid), encoding="utf-8")
        os.chmod(f, 0o755)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title")
    ap.add_argument("source", nargs="*", help="folder(s) holding the clips")
    ap.add_argument("--id")
    ap.add_argument("--kind", default="")
    ap.add_argument("--brief", default="")
    ap.add_argument("--target", nargs=2, type=int, metavar=("MIN", "MAX"), default=(120, 180),
                    help="target length in seconds (default 120 180)")
    ap.add_argument("--recursive", action="store_true", help="include subfolders of the source folders")
    args = ap.parse_args()

    pid = args.id or slug(args.title)
    d = PROJECTS / pid
    if (d / "project.json").exists():
        sys.exit(f"Project {pid!r} already exists: {d}")
    for s in args.source:
        if not Path(s).is_dir():
            sys.exit(f"Not a folder: {s}")
    cfg = {
        "title": args.title, "kind": args.kind,
        "source": args.source[0] if len(args.source) == 1 else args.source,
        "target": {"min": args.target[0], "max": args.target[1]},
        "brief": args.brief,
        "groups": [],
        "groupRules": [],
        "highlightTags": TEMPLATE_TAGS,
    }
    if args.recursive:
        cfg["recursive"] = True
    write_json(d / "project.json", cfg, indent=2)
    write_launcher(d, pid)
    print(f"Created {d}\nNext: edit project.json if you like, then run:  python engine/prepare.py {pid}")


if __name__ == "__main__":
    main()
