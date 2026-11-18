---
name: find-clips
description: Find footage for a Cutting Room project (search drives, download clips the user owns) or scan prepared clips for promising moments and suggest highlights. Use when the user asks to find, gather, download or scan footage, or wants suggestions for what to use.
---

Follow "Phase 2: finding clips" in CLAUDE.md. Work out which the user wants:

**Gathering footage**
- Search the drives/folders they name for video files matching what they describe (name, date, size, folder).
  Present what you found (count, total length if cheap to get, sample names) and get a yes before adding to
  `project.json` (`source` folders or `files` entries). Then `python engine/prepare.py <id>`.
- URLs: only with their go-ahead and for footage they have the rights to:
  `python -m yt_dlp -f "bv*+ba/b" --merge-output-format mp4 -o "<source folder>/<name>.%(ext)s" <url>`

**Scanning for moments**
- Pick the clips worth scanning (long ones, unrated ones, or the ones they name). For each:
  `python engine/inspect_regions.py <id> <clip> 0 <dur>` (dur from `_cache/clips.json`).
- Look at the contact sheets in `projects/<id>/edit/sheets/` and the loudness/onset printout. Judge against the
  project brief and categories.
- Report a short list per clip: time range, what happens, why it fits, suggested category. Be honest that you're
  judging from frames and levels, not sound.
- If they want the suggestions in the editor: hard rule 3 in CLAUDE.md (they close the tab, you re-read the file,
  add highlights with notes starting `"Suggested: "`, set `savedAt` to now in ms, never touch their own marks), then
  tell them to reload.
