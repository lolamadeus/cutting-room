"""Local server for the cutting room: one server for every project.

    python engine/serve.py            -> http://localhost:8770/

  /                         project hub (web/index.html)
  /api/projects             project list + progress
  /p/<id>/                  editor page (web/editor.html) for that project
  /p/<id>/project.json      project settings
  /p/<id>/clips.json        clip metadata built by prepare.py
  /p/<id>/review.json       your marks (GET), POST /p/<id>/save to write it
  /p/<id>/media/<kind>/...  proxies, thumbs, strips, waves from _cache/
  /p/<id>/notes/            render notes page (web/notes.html): watch a render, leave timed notes
  /p/<id>/api/renders       renders in edit/renders/ with their segment timelines (from <name>.plan.json)
  /p/<id>/render/<file>     a rendered video from edit/renders/
  /p/<id>/render-notes.json the notes (GET), POST /p/<id>/save-notes to write edit/render-notes.json
"""
import http.server
import json
import shutil
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

from common import PORT, WEB, list_projects, load_project, project_dir, write_json

MEDIA_KINDS = {"proxy", "thumbs", "strips", "waves"}
BACKUP_EVERY = 10 * 60
BACKUPS_KEPT = 40
RENDER_SUFFIXES = ("_final", "_share", "_captioned")


def render_list(pid):
    """Every rendered video, newest first, with the segment timeline of the plan it came from."""
    d = project_dir(pid)
    rdir = d / "edit" / "renders"
    if not rdir.is_dir():
        return []
    plans = {p.name[: -len(".plan.json")]: p for p in rdir.glob("*.plan.json")}
    out = []
    for f in sorted(rdir.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True):
        base = f.stem
        for suf in RENDER_SUFFIXES:
            if base.endswith(suf) and base[: -len(suf)] in plans:
                base = base[: -len(suf)]
        segs = []
        if base in plans:
            fps = 60
            edl = d / "edit" / f"edl_{base}.json"
            if edl.is_file():
                try:
                    fps = json.loads(edl.read_text(encoding="utf-8")).get("fps", 60)
                except ValueError:
                    pass
            t = 0.0
            for p in json.loads(plans[base].read_text(encoding="utf-8")):
                dur = round((p["out"] - p["in"]) * fps) / fps
                segs.append({"n": p["n"], "start": round(t, 3), "dur": round(dur, 3), "clip": p["clip"], "in": p["in"],
                             "out": p["out"], "section": p.get("section", ""), "label": p.get("label", "")})
                t += dur
        st = f.stat()
        out.append({"file": f.name, "base": base, "size": st.st_size, "mtime": st.st_mtime, "segments": segs})
    return out


def project_summary(pid):
    cfg = load_project(pid)
    d = project_dir(pid)
    clips = json.loads((d / "_cache" / "clips.json").read_text()) if (d / "_cache" / "clips.json").is_file() else []
    review = json.loads((d / "review.json").read_text()) if (d / "review.json").is_file() else {}
    recs = review.get("clips", {})
    hls = [h for c in clips if (recs.get(c["id"], {}).get("prio") != "dont") for h in recs.get(c["id"], {}).get("hl", [])]
    return {
        "id": pid, "title": cfg.get("title", pid), "kind": cfg.get("kind", ""), "brief": cfg.get("brief", ""),
        "accent": cfg.get("accent"), "target": cfg.get("target"),
        "clips": len(clips), "minutes": round(sum(c["dur"] for c in clips) / 60, 1),
        "reviewed": sum(1 for c in clips if recs.get(c["id"], {}).get("prio")),
        "highlights": len(hls), "seconds": round(sum(h["e"] - h["s"] for h in hls), 1),
        "prepared": bool(clips), "savedAt": review.get("savedAt"),
    }


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    # ---------- routing ----------
    def resolve(self, raw_path):
        """URL path -> file on disk (or None)."""
        path = unquote(urlsplit(raw_path).path)
        parts = [p for p in path.split("/") if p]
        if not parts:
            return WEB / "index.html"
        if parts[0] == "p" and len(parts) >= 2:
            try:
                d = project_dir(parts[1])
            except FileNotFoundError:
                return None
            rest = parts[2:]
            if not rest:
                return WEB / "editor.html"
            if rest == ["clips.json"]:
                return d / "_cache" / "clips.json"
            if rest == ["review.json"]:
                return d / "review.json"
            if rest == ["notes"]:
                return WEB / "notes.html"
            if rest == ["render-notes.json"]:
                return d / "edit" / "render-notes.json"
            if len(rest) == 2 and rest[0] == "render" and ".." not in rest[1] and rest[1].lower().endswith(".mp4"):
                return d / "edit" / "renders" / rest[1]
            if len(rest) == 3 and rest[0] == "media" and rest[1] in MEDIA_KINDS and "/" not in rest[2] and ".." not in rest[2]:
                return d / "_cache" / rest[1] / rest[2]
            return None
        f = (WEB / Path(*parts)).resolve()
        return f if WEB.resolve() in f.parents else None

    def translate_path(self, path):
        f = self.resolve(path)
        return str(f) if f else str(WEB / "__missing__")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/projects":
            return self.send_json([project_summary(p) for p in list_projects()])
        parts = [p for p in unquote(path).split("/") if p]
        if len(parts) == 4 and parts[0] == "p" and parts[2:] == ["api", "renders"]:
            try:
                return self.send_json(render_list(parts[1]))
            except FileNotFoundError:
                return self.send_error(404)
        if len(parts) == 3 and parts[0] == "p" and parts[2] == "project.json":
            try:
                return self.send_json(load_project(parts[1]))
            except FileNotFoundError:
                return self.send_error(404)
        if len(parts) in (2, 3) and parts[0] == "p" and parts[-1] in (parts[1], "notes") and not path.endswith("/"):
            self.send_response(301)
            self.send_header("Location", path + "/")
            self.end_headers()
            return
        return super().do_GET()

    def send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- saving ----------
    def do_POST(self):
        parts = [p for p in unquote(urlsplit(self.path).path).split("/") if p]
        if not (len(parts) == 3 and parts[0] == "p" and parts[2] in ("save", "save-notes")):
            return self.send_error(404)
        try:
            d = project_dir(parts[1])
        except FileNotFoundError:
            return self.send_error(404)
        body = self.rfile.read(int(self.headers["Content-Length"]))
        try:
            data = json.loads(body)
        except ValueError:
            return self.send_error(400, "bad json")
        dest = d / "review.json" if parts[2] == "save" else d / "edit" / "render-notes.json"
        self.backup(d, dest)
        write_json(dest, data, separators=(",", ":"))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    @staticmethod
    def backup(d, dest):
        if not dest.is_file():
            return
        bdir = d / "backups"
        bdir.mkdir(exist_ok=True)
        prefix = dest.stem
        existing = sorted(bdir.glob(f"{prefix}-*.json"))
        if existing and time.time() - existing[-1].stat().st_mtime < BACKUP_EVERY:
            return
        shutil.copy2(dest, bdir / time.strftime(f"{prefix}-%Y%m%d-%H%M%S.json"))
        for old in existing[: max(0, len(existing) + 1 - BACKUPS_KEPT)]:
            old.unlink(missing_ok=True)

    # ---------- byte ranges so videos can seek ----------
    def send_head(self):
        rng = self.headers.get("Range")
        f = self.resolve(self.path)
        if not rng or not rng.startswith("bytes=") or not f or not f.is_file():
            return super().send_head()
        size = f.stat().st_size
        a, _, b = rng[6:].split(",")[0].partition("-")
        start = int(a) if a else max(0, size - int(b))
        end = min(int(b), size - 1) if a and b else size - 1
        if start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        fh = open(f, "rb")
        fh.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(f)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        self._remaining = end - start + 1
        return fh

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_remaining", None)
        try:
            if remaining is None:
                return super().copyfile(source, outputfile)
            self._remaining = None
            while remaining > 0:
                chunk = source.read(min(256 * 1024, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass


def main():
    import argparse
    import threading
    import webbrowser

    ap = argparse.ArgumentParser(description="Run the cutting-room server.")
    ap.add_argument("--open", nargs="?", const="", metavar="PROJECT",
                    help="open the hub (or a project's editor) in the browser")
    args = ap.parse_args()
    url = f"http://localhost:{PORT}/" + (f"p/{args.open}/" if args.open else "")
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:  # already running: just open the page
        print(f"Cutting room is already running at http://localhost:{PORT}/", flush=True)
        if args.open is not None:
            webbrowser.open(url)
        return
    server.daemon_threads = True
    print(f"Cutting room running at http://localhost:{PORT}/  (Ctrl+C to stop)", flush=True)
    if args.open is not None:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
