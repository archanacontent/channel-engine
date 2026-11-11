"""Turns a public domain comic page into a motion-comic episode.

A vision model finds the panels, reads the lettering, names each speaker and
writes a short narrator hook and closing line. The dialogue is the original
1900s text; only the hook and closer are new.
"""
import base64
import io
import json
import re
import urllib.request
from pathlib import Path

from PIL import Image

from pipeline.write import QuotaSpent, generate

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "comics"
VOICES = ["narrator", "boy", "girl", "man", "woman", "old_man", "creature"]
DASHES = re.compile(r"[‒-―]")

SYSTEM = """You voice-direct a channel that turns public domain newspaper comics from the 1900s into
motion comics. You get one scanned comic page.

1. Find every panel in reading order (top row left to right, then the next row). Give each panel
   box_2d as [ymin, xmin, ymax, xmax] on a 0-1000 scale, tight to the panel's border. Ignore the
   title banner, signature and newspaper margins.
2. For each panel, transcribe its lettering: speech, thought and caption text, exactly as printed,
   keeping old spelling and dialect, but written in normal sentence case (the lettering is in
   capitals; write "Be careful you don't tip over." not "BE CAREFUL YOU DON'T TIP OVER"), with
   names capitalised and end punctuation added. Fix only line-break hyphens. If a panel has no text, give it
   no lines. Give each line a speaker (the character's name if the page shows it, else a short
   description like "Mother" or "Policeman"; captions use "Narrator") and a voice from:
   narrator, boy, girl, man, woman, old_man, creature.
3. If the dialogue on the page totals more than 200 words, shorten long lines by cutting words
   only, never adding or rewording, until it is under 200, and set "abridged" true.
4. Write "hook": one line, at most 14 words, spoken by our narrator over the first panel. It sets
   up the comedy of what is on this page without giving away the ending. Present tense. Funny,
   warm, modern, never mean.
5. Write "closer": one line, at most 16 words, reacting to how this page actually ends, then
   nothing else. No calls to action.
6. Write "title": at most 60 characters, a funny hook about this page's events. No hashtags.
7. Write "summary": two plain sentences on what happens on this page. Only what the page shows.
8. Set "skip" true, with "skip_reason", if the page contains a racial or ethnic caricature or a
   slur, if the lettering is mostly unreadable, or if it is not a comic page.

Never invent events, characters or dialogue that are not on the page. Never use em or en dashes.
Return JSON only."""


def schema():
    S, A = {"type": "STRING"}, lambda t: {"type": "ARRAY", "items": t}
    line = {"type": "OBJECT", "properties": {"speaker": S, "voice": {"type": "STRING", "enum": VOICES}, "text": S},
            "required": ["speaker", "voice", "text"]}
    panel = {"type": "OBJECT", "properties": {"box_2d": A({"type": "INTEGER"}), "lines": A(line)},
             "required": ["box_2d", "lines"]}
    return {"type": "OBJECT", "properties": {
        "skip": {"type": "BOOLEAN"}, "skip_reason": S, "title": S, "hook": S, "closer": S, "summary": S,
        "abridged": {"type": "BOOLEAN"}, "panels": A(panel), "hashtags": A(S)},
        "required": ["skip", "title", "hook", "closer", "summary", "panels"]}


def fetch_image(rec):
    CACHE.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", rec["id"].split(":", 1)[1])
    path = CACHE / (Path(name).stem + ".jpg")
    if not path.exists():
        req = urllib.request.Request(rec["image_url"], headers={"User-Agent": "ChannelEngine/1.0 (creativecontent707@gmail.com)"})
        img = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=120).read())).convert("RGB")
        img.save(path, quality=92)
    return path


NAMES = {"nemo", "flip", "morpheus", "slumberland", "somnus", "oomp", "sammy", "moontown", "pill", "princess",
         "silas", "papa", "mama", "god"}


def sentence_case(text, names=()):
    """Turns all-capitals lettering into sentence case, keeping names capitalised."""
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(c.isupper() for c in letters) / len(letters) < 0.6:
        return text
    keep = NAMES | {n.lower() for n in names}
    out = re.sub(r"[A-Za-z']+", lambda m: m[0].capitalize() if m[0].lower().strip("'") in keep else m[0].lower(), text)
    out = re.sub(r"(^|[.!?]\s+|(?:^|\s)['\"])([a-z])", lambda m: m[1] + m[2].upper(), out)
    out = re.sub(r"\bi\b", "I", out)
    out = re.sub(r"\bi'", "I'", out)
    return out


def check(ep):
    errs = []
    panels = ep.get("panels") or []
    if not 2 <= len(panels) <= 16:
        errs.append(f"Found {len(panels)} panels; a comic page has 2 to 16.")
    for i, p in enumerate(panels):
        b = p.get("box_2d") or []
        if len(b) != 4 or not (0 <= b[0] < b[2] <= 1000 and 0 <= b[1] < b[3] <= 1000):
            errs.append(f"Panel {i + 1} box_2d must be [ymin, xmin, ymax, xmax] within 0-1000.")
        elif (b[2] - b[0]) * (b[3] - b[1]) < 4000:
            errs.append(f"Panel {i + 1} box is too small to be a panel.")
    words = sum(len(l.get("text", "").split()) for p in panels for l in p.get("lines") or [])
    if words == 0:
        errs.append("No lettering transcribed.")
    if words > 240:
        errs.append(f"Dialogue totals {words} words; abridge to under 200 by cutting words from long lines.")
    for k, n in (("hook", 14), ("closer", 16)):
        if not ep.get(k) or len(ep[k].split()) > n + 3:
            errs.append(f"{k} must be one line of at most {n} words.")
    if not ep.get("title") or len(ep["title"]) > 70:
        errs.append("title must be at most 60 characters.")
    return errs


def write_comic(brand, rec):
    path = fetch_image(rec)
    img = Image.open(path)
    small = img.copy()
    small.thumbnail((1600, 1600))
    buf = io.BytesIO()
    small.save(buf, "JPEG", quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode()
    user = (f"This is {rec['comic_name']} by {rec['creator']}, published {rec['date']}. "
            f"Our channel: {brand['name']}.")
    errs = []
    for attempt in range(3):
        prompt = user + ("\n\nYour last answer had these problems, fix them:\n- " + "\n- ".join(errs) if errs else "")
        ep = generate(SYSTEM, prompt, schema(), image=b64)
        if ep.get("skip"):
            return None, f"skipped: {ep.get('skip_reason', 'no reason')}"
        errs = check(ep)
        if not errs:
            break
        print(f"  comic check failed ({rec['id']}):", "; ".join(errs[:4]), flush=True)
    if errs:
        return None, "; ".join(errs[:4])
    for k in ("title", "hook", "closer", "summary"):
        ep[k] = DASHES.sub(", ", ep[k]).strip()
    speakers = {w for p in ep["panels"] for l in p["lines"] for w in l["speaker"].split()}
    for p in ep["panels"]:
        for l in p["lines"]:
            l["text"] = sentence_case(DASHES.sub(", ", l["text"]), speakers)
            l["speaker"] = l["speaker"].title() if l["speaker"].isupper() else l["speaker"]
    year = rec["date"][:4]
    out = {
        "format": "comic",
        "title": f"{ep['title']} | {rec['comic_name']} ({year})",
        "comic": rec["comic_name"], "date": rec["date"], "creator": rec["creator"],
        "hook": ep["hook"], "closer": ep["closer"], "abridged": bool(ep.get("abridged")),
        "panels": [{"box": p["box_2d"], "lines": [{k: l[k] for k in ("speaker", "voice", "text")} for l in p["lines"]]}
                   for p in ep["panels"]],
        "media": {"image": str(path.resolve()), "credit": rec["credit"]},
        "description": {
            "summary": ep["summary"],
            "credit": rec["credit"],
            "abridged_note": "Dialogue lightly abridged for length." if ep.get("abridged") else "",
            "sources": rec["sources"],
        },
        "seo": {"seeds": [rec["comic_name"], rec["creator"], "classic comics", "motion comic"],
                "hashtags": [h if h.startswith("#") else "#" + h for h in (ep.get("hashtags") or [])][:3]},
    }
    return out, None
