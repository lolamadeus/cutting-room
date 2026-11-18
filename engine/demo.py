"""Make a demo project from generated test footage, to try the editor without your own clips.

    python engine/demo.py            creates projects/demo (footage in projects/demo/footage/), then prepares it

Three short clips (test patterns with beeps and tones, so there's something to see on the filmstrip and in the
waveform) and a couple of example highlights. Delete projects/demo when you're done; nothing else is touched.
"""
import random
import subprocess
import sys
import time

from common import PROJECTS, write_json
from new_project import write_launcher

PID = "demo"

# name, video source, audio (aevalsrc expression: plucks and swells, so the waveform and onsets have shape), seconds
CLIPS = [
    ("Pattern drive", "testsrc2=size=1280x720:rate=30",
     "aevalsrc=0.5*sin(2*PI*330*t)*exp(-5*mod(t\\,1.5)):s=48000", 24),
    ("Fractal zoom", "mandelbrot=size=1280x720:rate=30",
     "aevalsrc=0.35*sin(2*PI*196*t)*(0.55+0.45*sin(2*PI*t/6)):s=48000", 18),
    ("Game of life", "life=size=320x180:rate=30:mold=10:ratio=0.1:death_color=#1a1a2e:life_color=#ff6b3d,scale=1280:720:flags=neighbor",
     "aevalsrc=0.04*(random(0)-0.5)+0.6*(random(1)-0.5)*exp(-12*mod(t\\,2.5)):s=48000", 20),
]


def main():
    d = PROJECTS / PID
    if (d / "project.json").exists():
        sys.exit(f"The demo project already exists: {d}\nDelete that folder to make it again.")
    footage = d / "footage"
    footage.mkdir(parents=True, exist_ok=True)
    for name, v, a, dur in CLIPS:
        out = footage / f"{name}.mp4"
        print(f"making {out.name}", flush=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", v, "-f", "lavfi", "-i", a,
                        "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", str(out)], check=True)

    cfg = {
        "title": "Demo project",
        "kind": "Try-out (generated footage)",
        "source": str(footage),
        "target": {"min": 20, "max": 40},
        "brief": "A 20-40 second test cut. Open with the fractal, end on the game of life.",
        "accent": "#ff6b3d",
        "groups": ["Patterns", "Organic"],
        "groupRules": [{"match": "life|fractal", "group": "Organic"}, {"match": ".", "group": "Patterns"}],
        "highlightTags": [
            {"id": "cat", "label": "Category", "mode": "single", "board": True, "options": [
                {"id": "open", "label": "Opening", "color": "#9b5de5"},
                {"id": "mid", "label": "Middle", "color": "#3b82f6"},
                {"id": "end", "label": "Ending", "color": "#14b8a6"}]},
            {"id": "focus", "label": "Watch for", "mode": "multi", "options": [
                {"id": "motion", "label": "Motion"}, {"id": "colour", "label": "Colour"}, {"id": "sound", "label": "Sound"}]},
        ],
    }
    write_json(d / "project.json", cfg, indent=2)
    write_launcher(d, PID)

    rid = lambda: "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(8))
    review = {"v": 1, "savedAt": int(time.time() * 1000), "clips": {
        "Fractal zoom": {"prio": "must", "notes": "Example marks: replace them with your own.", "hl": [
            {"id": rid(), "s": 2.0, "e": 8.0, "note": "nice slow push in", "key": True, "tags": {"cat": "open", "focus": ["motion"]}}]},
        "Pattern drive": {"prio": "try", "notes": "", "hl": [
            {"id": rid(), "s": 5.0, "e": 11.0, "note": "", "key": False, "tags": {"cat": "mid", "focus": ["sound"]}}]},
    }}
    write_json(d / "review.json", review, indent=1)

    print("preparing (proxies, filmstrips, waveforms)...", flush=True)
    subprocess.run([sys.executable, str(PROJECTS.parent / "engine" / "prepare.py"), PID], check=True)
    print(f"\nDemo ready. Open the cutting room and pick \"Demo project\", or go to http://localhost:8770/p/{PID}/")


if __name__ == "__main__":
    main()
