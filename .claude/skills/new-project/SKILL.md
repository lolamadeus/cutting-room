---
name: new-project
description: Create and prepare a new Cutting Room project from the user's footage folders, with Board categories and tags that fit what they're making. Use when the user wants to start a new video, reel, montage or edit.
---

Follow "Phase 1: new project" in CLAUDE.md.

1. In one short message, ask only for what's missing from: footage location(s), what it's for and who will watch,
   target length, the sections they think in, anything to listen/look for, must-use / never-use clips. Offer
   sensible defaults ("I'll use Opening / Highlights / Closing unless you'd rather...").
2. Check the folders exist and roughly how much footage there is (count and total size of video files).
3. `python engine/new_project.py "<Title>" "<folder>" ... --kind "..." --brief "..." --target MIN MAX [--recursive]`
4. Edit `projects/<id>/project.json` (see docs/REFERENCE.md): real `highlightTags` (a `board: true` category set with
   4–8 coloured options, plus any extra tag sets), `groups`/`groupRules` if the footage groups naturally, `exclude`
   for junk, an `accent` colour. Standing rules go in `brief`.
5. `python engine/prepare.py <id>` (background for big folders). Report clips, minutes, failures.
6. Make sure the server is running and give them the editor link `http://localhost:8770/p/<id>/` with three tips:
   drag under the waveform to mark, `1`–`4` for priority, `?` for shortcuts. Offer /find-clips to pre-scan long
   footage for moments.
