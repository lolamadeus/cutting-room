"""Render an edit decision list (EDL) to a finished video, with a loudness-matching pass.

    python engine/render.py <project-id> <edl.json> [--jobs 4]

EDL (JSON) format:
{
  "name": "showreel_v1",                    output file name (edit/renders/<name>.mp4)
  "width": 1920, "height": 1080, "fps": 60,
  "loudness": {
    "target": -13,        LUFS each segment is pulled towards (integrated, measured on the segment itself)
    "peakAllowance": 1.5, dB a segment's true peak may exceed the ceiling before the master limiter (keeps transients intact)
    "ceiling": -1.0,      dBTP master ceiling (oversampled limiter)
    "maxBoost": 12        never raise a segment by more than this
  },
  "defaults": { "fadeIn": 0.012, "fadeOut": 0.012, "tail": 0 },   audio micro-fades (seconds) so cuts never click
  "segments": [
    { "clip": "<clip id>", "in": 12.3, "out": 15.8, "section": "Combat", "label": "...",
      "fadeIn": 0.05, "fadeOut": 0.3,       optional audio fades
      "tail": 0.35,                         optional: audio carries on this long past the cut, fading out under the
                                            next segment (an L-cut), so reverbs and decays aren't chopped off.
                                            With a tail, fadeOut is ignored; the tail itself is the fade.
      "vFadeIn": 0.3, "vFadeOut": 0.3,      optional fades from / to black
      "blackFrom": 51.95,                   optional: picture goes black from this source time (audio continues)
      "crop": [x, y, w, h],                 optional: use only this rectangle of the source picture (source pixels),
                                            e.g. to cut a video player's title bar and controls out of a screen grab
      "gain": -2 }                          optional manual trim in dB, applied on top of the normalisation
  ]
}

Normalisation is plain gain per segment (no compression), so each segment keeps its own dynamics. The gain aims every
segment at the same integrated loudness, but is capped so peaks never get pushed more than `peakAllowance` dB into the
limiter. The master then goes through a 4x-oversampled peak limiter at the ceiling, which only touches the odd transient.
Original footage is read directly (never the proxies) and is never modified.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import project_dir, write_json


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)


def measure(src, s, dur):
    """Integrated loudness (LUFS) and true peak (dBTP) of a stretch of a file."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{s:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
                        "-vn", "-af", "aresample=48000,ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = p.stderr[p.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", tail)
    lra = re.search(r"LRA:\s+(-?[\d.]+) LU", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
    f = lambda m: -70.0 if not m or m.group(1) == "-inf" else float(m.group(1))
    return {"I": f(i), "TP": f(tp), "LRA": f(lra)}


def seg_key(seg, gain, cfg):
    blob = json.dumps([seg, round(gain, 2), cfg], sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:10]


def render_segment(seg, src, src_dur, gain, out, W, H, fps, dflt):
    """Picture -> out (.mkv, exactly n frames); sound -> out.wav (picture length + tail)."""
    n = max(1, round((seg["out"] - seg["in"]) * fps))
    dur = n / fps
    fi, fo = seg.get("fadeIn", dflt["fadeIn"]), seg.get("fadeOut", dflt["fadeOut"])
    tail = max(0.0, min(seg.get("tail", dflt["tail"]), src_dur - seg["out"]))
    adur = dur + tail
    crop = [f"crop={seg['crop'][2]}:{seg['crop'][3]}:{seg['crop'][0]}:{seg['crop'][1]}"] if seg.get("crop") else []
    v = crop + [f"fps={fps}", f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos",
         f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black", "setsar=1", "format=yuv420p"]
    if seg.get("vFadeIn"):
        v.append(f"fade=t=in:st=0:d={seg['vFadeIn']}")
    if seg.get("blackFrom") is not None:
        v.append(f"fade=t=out:st={max(0, seg['blackFrom'] - seg['in']):.3f}:d=0.04")
    elif seg.get("vFadeOut"):
        v.append(f"fade=t=out:st={dur - seg['vFadeOut']:.3f}:d={seg['vFadeOut']}")
    a = ["aresample=48000", "aformat=sample_fmts=fltp:channel_layouts=stereo", f"volume={gain:.2f}dB",
         "apad", f"atrim=0:{adur:.6f}", "asetpts=N/SR/TB"]
    if fi:
        a.append(f"afade=t=in:st=0:d={fi}")
    if tail > 0.01:
        a.append(f"afade=t=out:st={dur:.6f}:d={tail:.3f}:curve=qsin")
    elif fo:
        a.append(f"afade=t=out:st={dur - fo:.6f}:d={fo}")
    tmp, tmpa = out.with_suffix(".tmp.mkv"), out.with_suffix(".tmp.wav")
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{seg['in']:.3f}", "-t", f"{adur + 0.5:.3f}", "-i", str(src),
         "-filter_complex", f"[0:v]{','.join(v)}[v];[0:a]{','.join(a)}[a]",
         "-map", "[v]", "-frames:v", str(n), "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-g", str(fps), str(tmp),
         "-map", "[a]", "-c:a", "pcm_s24le", str(tmpa)])
    tmp.replace(out)
    tmpa.replace(out.with_suffix(".wav"))
    return dur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("edl")
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()

    d = project_dir(args.project)
    edl_path = Path(args.edl) if Path(args.edl).is_absolute() else (d / "edit" / args.edl if (d / "edit" / args.edl).is_file() else Path(args.edl))
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    clips = {c["id"]: c for c in json.loads((d / "_cache" / "clips.json").read_text())}
    W, H, fps = edl.get("width", 1920), edl.get("height", 1080), edl.get("fps", 60)
    L = {"target": -13, "peakAllowance": 1.5, "ceiling": -1.0, "maxBoost": 12, **edl.get("loudness", {})}
    dflt = {"fadeIn": 0.012, "fadeOut": 0.012, "tail": 0.0, **edl.get("defaults", {})}
    segs = edl["segments"]
    for s in segs:
        if s["clip"] not in clips:
            sys.exit(f"Unknown clip {s['clip']!r}")
        if not (0 <= s["in"] < s["out"] <= clips[s["clip"]]["dur"] + 0.01):
            sys.exit(f"Bad in/out for {s['clip']}: {s['in']}–{s['out']}")

    work = d / "edit" / "cache"
    (work / "segs").mkdir(parents=True, exist_ok=True)
    out_dir = d / "edit" / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # 1. loudness of every segment (cached)
    lpath = work / "loudness.json"
    lcache = json.loads(lpath.read_text()) if lpath.is_file() else {}
    keyf = lambda s: f"{s['clip']}|{s['in']:.3f}|{s['out']:.3f}"
    todo = [s for s in segs if keyf(s) not in lcache]
    with ThreadPoolExecutor(args.jobs * 2) as ex:
        for s, m in zip(todo, ex.map(lambda s: measure(clips[s["clip"]]["src"], s["in"], s["out"] - s["in"]), todo)):
            lcache[keyf(s)] = m
    write_json(lpath, lcache, indent=1)
    print(f"measured {len(todo)} segments ({time.time() - t0:.0f}s)", flush=True)

    # 2. gain per segment
    plan = []
    for i, s in enumerate(segs):
        m = lcache[keyf(s)]
        want = L["target"] - m["I"]
        room = L["ceiling"] + L["peakAllowance"] - m["TP"]
        g = min(want, room, L["maxBoost"]) + s.get("gain", 0)
        plan.append({"n": i + 1, **s, "measured": m, "gainDb": round(g, 2),
                     "limitedBy": "peak" if room < want else ("maxBoost" if L["maxBoost"] < want else "target")})

    # 3. render segments (cached by settings)
    def do(p):
        s = {k: p[k] for k in p if k not in ("n", "measured", "gainDb", "limitedBy", "label", "section", "note")}
        out = work / "segs" / f"{p['n']:03d}_{seg_key(s, p['gainDb'], [W, H, fps, dflt])}.mkv"
        if not (out.is_file() and out.with_suffix(".wav").is_file()):
            c = clips[p["clip"]]
            render_segment(p, c["src"], c["dur"], p["gainDb"], out, W, H, fps, dflt)
        return out
    with ThreadPoolExecutor(args.jobs) as ex:
        files = list(ex.map(do, plan))
    keep = {f.stem for f in files}
    for f in list((work / "segs").glob("*.mkv")) + list((work / "segs").glob("*.wav")):
        if f.stem not in keep and ".tmp" not in f.name:
            f.unlink()
    print(f"rendered segments ({time.time() - t0:.0f}s)", flush=True)

    # 4. join picture; lay each segment's sound on the timeline at its cut (tails overlap the next cut); master limiter
    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{f.as_posix()}'\n" for f in files), encoding="utf-8")
    name = edl.get("name", edl_path.stem)
    final = out_dir / f"{name}.mp4"
    lim = 10 ** ((L["ceiling"] - 0.3) / 20)
    starts, t = [], 0
    for p in plan:
        starts.append(round(t * 48000))
        t += max(1, round((p["out"] - p["in"]) * fps)) / fps
    total = t
    ins, graph = [], []
    for i, f in enumerate(files):
        ins += ["-i", str(f.with_suffix(".wav"))]
        graph.append(f"[{i + 1}:a]adelay=delays={starts[i]}S:all=1[a{i}]")
    graph.append("".join(f"[a{i}]" for i in range(len(files))) +
                 f"amix=inputs={len(files)}:normalize=0:duration=longest,atrim=0:{total:.6f},"
                 f"aresample=192000,alimiter=limit={lim:.4f}:attack=1:release=80:level=0:latency=1,aresample=48000[a]")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), *ins,
         "-filter_complex", ";".join(graph),
         "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-r", str(fps), "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", str(final.with_suffix(".tmp.mp4"))])
    final.with_suffix(".tmp.mp4").replace(final)

    # 5. report
    m = measure(final, 0, 10000)
    t = 0.0
    lines = [f"{name}: {sum(round((p['out'] - p['in']) * fps) / fps for p in plan):.1f}s, {len(plan)} segments",
             f"master: {m['I']:.1f} LUFS integrated, true peak {m['TP']:.1f} dBTP, loudness range {m['LRA']:.1f} LU", ""]
    section = None
    for p in plan:
        dur = round((p["out"] - p["in"]) * fps) / fps
        if p.get("section") != section:
            section = p.get("section")
            lines.append(f"-- {section}")
        mm = p["measured"]
        lines.append(f"{p['n']:>3} {int(t // 60)}:{t % 60:05.2f}  {p['clip']} {p['in']:.2f}-{p['out']:.2f} ({dur:.1f}s)  "
                     f"{mm['I']:.1f} LUFS / {mm['TP']:.1f} dBTP -> {p['gainDb']:+.1f} dB ({p['limitedBy']})  {p.get('label', '')}")
        t += dur
    report = "\n".join(lines)
    (out_dir / f"{name}.txt").write_text(report + "\n", encoding="utf-8")
    write_json(out_dir / f"{name}.plan.json", plan, indent=1)
    print(report)
    print(f"\n-> {final} ({final.stat().st_size / 1e6:.0f} MB, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
