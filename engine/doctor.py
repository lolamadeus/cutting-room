"""Check this machine is ready for the cutting room, and list the projects.

    python engine/doctor.py

Checks Python, ffmpeg/ffprobe (and the libx264 encoder), the optional extras (yt-dlp for downloading footage,
Pillow for text/image overlays), whether the server is running, and each project's state.
Exits non-zero if something required is missing.
"""
import json
import shutil
import subprocess
import sys
import urllib.request

from common import PORT, PROJECTS, list_projects, project_dir

OK, WARN, BAD = "ok  ", "--  ", "XX  "

INSTALL_FFMPEG = {
    "win32": "winget install Gyan.FFmpeg   (then open a new terminal)",
    "darwin": "brew install ffmpeg",
}.get(sys.platform, "sudo apt install ffmpeg   (or your distro's package manager)")


def version(cmd):
    try:
        out = subprocess.run([cmd, "-version"], capture_output=True, text=True, timeout=20).stdout
        return out.splitlines()[0] if out else "?"
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    sys.stdout.reconfigure(errors="replace")
    problems = 0

    v = sys.version_info
    if v >= (3, 10):
        print(f"{OK}Python {v.major}.{v.minor}.{v.micro}")
    else:
        problems += 1
        print(f"{BAD}Python {v.major}.{v.minor}: need 3.10 or newer (python.org/downloads)")

    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            print(f"{OK}{version(tool)}")
        else:
            problems += 1
            print(f"{BAD}{tool} not found on PATH. Install it:  {INSTALL_FFMPEG}")
    if shutil.which("ffmpeg"):
        enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
        if "libx264" in enc:
            print(f"{OK}ffmpeg has libx264")
        else:
            problems += 1
            print(f"{BAD}this ffmpeg build has no libx264 encoder; install a full build ({INSTALL_FFMPEG})")

    try:
        import yt_dlp  # noqa: F401
        print(f"{OK}yt-dlp (optional: download footage from URLs)")
    except ImportError:
        print(f"{WARN}yt-dlp not installed (optional: pip install yt-dlp, to download footage from URLs)")
    try:
        import PIL  # noqa: F401
        print(f"{OK}Pillow (optional: captions, logos and cards burned onto renders)")
    except ImportError:
        print(f"{WARN}Pillow not installed (optional: pip install pillow, for captions/overlays on renders)")

    try:
        urllib.request.urlopen(f"http://localhost:{PORT}/api/projects", timeout=2)
        print(f"{OK}server running at http://localhost:{PORT}/")
    except OSError:
        print(f"{WARN}server not running (start it with \"Open cutting room.bat\", ./cutting-room.sh,"
              f" or python engine/serve.py --open)")

    pids = list_projects()
    print(f"\nProjects in {PROJECTS}:" if pids else f"\nNo projects yet in {PROJECTS}."
          " Ask Claude to start one, or try: python engine/demo.py")
    for pid in pids:
        d = project_dir(pid)
        clips = d / "_cache" / "clips.json"
        n = len(json.loads(clips.read_text(encoding="utf-8"))) if clips.is_file() else 0
        review = json.loads((d / "review.json").read_text(encoding="utf-8")) if (d / "review.json").is_file() else {}
        marked = sum(len(r.get("hl", [])) for r in review.get("clips", {}).values())
        renders = sorted((d / "edit" / "renders").glob("*.mp4")) if (d / "edit" / "renders").is_dir() else []
        notes = d / "edit" / "render-notes.json"
        open_notes = 0
        if notes.is_file():
            data = json.loads(notes.read_text(encoding="utf-8"))
            open_notes = sum(1 for r in data.get("renders", {}).values() for x in r.get("notes", [])
                             if x.get("status") != "done")
        state = f"{n} clips prepared" if n else "not prepared yet (run prepare.py)"
        print(f"  {pid}: {state}, {marked} highlights, {len(renders)} renders, {open_notes} open render notes")

    print("\nAll good." if not problems else f"\n{problems} problem(s) to fix first.")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
