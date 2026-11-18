---
name: setup
description: First-run setup for the Cutting Room. Checks Python and ffmpeg, explains the workflow, and offers the demo project or a first real project. Use when the user says "set me up", "get started", "how does this work", or has no projects yet.
---

Follow "First contact" in CLAUDE.md:

1. Run `python engine/doctor.py`. For anything marked `XX`, give the exact install command for the user's OS and
   wait for them. Mention the optional extras (`yt-dlp`, `pillow`) only if they're missing, as optional.
2. Explain the loop in 4–6 plain lines: set up a project → find clips → you mark highlights in the editor → Claude cuts
   and renders → you leave notes on the render → Claude makes the next version.
3. If projects already exist, list them with their state (doctor prints it) and ask what they'd like to work on.
4. Otherwise offer: **try the demo** (`python engine/demo.py`, then start the server and open
   `http://localhost:8770/p/demo/`, and suggest they mark a couple of highlights and then ask for a cut) or **start a
   real project** (go to /new-project).

Keep it friendly and short. Don't dump the whole guide; point at `docs/GUIDE.md` for later.
