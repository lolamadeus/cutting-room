"""Contact sheets + audio profiles for picking exact cut points.

    python engine/inspect_regions.py <project-id>                      every highlight + rated clips with no highlights
    python engine/inspect_regions.py <project-id> <clip> <start> <end>  one region

Writes edit/sheets/<clip>_<start>.jpg (frames with timecodes) and prints, per region:
  - loudness per second (RMS dBFS, from the cached envelope)
  - onsets: sudden jumps in level (hits, impacts, UI blips): good cut points
"""
import json
import math
import subprocess
import sys

from common import ffmpeg_path, find_font, load_project, project_dir

_font = find_font(bold=True)
FONT = f"fontfile='{ffmpeg_path(_font)}':" if _font else ""


def db(v):
    return -99 if v <= 0 else 20 * math.log10(v / 1000)


def sheet(proxy, out, s, e, step):
    cols = 8
    n = max(1, int((e - s) / step))
    rows = math.ceil(n / cols)
    vf = (f"fps=1/{step},scale=240:135,"
          f"drawtext={FONT}text='%{{pts\\:hms\\:{s:.3f}}}':x=4:y=4:fontsize=15:fontcolor=white:box=1:boxcolor=black@0.6,"
          f"tile={cols}x{rows}:padding=2")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", str(proxy),
                    "-vf", vf, "-frames:v", "1", "-q:v", "4", str(out)], check=True)


def profile(wave, s, e):
    rate, rms, peak = wave["rate"], wave["rms"], wave["peak"]
    lines = []
    secs = []
    t = math.floor(s)
    while t < e:
        a, b = int(max(t, s) * rate), int(min(t + 1, e) * rate)
        seg = rms[a:b]
        secs.append(f"{t:>4.0f}s {db(max(seg)) if seg else -99:>4.0f}")
        t += 1
    for i in range(0, len(secs), 8):
        lines.append("   " + " | ".join(secs[i:i + 8]))
    # onsets: 30ms window RMS jumps >= 9 dB over the previous 300ms and lands above -32 dBFS
    on = []
    a0, a1 = int(s * rate), min(int(e * rate), len(rms) - 3)
    last = -1
    for i in range(max(a0, 30), a1):
        cur = db(max(rms[i:i + 3]))
        prev = db(sum(rms[i - 30:i]) / 30)
        if cur > -32 and cur - prev >= 9 and i - last > 25:
            on.append(f"{i / rate:.2f}({cur:.0f})")
            last = i
    pk = db(max(peak[a0:a1] or [0]))
    lines.append(f"   peak {pk:.1f} dBFS; onsets: " + (", ".join(on) if on else "none"))
    return "\n".join(lines)


def main():
    pid = sys.argv[1]
    cfg = load_project(pid)
    d = project_dir(pid)
    clips = {c["id"]: c for c in json.loads((d / "_cache" / "clips.json").read_text())}
    out = d / "edit" / "sheets"
    out.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) >= 5:
        regions = [(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), "")]
    else:
        review = json.loads((d / "review.json").read_text())
        regions = []
        for cid, r in review["clips"].items():
            if r.get("prio") == "dont" or cid not in clips:
                continue
            if r.get("hl"):
                regions += [(cid, x["s"], x["e"], x.get("note", "")) for x in r["hl"]]
            elif r.get("prio") in ("must", "try"):
                regions.append((cid, 0, clips[cid]["dur"], "(whole clip, no highlight)"))

    for cid, s, e, note in regions:
        c = clips[cid]
        step = 0.5 if e - s <= 24 else 1.0
        name = f"{cid}_{s:06.1f}.jpg"
        sheet(d / "_cache" / "proxy" / f"{cid}.mp4", out / name, s, e, step)
        wave = json.loads((d / "_cache" / "waves" / f"{cid}.json").read_text()) if c["audio"] else None
        print(f"\n## {cid}  {s:.1f}-{e:.1f} ({e - s:.1f}s)  sheet={name} step={step}s  {note}")
        if wave:
            print(profile(wave, s, e))


if __name__ == "__main__":
    main()
