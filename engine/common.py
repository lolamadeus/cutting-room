"""Shared paths and project loading for the cutting-room tools."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
WEB = ROOT / "web"
PORT = 8770

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mts", ".mxf", ".flv", ".wmv", ".mpeg", ".mpg"}

DEFAULT_PRIORITIES = [
    {"id": "must", "label": "Must use", "key": "1", "color": "#3f8f4a"},
    {"id": "try", "label": "Try to use", "key": "2", "color": "#d39a1f"},
    {"id": "space", "label": "If there's space", "key": "3", "color": "#7d7f8a"},
    {"id": "dont", "label": "Don't use", "key": "4", "color": "#c0443a"},
]


def project_dir(pid: str) -> Path:
    d = (PROJECTS / pid).resolve()
    if d.parent != PROJECTS.resolve() or not (d / "project.json").is_file():
        raise FileNotFoundError(f"No project called {pid!r} in {PROJECTS}")
    return d


def load_project(pid: str) -> dict:
    cfg = json.loads((project_dir(pid) / "project.json").read_text(encoding="utf-8"))
    cfg.setdefault("priorities", DEFAULT_PRIORITIES)
    cfg.setdefault("highlightTags", [])
    cfg.setdefault("groups", [])
    cfg.setdefault("groupRules", [])
    src = cfg.get("source", [])
    cfg["source"] = [src] if isinstance(src, str) else list(src)
    return cfg


def list_projects():
    if not PROJECTS.is_dir():
        return []
    return sorted(p.name for p in PROJECTS.iterdir() if (p / "project.json").is_file())


def write_json(path: Path, data, **kw):
    """Atomic write so a crash never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, **kw), encoding="utf-8")
    tmp.replace(path)


def find_font(bold=True):
    """A TrueType font for ffmpeg drawtext, or None (then ffmpeg falls back to its default)."""
    if sys.platform == "win32":
        names = ["C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"]
    elif sys.platform == "darwin":
        names = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]
    else:
        names = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]
    return next((n for n in names if Path(n).is_file()), None)


def ffmpeg_path(p) -> str:
    r"""Escape a path for use inside an ffmpeg filter argument (C:\x -> C\:/x)."""
    return str(p).replace("\\", "/").replace(":", "\\:")
