# Cutting Room

A local, Claude-driven video editing workflow for **"go through hours of footage → pick the best bits → cut a reel"** jobs:
showreels, highlight reels, montages, family videos, trailers.

You do the part that needs taste (watching, marking the good moments, saying what's wrong with a cut). Claude does the
rest: setting up projects, finding and scanning footage, building the edit, rendering it with matched loudness, and
reworking it from your notes, version after version.

```
  set up + find clips  →  mark the best bits  →  cut + render v1  →  watch + leave notes  →  v2, v3 …
      (Claude)              (you, in the editor)      (Claude)         (you, notes page)       (Claude)
```

- **Editor** (in your browser): scrub every clip with a filmstrip and dB waveform, drag to mark highlights, tag and
  star them, set clip priorities, then arrange everything on a Board and play a rough cut against your target length.
- **Renderer**: cuts straight from your original files at full quality. Every segment is loudness-matched (EBU R128,
  plain gain, no squashing), with click-free micro-fades, optional L-cut audio tails, crops and fades, through an
  oversampled true-peak limiter. Segments are cached, so a v2 that changes one cut re-renders in seconds.
- **Render notes**: watch a render, press `N` to drop a note at any moment ("cut this", "too loud", "love it").
  Each note knows which segment, source clip and source time it's on, so Claude can act on it precisely and reply.

Everything runs on your machine. Your footage is never copied, moved or modified.

## What you need

- **[Claude Code](https://claude.com/claude-code)** (any Claude subscription that includes it): the desktop app, the
  CLI or the VS Code extension
- **Python 3.10+** (standard library only, no `pip install` needed for the core)
- **ffmpeg** on your PATH: `winget install Gyan.FFmpeg` (Windows), `brew install ffmpeg` (macOS), `sudo apt install ffmpeg` (Linux)
- Optional: `pip install yt-dlp` (download footage from URLs), `pip install pillow` (captions and cards on renders)

Don't worry about checking these yourself: Claude will on first run.

## Get started

```bash
git clone <this repo's URL> cutting-room
cd cutting-room
claude
```

(Or open the folder in the Claude desktop app's Code tab.) Then just talk to it:

> **"Set me up"** — checks your machine, explains the workflow, offers a demo project
>
> **"Start a new project for the clips in D:\Footage\Japan trip. I want a 2–3 minute travel montage."**

Claude knows this repo (see [CLAUDE.md](CLAUDE.md)), so you don't need to learn the commands. A few shortcuts are
built in as skills: `/setup`, `/new-project`, `/find-clips`, `/cut`.

Prefer to try it before pointing it at real footage? `python engine/demo.py` makes a demo project from generated test
clips in about 20 seconds.

**Opening the editor:** double-click `Open cutting room.bat` (Windows) or run `./cutting-room.sh` (macOS / Linux).
It starts the local server and opens the project hub at <http://localhost:8770/>. Each project folder also gets its
own "Open editor" shortcut.

## The workflow

1. **Set up a project.** Tell Claude where the footage is, what you're making, how long it should be, and what
   sections you think in (e.g. "Action, Landscapes, Food, People"). Claude writes the project config and prepares
   light proxies, filmstrips and waveforms.
2. **Find clips.** Claude can search your drives for footage, download clips you have the rights to, and pre-scan
   long recordings (contact sheets + audio hits) to suggest moments worth a look.
3. **Mark it up.** In the editor, go clip by clip. Drag along the lane under the waveform to mark a highlight, tag it,
   star key moments, set the clip's priority (`1`–`4`). Then use the **Board** to arrange the running order and
   **Play rough cut**. Write the overall direction in the Board's notes box.
4. **Cut.** Ask Claude for a cut. It reads your marks and direction, picks exact cut points (on hits and silences,
   not mid-word), writes an edit decision list and renders `v1`.
5. **Note it.** Open **Render notes** (top bar, or `/p/<project>/notes/`), watch the render and leave notes.
6. **Repeat.** Tell Claude "I've left notes on v1". It makes v2, marks each note done with a short reply, and
   tells you what changed. Go round until it's right.

The full walkthrough, with tips that make each stage faster, is in **[docs/GUIDE.md](docs/GUIDE.md)**.
File formats and every command are in **[docs/REFERENCE.md](docs/REFERENCE.md)**.

## Your data stays local

Everything you make lives in `projects/`, which is **git-ignored** (apart from its README). Your project settings,
marks, backups, proxies, edit lists, renders and notes never get committed, and `git pull` won't touch them.
Source footage stays wherever it already is; projects just point at it.

## Layout

```
cutting-room/
  CLAUDE.md                 how Claude should drive the workflow (read automatically by Claude Code)
  .claude/skills/           /setup, /new-project, /find-clips, /cut
  Open cutting room.bat     Windows launcher (server + browser)
  cutting-room.sh           macOS / Linux launcher
  engine/                   Python tools: prepare, serve, export_brief, inspect_regions, render, new_project, demo, doctor
  web/                      the hub, the editor and the render-notes page
  docs/                     GUIDE.md (how to use it), REFERENCE.md (formats and commands)
  projects/                 your projects (git-ignored)
```

## Improving it

Found something missing? Ask Claude to add it ("add a way to burn captions into renders"). General features go in
`engine/` and `web/`; one-off scripts for a single project stay in that project's `edit/` folder. Run
`python engine/doctor.py` and try the demo project before committing. Pull requests welcome.

## Licence

MIT, see [LICENSE](LICENSE).
