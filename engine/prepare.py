"""Scan a project's source folder(s) and build everything the editor page needs.

    python engine/prepare.py <project-id> [--jobs 3] [--force]

For each video it makes (in projects/<id>/_cache/):
  proxy/<clip>.mp4   light 540p H.264 copy for fast scrubbing (originals are never touched)
  thumbs/<clip>.jpg  list thumbnail
  strips/<clip>.jpg  filmstrip sprite (one tile every ~1.5s) for the timeline
  waves/<clip>.json  audio peak/RMS envelope, 100 values per second
and writes clips.json (metadata + group). Safe to re-run: only new or changed clips are processed.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from array import array
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import VIDEO_EXT, load_project, project_dir, write_json

TW, TH = 112, 63          # filmstrip tile size (16:9)
WAVE_RATE = 100           # envelope values per second
WAVE_SR = 6000            # sample rate used to compute the envelope


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, check=True, **kw)


def probe(f: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(f)], text=True, encoding="utf-8", errors="replace").stdout
    p = json.loads(out)
    vs = next((s for s in p["streams"] if s["codec_type"] == "video"), None)
    has_audio = any(s["codec_type"] == "audio" for s in p["streams"])
    dur = float(p["format"].get("duration") or (vs or {}).get("duration") or 0)
    w = h = fps = 0
    if vs:
        w, h = vs.get("width", 0), vs.get("height", 0)
        rot = 0
        for sd in vs.get("side_data_list", []):
            rot = abs(int(sd.get("rotation", 0) or 0))
        if rot in (90, 270):
            w, h = h, w
        num, den = (vs.get("avg_frame_rate") or vs.get("r_frame_rate") or "0/1").split("/")
        fps = round(int(num) / int(den)) if int(den) else 0
    return {"dur": round(dur, 3), "w": w, "h": h, "fps": fps, "audio": has_audio}


def stale(out: Path, src: Path, force: bool) -> bool:
    return force or not out.is_file() or out.stat().st_size == 0 or out.stat().st_mtime < src.stat().st_mtime


def make_proxy(src: Path, out: Path):
    tmp = out.with_suffix(".tmp.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
         "-vf", "scale='if(gt(iw,ih),960,-2)':'if(gt(iw,ih),-2,960)',fps=30",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-g", "6", "-bf", "0", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", str(tmp)])
    tmp.replace(out)


def make_thumb(proxy: Path, out: Path, dur: float):
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur * 0.3:.3f}", "-i", str(proxy), "-frames:v", "1",
         "-vf", "scale=192:108:force_original_aspect_ratio=increase,crop=192:108", "-q:v", "4", str(out)])


def tile_count(dur: float) -> int:
    return max(24, min(400, round(dur / 1.5)))


def make_strip(proxy: Path, out: Path, dur: float):
    n = tile_count(dur)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(proxy), "-an",
         "-vf", f"fps={n / max(dur, 0.1):.6f},scale={TW}:{TH}:force_original_aspect_ratio=increase,crop={TW}:{TH},tile={n}x1",
         "-frames:v", "1", "-q:v", "5", str(out)])


def make_wave(proxy: Path, out: Path):
    raw = run(["ffmpeg", "-v", "error", "-i", str(proxy), "-vn", "-ac", "1", "-ar", str(WAVE_SR),
               "-f", "s16le", "-"]).stdout
    a = array("h")
    a.frombytes(raw[: len(raw) // 2 * 2])
    step = WAVE_SR // WAVE_RATE
    peak, rms = [], []
    for i in range(0, len(a), step):
        seg = a[i:i + step]
        if not seg:
            break
        peak.append(round(max(max(seg), -min(seg)) / 32768 * 1000))
        rms.append(round((sum(x * x for x in seg) / len(seg)) ** 0.5 / 32768 * 1000))
    write_json(out, {"rate": WAVE_RATE, "peak": peak, "rms": rms}, separators=(",", ":"))


def group_for(name: str, rules: list, fixed: str | None = None) -> str:
    if fixed:
        return fixed
    for r in rules:
        if re.search(r["match"], name, re.I):
            return r["group"]
    return "Other"


def file_entries(cfg: dict) -> dict:
    """Explicit clips from project.json "files": paths, or {path, group, catalogueId} objects.

    Lets clips come from anywhere (a hand-picked list, or another tool that writes project.json),
    not only from the "source" folders. "catalogueId" is passed through to clips.json untouched."""
    out = {}
    for e in cfg.get("files", []):
        e = {"path": e} if isinstance(e, str) else e
        p = Path(e["path"])
        if p.is_file() and p.suffix.lower() in VIDEO_EXT:
            out[p] = e
    return out


def find_sources(cfg: dict) -> list:
    files = []
    for folder in cfg["source"]:
        d = Path(folder)
        it = d.rglob("*") if cfg.get("recursive") else d.iterdir()
        files += [f for f in it if f.is_file() and f.suffix.lower() in VIDEO_EXT]
    exclude = [re.compile(x, re.I) for x in cfg.get("exclude", [])]
    files = [f for f in files if not any(x.search(f.name) for x in exclude)]
    files += [f for f in file_entries(cfg) if f not in files]
    return sorted(files, key=lambda f: f.name.lower())


def main():
    # clip names can contain characters the Windows console can't show (e.g. full-width colons from YouTube titles)
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    cfg = load_project(args.project)
    pdir = project_dir(args.project)
    cache = pdir / "_cache"
    for sub in ("proxy", "thumbs", "strips", "waves"):
        (cache / sub).mkdir(parents=True, exist_ok=True)

    files = find_sources(cfg)
    explicit = file_entries(cfg)
    if not files:
        sys.exit(f"No videos found in {cfg['source']} or project.json \"files\"")

    # unique, filesystem-safe clip ids (stem; add the extension if two files share a stem)
    stems = {}
    for f in files:
        stems.setdefault(f.stem.lower(), []).append(f)
    ids = {f: (f.stem if len(stems[f.stem.lower()]) == 1 else f"{f.stem}_{f.suffix[1:]}") for f in files}
    seen = {}
    for f in files:  # same name and extension in different folders: add a short path hash
        seen.setdefault(ids[f].lower(), []).append(f)
    for dupes in seen.values():
        if len(dupes) > 1:
            for f in dupes:
                ids[f] = f"{ids[f]}_{hashlib.sha1(str(f).lower().encode()).hexdigest()[:6]}"

    print(f"{len(files)} videos ({len(explicit)} listed in \"files\") from {', '.join(cfg['source']) or 'file list'}", flush=True)
    t0 = time.time()
    done = 0

    def work(f: Path):
        cid = ids[f]
        meta = probe(f)
        proxy = cache / "proxy" / f"{cid}.mp4"
        if stale(proxy, f, args.force):
            make_proxy(f, proxy)
        if stale(cache / "thumbs" / f"{cid}.jpg", proxy, args.force):
            make_thumb(proxy, cache / "thumbs" / f"{cid}.jpg", meta["dur"])
        if stale(cache / "strips" / f"{cid}.jpg", proxy, args.force):
            make_strip(proxy, cache / "strips" / f"{cid}.jpg", meta["dur"])
        if meta["audio"] and stale(cache / "waves" / f"{cid}.json", proxy, args.force):
            make_wave(proxy, cache / "waves" / f"{cid}.json")
        entry = explicit.get(f, {})
        clip = {"id": cid, "file": f.name, "src": str(f), "size": f.stat().st_size, **meta,
                "group": group_for(f.name, cfg["groupRules"], entry.get("group")),
                "tiles": tile_count(meta["dur"]), "tw": TW, "th": TH}
        if entry.get("catalogueId"):
            clip["catalogueId"] = entry["catalogueId"]
        return clip

    clips, failed = [], []
    with ThreadPoolExecutor(args.jobs) as ex:
        futs = {ex.submit(work, f): f for f in files}
        for fut in as_completed(futs):
            f = futs[fut]
            done += 1
            try:
                clips.append(fut.result())
                print(f"[{done}/{len(files)}] {f.name}", flush=True)
            except subprocess.CalledProcessError as e:
                failed.append(f.name)
                print(f"[{done}/{len(files)}] FAILED {f.name}: {e.stderr.decode(errors='replace')[-400:]}", flush=True)

    order = {g: i for i, g in enumerate(cfg["groups"])}
    clips.sort(key=lambda c: (order.get(c["group"], len(order)), c["file"].lower()))
    write_json(cache / "clips.json", clips, indent=1)
    mins = sum(c["dur"] for c in clips) / 60
    print(f"DONE: {len(clips)} clips, {mins:.1f} min of footage, {time.time() - t0:.0f}s"
          + (f"; {len(failed)} failed: {failed}" if failed else ""), flush=True)


if __name__ == "__main__":
    main()
