# Cutting Room: how to use it

This is the long version. The short version: open the folder in Claude Code and say what you want to make.

- [1. First run](#1-first-run)
- [2. Start a project](#2-start-a-project)
- [3. Find clips](#3-find-clips)
- [4. Mark it up in the editor](#4-mark-it-up-in-the-editor)
- [5. The first cut](#5-the-first-cut)
- [6. Render notes and the next version](#6-render-notes-and-the-next-version)
- [7. Finishing](#7-finishing)
- [Workflow tips](#workflow-tips)
- [Troubleshooting](#troubleshooting)

---

## 1. First run

Open the repo in Claude Code (`claude` in a terminal inside the folder, or the desktop app's Code tab) and say
**"set me up"** (or type `/setup`). Claude will:

- run `python engine/doctor.py` to check Python, ffmpeg and the optional extras, and tell you how to install anything
  missing for your OS
- explain the workflow in a few lines
- offer to make the demo project, so you can try the editor before using real footage

The editor runs at <http://localhost:8770/>. Start it with `Open cutting room.bat` (Windows), `./cutting-room.sh`
(macOS / Linux), or ask Claude to open it. Leave it running while you work; it's a tiny local server.

## 2. Start a project

One project per video you're making. Tell Claude:

- **where the footage is**: one or more folders (with or without subfolders), or a list of specific files
- **what it's for**: "sound design showreel for game studios", "our wedding, for the family", "a 60s trailer"
- **target length**: e.g. 2–3 minutes. The Board shows a running total against it.
- **the sections you think in**: these become the colour-coded categories on the Board, e.g.
  *Opening / Action / Quiet moments / Finale*, or *Combat / UI / Creatures / Cinematics*
- **anything to listen or look for** (optional): extra tags like *Foley / VO / Music*, or *Wide / Close-up / Drone*
- **groups** (optional): how to section the clip list, e.g. by camera, day or game. Claude can set rules that group
  clips by filename.

Claude writes `projects/<id>/project.json` and runs `prepare.py`, which makes 540p proxies, thumbnails, filmstrips and
waveforms for every clip. That takes roughly a few seconds per minute of footage, and only new or changed clips are
processed when you re-run it. Your originals are never touched.

> **Tip:** write a real brief. "Showreel for audio leads at mobile studios; open on the biggest moment; no music-only
> clips; must include the boss fight" gives Claude a lot to work with when it cuts, and it's shown at the top of the
> editor so you remember what you're aiming for.

## 3. Find clips

Claude can help get the footage together before you start watching:

- **On your drives:** "find all my screen recordings from August", "find every clip with 'boss' in the name on D:".
  Claude searches and adds the folders or files to the project.
- **From the web:** "download this video I made: <url>". Claude uses `yt-dlp` and saves to your source folder.
  (Only footage you have the right to use.)
- **Scanning long recordings:** for an hour of gameplay or a long vlog, ask "scan the long clips and suggest moments".
  Claude makes contact sheets (a grid of frames with timecodes) and an audio profile (loudness per second, hits and
  impacts), looks through them, and adds suggested highlights to the editor, each with a note saying why. You still
  decide: keep, trim or delete them.
- **Spotting duplicates and junk:** "which clips are near-duplicates?", "flag clips with no audio".

Ask Claude to do this *before* you open the editor, or close the editor tab while it writes suggestions (see
[the tip on editing at the same time](#claude-and-you-editing-the-same-file)).

## 4. Mark it up in the editor

Open the hub and click your project. Press `?` at any time for every shortcut.

### Review tab: clip by clip

- **Mark a highlight:** drag along the lane under the waveform. Or press `H` while it plays and `H` again to stop,
  or `I` / `O` to set in and out at the playhead.
- **Adjust:** drag a highlight's ends to trim, its middle to move. Click it to play just that bit.
- **Tag it:** pick its category (`Shift`+`1`…`9`) and any other tags, and write a note if there's something Claude
  should know ("the hit at the end is the good bit", "music bleeds in after 4s").
- **Star key moments** with `K`. Claude treats them as the moments a section is built around.
- **Clip priority:** `1` Must use · `2` Try to use · `3` If there's space · `4` Don't use. `U` jumps to the next clip
  without one, which is the quickest way to get through a big folder.
- **Clip notes:** for anything about the whole clip ("this is a mock-up, not real gameplay").
- **Zoom:** scroll over the timeline (or `=` / `-` / `0`) on long clips. The waveform is in dB, so quiet detail shows.

### Board tab: the running order

Every highlight, grouped into your categories, with the total length against your target.

- Drag cards to reorder them or move them between categories; drag a category header to reorder sections.
- Choose which priorities count towards the total.
- **Play rough cut** plays everything back to back. It's the fastest way to feel whether the order works.
- Write the **edit direction** in the notes box: pacing, what to open and close on, what to avoid. Claude reads it
  before every cut.

Everything autosaves to `projects/<id>/review.json`, with a timestamped backup every 10 minutes in `backups/`.

## 5. The first cut

Tell Claude **"make the first cut"** (or `/cut`). It will:

1. export your marks to an edit brief (`edit/brief.md` and `edit/selects.json`), in Board order
2. inspect each highlight to find exact cut points: contact sheets plus audio hits and silences, so cuts land on
   impacts or between sounds rather than mid-word or mid-reverb
3. write a small script (`edit/make_edl_v1.py`) that builds the edit decision list, so every version is reproducible
   and easy to diff
4. render `edit/renders/<name>_v1.mp4` from your original files, with matched loudness, micro-fades and any audio
   tails, plus a report of every segment's timing and levels
5. summarise the cut for you (length, loudness, what it did with your marks) in `edit/CUT_v1.md`

Ask for anything you'd ask an editor: "keep it under 2:30", "open with the dragon", "let the explosions ring out",
"1080p30 this time", "crop the browser bar out of that screen recording".

## 6. Render notes and the next version

Open **Render notes** from the editor's top bar (or `http://localhost:8770/p/<id>/notes/`) and pick the render.

- `N` drops a note at the playhead; `I` then `O` (or drag along the lane) for a stretch.
- Tag each note **Change / Cut it / Mix / Love it**. "Love it" notes matter: they tell Claude what not to touch.
- The strip under the video shows every segment, so you can see which source clip you're on.
- There's an overall notes box for the whole render.

When you're done, tell Claude **"I've left notes on v1"**. It makes v2 from v1's script, then marks each note done
with a short reply ("Cut in v2", "Lowered 3 dB and let the tail ring out"). Reload the notes page to see the replies;
untick a note's *Done* if you disagree, and it goes round again.

Earlier renders are kept, so you can always compare or go back.

## 7. Finishing

- **Captions, logos, title or end cards:** the renderer cuts picture and sound only. Ask Claude to add a text/image
  pass; it writes a per-project overlay script (needs `pip install pillow`) that outputs `<name>_final.mp4`. The notes
  page still maps notes on `_final` renders back to segments.
- **A smaller file for uploading:** "make a share copy" gives `<name>_share.mp4`.
- **Different delivery specs:** resolution, frame rate and loudness target are per edit (`-14 LUFS` suits most
  streaming sites; the default is `-13`).

---

## Workflow tips

**Mark generously, then cut.** It's faster to mark everything that might work and let the Board and the length
meter force the choices than to agonise clip by clip. Use priorities to say what can go first.

**Marks are rough on purpose.** You don't need frame-accurate highlights; Claude refines each cut point by looking at
frames and audio around your marks. Mark the moment, roughly, and add a note if the exact point matters.

**Notes beat re-marking.** After v1, it's usually quicker to leave render notes than to go back to the editor.
"Start this 0.5 s later", "swap these two", "too long, halve it" all work.

**Be specific about sound.** Claude can see levels and hits but can't hear. Notes like "the music bleeds in at the
end of this", "the reverb is cut off", or "this is quieter than it looks" are exactly what it can't work out alone.

**Say what you love.** A "Love it" note, or a ★ on a highlight, protects it from being trimmed in later versions.

**Keep the direction note current.** Big-picture changes ("less battle back to back", "end on something quiet") go
in the Board's edit-direction box, and Claude rereads it before each version.

**Let Claude remember.** Rules that apply to the whole project ("never use the intro clip", "no music-only clips",
"don't caption client names") belong in the project brief or edit direction, not just in chat, so they survive into
future sessions.

**Big folders.** Use groups (by game, camera or day) and the `U` key. Set obvious junk to *Don't use* (`4`) quickly
and move on. Hundreds of clips are fine.

<a name="claude-and-you-editing-the-same-file"></a>
**Claude and you editing the same file.** The editor and the notes page autosave the whole file. If Claude writes
suggestions into your marks, or replies to notes, while the page is open, your next autosave could overwrite them.
So: close the tab (or stop editing) before asking Claude to change marks, and reload the page after it's done.
Claude will remind you.

**Backups.** `projects/<id>/backups/` keeps the last 40 snapshots of your marks and notes. If something goes wrong,
ask Claude to restore one.

**Moving footage.** Projects point at your files by path. If you move the footage, ask Claude to update the
project's source folders and re-run prepare; your marks are kept (they're keyed by file name).

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| "Can't reach the cutting-room server" | Start it again: `Open cutting room.bat` / `./cutting-room.sh`, then refresh. |
| `ffmpeg` not found | Install it (see the README), then open a **new** terminal / restart Claude Code so PATH updates. |
| A clip shows no waveform | It has no audio track. Normal for some screen recordings. |
| A clip failed in prepare | Usually a damaged or unusual file. Claude can check it with `ffprobe` and often re-wrap it. |
| Port 8770 is in use | Something else uses it. Change `PORT` in `engine/common.py`. |
| Editor looks out of date after Claude changed marks | Reload the page. The newest save wins. |
| Render is too quiet / loud | Ask for a different loudness target, or note specific segments on the notes page. |
