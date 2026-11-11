"""Reads and writes the review checklist. Everything posts automatically; a ticked
box STOPS that Short (it stays private).

Every Short has its own box, keyed by its YouTube id once uploaded, or by
`channel--slot` while it is still waiting to upload (it can be stopped early).
Two kinds of bulk box stop many at once and then clear themselves:
"Stop every Short in this week" and "Stop all of <day>".
"""
import os
import re
from pathlib import Path
from datetime import datetime

TICK = re.compile(r"- \[[xX]\] `([A-Za-z0-9_.:-]+)`")
ALL = re.compile(r"- \[[xX]\] \*\*Stop every Short in this week\*\*")
DAY = re.compile(r"- \[[xX]\] \*\*Stop all of (\d{4}-\d\d-\d\d)")


def key(e):
    return f"{e['slug']}--{e['stem']}"


def ticked(body, entries):
    """Keys and ids ticked (stopped) in this body, with bulk boxes expanded."""
    out = set(TICK.findall(body or ""))
    days = set(DAY.findall(body or ""))
    every = bool(ALL.search(body or ""))
    for e in entries:
        if every or e["publish_at"][:10] in days:
            out.add(key(e))
            if e.get("video_id"):
                out.add(e["video_id"])
    return out


_AUTO = {}


def auto(e):
    """Channels whose brand says auto_approve post without a checklist tick."""
    slug = e["slug"]
    if slug not in _AUTO:
        f = Path(__file__).resolve().parent.parent / "channels" / slug / "brand.yaml"
        _AUTO[slug] = f.exists() and "auto_approve: true" in f.read_text()
    return _AUTO[slug] or bool(e.get("auto_approve"))


def is_held(e, ticks):
    return key(e) in ticks or (e.get("video_id") or "") in ticks


def is_approved(e, ticks):
    return not is_held(e, ticks)


def review_body(entries, ticks):
    out = ["Everything here posts automatically at its slot (US Eastern time), scheduled on YouTube itself, "
           "with playlist and captions. **Tick a Short only to stop it**; it then stays private.",
           "Tap a title to watch it in YouTube Studio. ⏳ means made and uploading within a day.", "",
           "- [ ] **Stop every Short in this week**", ""]
    days = {}
    entries = [e for e in entries if e.get("status") != "expired" and not auto(e)]
    for e in sorted(entries, key=lambda x: x["publish_at"]):
        days.setdefault(e["publish_at"][:10], []).append(e)
    for day, items in days.items():
        name = datetime.fromisoformat(day).strftime("%A %d %B")
        out.append(f"### {name}")
        out.append(f"- [ ] **Stop all of {day}** ({name})")
        for e in items:
            t = e["publish_at"][11:16]
            box = "x" if is_held(e, ticks) else " "
            if e.get("video_id"):
                state = {"published": " (live)", "scheduled": " (scheduled)", "held": " (stopped)"}.get(e["status"], "")
                out.append(f"- [{box}] `{e['video_id']}` {t} · **{e['channel']}** · {e['series']}: "
                           f"[{e['title']}](https://studio.youtube.com/video/{e['video_id']}/edit){state}")
            elif e.get("platform") == "instagram":
                repo = os.environ.get("GITHUB_REPOSITORY", "archanacontent/channel-engine")
                ext = Path(e.get("file", "x.mp4")).suffix
                link = f"https://github.com/{repo}/releases/download/{e['release']}/{e['slug']}--{e['stem']}{ext}"
                state = " (posted)" if e["status"] == "published" else ""
                kind = "Reel" if ext == ".mp4" else "Image"
                out.append(f"- [{box}] `{key(e)}` {t} · **{e['channel']}** (Instagram {kind}): [{e['title']}]({link}){state}")
            else:
                out.append(f"- [{box}] `{key(e)}` ⏳ {t} · **{e['channel']}** · {e['series']}: {e['title']}")
        out.append("")
    return "\n".join(out)
