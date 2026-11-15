"""Writes a new Comicsofy gag as a comic spec: a rotating cast, many places, never a repeated premise."""
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

from pipeline.write import generate
from strips.art import PROPS, ROOMS, SIZE, X
from strips.cast import ENSEMBLE, EXTRA_LOOKS, GUESTS, MOODS
from strips.sets import FX, SHOTS

ROOT = Path(__file__).resolve().parent.parent
DASHES = re.compile(r"[‒-―]")
RECENT = []   # specs written in this run, so a week's batch also rotates

CAST = "\n".join(f"- {v}" for v in ENSEMBLE.values())

SYSTEM = f"""You are the head writer of Comicsofy, an Instagram comic with a rotating ensemble. Your bar is the
funniest four-panel strips online: a gag people screenshot and send to the group chat. Specific, sharp,
quotable, a little savage, with heart underneath.

The ensemble (pick 2 or 3 per strip; Pim and Soot are rare guests):
{CAST}
You may add ONE one-off extra per strip (a barista, a landlord, a date, a doctor, a kid, a delivery driver, a gym
bro...). List it in "extras" with a short name (e.g. "Barista", "Landlord", "The Date") and the closest look.

Comedy rules:
- Brainstorm 8 premises across different worlds (office, dating, family, money, health, fitness, city life,
  roommates, holidays, the internet). Score each 1 to 10 for how hard it lands with adults, then write the best.
- Comic engines that work: a misdirect where the last line reframes everything; escalation to an absurd
  extreme; a character answering with brutal literal honesty; a dark twist (mortality, burnout, rent, bad
  dates) delivered casually; a wholesome reversal that still gets a real laugh.
- The punchline must be a turn, not a reaction. Banned endings: "Never!", "Typical.", "Classic X", "Nope",
  "Oh no", "Worth it", someone just sighing or agreeing, or a line that repeats the setup.
- Banned premise shape: "X tries to do Y and it goes wrong." Find an angle a stand-up comedian would use.
- Write in each character's voice. Real, specific details beat generic ones ("my 401k is a vibe" beats
  "I have no money"). Under 10 words per line. At most 2 lines per panel.
- Family friendly enough for Instagram: no slurs, no sex, no gore, no real people, brands, or other creators'
  characters. No em or en dashes.

Visual rules (variety is mandatory):
- Each panel picks a "shot": wide, medium, close or extreme_close. Use at least 3 different shots in a strip.
  Use close or extreme_close on reactions and the punchline.
- You can change "room" between panels (a cut to a new place or a "Later" narration box). Use at least 2
  different rooms or a cut, unless one place is the joke.
- "fx" (optional list) adds drama: speed_lines (shock), impact (a big reveal), spotlight (a dramatic
  confession), gloom (despair), sparkles (fake glamour or joy), hearts, flashback.
- "sfx" (optional) is a short sound word drawn big, like SLAM, DING, CRUNCH, BZZT.
- "narration" (optional) is a caption box: "Meanwhile", "3 hours later", "Day 47 of my 5am routine".
- A line can have "style": shout (big jagged bubble) or thought (cloud bubble). Silent panels are allowed.
- Moods carry the acting. Give characters the mood the moment needs, and vary it between panels.
- Only the listed rooms, props, moods, positions and sizes can be drawn. Never rely on an action the art cannot
  show; the dialogue, moods, shots and fx carry the comedy. Characters in one panel need different positions.
- "caption": one or two short, funny lines for Instagram, no hashtags.
- "hashtags": 5 hashtags for this gag's audience, each starting with #.
Return JSON only."""


def schema(n_panels):
    S, A = {"type": "STRING"}, lambda t, **k: {"type": "ARRAY", "items": t, **k}
    E = lambda vals: {"type": "STRING", "enum": list(vals)}
    member = {"type": "OBJECT", "properties": {
        "who": S, "mood": E(MOODS), "pos": E(list(X)), "size": E(list(SIZE)),
        "flip": {"type": "BOOLEAN"}, "holding": E(PROPS)}, "required": ["who", "mood", "pos", "size"]}
    line = {"type": "OBJECT", "properties": {"who": S, "text": S, "style": E(["normal", "shout", "thought"])},
            "required": ["who", "text"]}
    prop = {"type": "OBJECT", "properties": {"name": E(PROPS), "spot": E(["left", "center", "right"])}, "required": ["name", "spot"]}
    panel = {"type": "OBJECT", "properties": {
        "room": E(list(ROOMS)), "shot": E(list(SHOTS)), "focus": S, "fx": A(E(FX)), "sfx": S, "narration": S,
        "props": A(prop), "cast": A(member, minItems=1), "lines": A(line)},
        "required": ["room", "shot", "cast", "lines"]}
    extra = {"type": "OBJECT", "properties": {"name": S, "look": E(list(EXTRA_LOOKS)), "who_they_are": S},
             "required": ["name", "look"]}
    cand = {"type": "OBJECT", "properties": {"premise": S, "score": {"type": "INTEGER"}}, "required": ["premise", "score"]}
    return {"type": "OBJECT", "properties": {
        "candidates": A(cand), "title": S, "premise": S, "why_its_funny": S, "extras": A(extra), "caption": S,
        "hashtags": A(S), "panels": A(panel, minItems=n_panels[0], maxItems=n_panels[1])},
        "required": ["candidates", "title", "premise", "why_its_funny", "caption", "hashtags", "panels"]}


def history(slug):
    """Earlier specs, oldest first: premises to avoid, and the casts and rooms to rotate away from."""
    out = []
    for f in sorted((ROOT / "channels" / slug / "episodes").glob("*.yaml"))[-120:]:
        try:
            out.append(yaml.safe_load(f.read_text()) or {})
        except Exception:
            pass
    return out + RECENT


def used_premises(slug):
    return [p for p in ((ep.get("premise") or ep.get("title")) for ep in history(slug)) if p]


def cast_of(ep):
    return {c["who"] for p in ep.get("panels") or [] for c in p.get("cast", [])}


def main_room(ep):
    rooms = [p.get("room") for p in ep.get("panels") or []]
    return Counter(rooms).most_common(1)[0][0] if rooms else None


def check(spec, n_panels, recent=()):
    errs = []
    ps = spec.get("panels") or []
    extras = {e["name"] for e in spec.get("extras") or []}
    allowed = set(ENSEMBLE) | extras
    if len(extras) > 1:
        errs.append("Use at most one extra.")
    if not n_panels[0] <= len(ps) <= n_panels[1]:
        errs.append(f"Need {n_panels[0]} to {n_panels[1]} panels, got {len(ps)}.")
    for i, p in enumerate(ps):
        names = [c["who"] for c in p.get("cast", [])]
        for n in names:
            if n not in allowed:
                errs.append(f"Panel {i + 1}: {n} is not in the ensemble or extras.")
        if len(set(names)) != len(names):
            errs.append(f"Panel {i + 1} lists a character twice.")
        if len(names) > 3:
            errs.append(f"Panel {i + 1} has more than 3 characters.")
        pos = [c.get("pos") for c in p.get("cast", [])]
        if len(set(pos)) != len(pos):
            errs.append(f"Panel {i + 1} puts two characters in the same position.")
        if len(p.get("lines", [])) > 2:
            errs.append(f"Panel {i + 1} has more than 2 lines.")
        for ln in p.get("lines", []):
            if ln["who"] not in names:
                errs.append(f"Panel {i + 1}: {ln['who']} speaks but is not in the panel.")
            if len(ln["text"].split()) > 12:
                errs.append(f"Panel {i + 1}: a line is longer than 10 words.")
        if p.get("sfx") and len(p["sfx"]) > 10:
            errs.append(f"Panel {i + 1}: sfx must be one short sound word.")
        if p.get("narration") and len(p["narration"].split()) > 7:
            errs.append(f"Panel {i + 1}: narration must be at most 7 words.")
    if not any(p.get("lines") for p in ps):
        errs.append("Nobody speaks.")
    shots = {p.get("shot", "wide") for p in ps}
    if len(ps) >= 4 and len(shots) < 3:
        errs.append("Use at least 3 different shots (wide, medium, close, extreme_close).")
    if len({p.get("room") for p in ps}) < 2 and len(shots) < 3:
        errs.append("Every panel is the same room and framing; cut to a new room or change the shots.")
    cast = cast_of(spec)
    regulars = cast & (set(ENSEMBLE) - GUESTS)
    if cast & GUESTS and any(cast_of(ep) & GUESTS for ep in recent[-4:]):
        errs.append("Pim and Soot appeared in the last 4 strips; leave them out this time.")
    if not regulars and not (cast & GUESTS):
        errs.append("Use at least one ensemble character.")
    for ep in recent[-2:]:
        if len(regulars) >= 2 and regulars <= cast_of(ep):
            errs.append(f"{' and '.join(sorted(regulars))} were the cast very recently; pair different characters.")
            break
    last_rooms = [main_room(ep) for ep in recent[-3:]]
    if main_room(spec) in last_rooms:
        errs.append(f"{main_room(spec)} was a main setting in the last 3 strips; set it somewhere else.")
    return errs


def brief(recent):
    """What the last few strips used, so the writer rotates."""
    seen = Counter(n for ep in recent[-8:] for n in cast_of(ep))
    fresh = [n for n in ENSEMBLE if n not in GUESTS and seen[n] == 0] or \
            sorted((n for n in ENSEMBLE if n not in GUESTS), key=lambda n: seen[n])[:3]
    rooms = [main_room(ep) for ep in recent[-6:] if main_room(ep)]
    return (f"Characters used least lately, favour them: {', '.join(fresh)}.\n"
            f"Settings used lately, avoid as the main setting: {', '.join(dict.fromkeys(rooms)) or 'none'}.")


def instagram_caption(brand, text, gag_tags=()):
    """Caption, dotted spacer, then the account's hashtag block. Instagram allows 30 hashtags."""
    tail = brand.get("caption_tail") or []
    lines, used = [], 0
    for row in tail:
        if row and not str(row[0]).startswith("#"):
            lines.append(" | ".join(row))
        else:
            lines.append(" ".join(row))
            used += len(row)
    have = set(" ".join(lines).lower().split())
    extra = []
    for h in list(brand.get("hashtags", [])) + list(gag_tags):
        if h.lower() not in have:
            have.add(h.lower())
            extra.append(h)
    extra = extra[:max(0, 30 - used)]
    if extra:
        lines[-1] = (lines[-1] + " " + " ".join(extra)).strip()
    return text.strip() + "\n.\n.\n.\n" + "\n".join(lines)


def write_strip(brand, rec):
    kind = rec.get("kind", "image")
    n_panels = (4, 4) if kind == "image" else (3, 5)
    recent = history(brand["slug"])
    used = used_premises(brand["slug"]) + list(rec.get("avoid", []))
    user = (f"Today is {date.today():%A %d %B %Y}. Write today's "
            f"{'four-panel comic' if kind == 'image' else 'animated Reel episode (3 to 5 panels, it plays with voices)'}.\n"
            f"{brief(recent)}\n"
            f"Already used premises (do not repeat or echo):\n- " + "\n- ".join(used[-80:] or ["none yet"]))
    errs = []
    for attempt in range(4):
        prompt = user + ("\n\nYour last answer had these problems, fix them:\n- " + "\n- ".join(errs) if errs else "")
        spec = generate(SYSTEM, prompt, schema(n_panels))
        errs = check(spec, n_panels, recent)
        if not errs:
            break
        print(f"  strip check failed ({rec['id']}):", "; ".join(errs[:4]), flush=True)
    if errs:
        return None, "; ".join(errs[:4])
    for p in spec["panels"]:
        p.setdefault("props", [])
        for k in ("sfx", "narration", "focus"):
            if not p.get(k):
                p.pop(k, None)
        if not p.get("fx"):
            p.pop("fx", None)
        for ln in p["lines"]:
            ln["text"] = DASHES.sub(", ", ln["text"]).strip()
            if ln.get("style") in (None, "", "normal"):
                ln.pop("style", None)
        if p.get("narration"):
            p["narration"] = DASHES.sub(", ", p["narration"]).strip()
    tags = [h if h.startswith("#") else "#" + h for h in spec.get("hashtags", [])][:5]
    caption = DASHES.sub(", ", spec["caption"]).strip()
    ep = {
        "format": "strip", "kind": kind, "title": spec["title"], "premise": spec["premise"],
        "extras": [{"name": e["name"], "look": e["look"]} for e in spec.get("extras") or []],
        "panels": spec["panels"],
        "caption": instagram_caption(brand, caption, tags),
        "description": {"summary": caption},
    }
    if not ep["extras"]:
        ep.pop("extras")
    RECENT.append(ep)
    return ep, None
