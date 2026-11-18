---
name: cut
description: Build and render the next version of a Cutting Room edit, the first cut from the user's marks, or a new version from their render notes, then reply to each note. Use when the user asks for a cut, a render, a new version, or says they've left notes.
---

Work out the project (ask if there are several and it's unclear) and whether this is a first cut or a revision:
a first cut if `projects/<id>/edit/renders/` has no renders, otherwise a revision.

**First cut:** follow "Phase 4: cutting" in CLAUDE.md. export_brief → inspect_regions → `edit/make_edl_v1.py` →
render → check the report → `edit/CUT_v1.md` → short summary to the user and the notes page link
`http://localhost:8770/p/<id>/notes/`.

**Revision:** follow "Phase 5: notes → next version". Read the open notes on the latest render (and the overall
note), map them to segments via `<render>.plan.json`, make `make_edl_vN+1.py` from the last one, render, write
`CUT_vN+1.md`, then reply to each note (`status`/`reply` only, after the user confirms the notes tab is closed) and
tell them to reload the notes page.

Either way:
- Never overwrite an earlier render or EDL.
- Long renders: run in the background and tell the user roughly how long.
- Say clearly what you couldn't judge without hearing it, so they know what to check.
- If the user asked for something new mid-way ("make it 1080p30", "add captions"), apply it and note it in CUT_vN.md.
