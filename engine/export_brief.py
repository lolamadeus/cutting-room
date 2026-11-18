"""Turn the review into an edit brief: the hand-off from reviewing to cutting.

    python engine/export_brief.py <project-id>

Writes projects/<id>/edit/:
  selects.json  ordered list of chosen segments (source file, in/out, tags, notes), in Board order
  brief.md      human-readable version: edit direction, then each section with its segments
"""
import json
import sys

from common import load_project, project_dir, write_json


def fmt(t):
    m = int(t // 60)
    return f"{m}:{t - m * 60:04.1f}"


def main():
    pid = sys.argv[1]
    cfg = load_project(pid)
    d = project_dir(pid)
    clips = json.loads((d / "_cache" / "clips.json").read_text())
    review = json.loads((d / "review.json").read_text()) if (d / "review.json").is_file() else {}
    recs = review.get("clips", {})
    tagsets = cfg["highlightTags"]
    bset = next((s for s in tagsets if s.get("board")), next((s for s in tagsets if s.get("mode") != "multi"), None))
    opt = {s["id"]: {o["id"]: o for o in s["options"]} for s in tagsets}
    groups_cfg = cfg["groups"]

    def group_of(c):
        return recs.get(c["id"], {}).get("group") or c["group"]

    ordered = sorted(clips, key=lambda c: ((groups_cfg.index(group_of(c)) if group_of(c) in groups_cfg else len(groups_cfg)), clips.index(c)))
    include = review.get("boardPrios") or ["must", "try", "space", "none"]
    pos = {hid: i for i, hid in enumerate(review.get("order", []))}

    items = []
    for c in ordered:
        r = recs.get(c["id"], {})
        prio = r.get("prio") or "none"
        if prio == "dont" or prio not in include:
            continue
        for x in r.get("hl", []):
            items.append((c, r, x))
    items.sort(key=lambda t: pos.get(t[2].get("id"), 1e9))

    bgroups = list(review.get("boardGroups") or [])
    for o in (bset["options"] if bset else []):
        if o["id"] not in bgroups:
            bgroups.append(o["id"])
    if "__none" not in bgroups:
        bgroups.append("__none")

    def cat(x):
        return (x.get("tags") or {}).get(bset["id"]) if bset else None

    selects, md = [], []
    total = 0.0
    md.append(f"# {cfg.get('title', pid)}: edit brief\n")
    if cfg.get("brief"):
        md.append(f"**Brief:** {cfg['brief']}\n")
    if cfg.get("target"):
        t = cfg["target"]
        md.append(f"**Target length:** {fmt(t['min'])}–{fmt(t.get('max', t['min']))}\n")
    if review.get("notes"):
        md.append("## Edit direction\n\n" + review["notes"].strip() + "\n")
    for g in bgroups:
        seg = [t for t in items if (cat(t[2]) or "__none") == g]
        if not seg:
            continue
        label = "No category" if g == "__none" else opt[bset["id"]][g]["label"]
        gdur = sum(x["e"] - x["s"] for _, _, x in seg)
        md.append(f"## {label} ({len(seg)} segment{'s' if len(seg) != 1 else ''}, {gdur:.1f}s)\n")
        for c, r, x in seg:
            tags = {}
            for s in tagsets:
                val = (x.get("tags") or {}).get(s["id"])
                ids = val if isinstance(val, list) else [val] if val else []
                labels = [opt[s["id"]][i]["label"] for i in ids if i in opt[s["id"]]]
                if labels:
                    tags[s["label"]] = labels
            dur = x["e"] - x["s"]
            total += dur
            selects.append({"n": len(selects) + 1, "section": label, "clip": c["id"], "src": c["src"],
                            "in": x["s"], "out": x["e"], "dur": round(dur, 2), "key": bool(x.get("key")),
                            "priority": r.get("prio"), "tags": tags, "note": x.get("note", ""),
                            "clipNotes": r.get("notes", "")})
            tag_txt = "; ".join(f"{k}: {', '.join(v)}" for k, v in tags.items() if k != (bset or {}).get("label"))
            line = f"{len(selects)}. {'★ ' if x.get('key') else ''}**{c['file']}** {fmt(x['s'])}–{fmt(x['e'])} ({dur:.1f}s)"
            if tag_txt:
                line += f" · {tag_txt}"
            if x.get("note"):
                line += f"\n   - {x['note']}"
            md.append(line)
        md.append("")
    md.insert(1, f"**Selected:** {len(selects)} segments, {fmt(total)} total\n")
    clip_notes = [(c, recs[c["id"]]["notes"]) for c in ordered if recs.get(c["id"], {}).get("notes")]
    if clip_notes:
        md.append("## Clip notes\n")
        md += [f"- **{c['file']}**: {n}" for c, n in clip_notes]

    out = d / "edit"
    write_json(out / "selects.json", {"project": pid, "total": round(total, 2), "segments": selects}, indent=1)
    (out / "brief.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(selects)} segments, {total:.1f}s -> {out}")


if __name__ == "__main__":
    main()
