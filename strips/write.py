"""Writes a new Pim and Soot gag as a comic spec, never repeating an earlier premise."""
import json
import re
from datetime import date
from pathlib import Path

import yaml

from pipeline.write import generate
from strips.art import CAT_MOODS, GHOST_MOODS, PROPS, ROOMS, SIZE, X

ROOT = Path(__file__).resolve().parent.parent
DASHES = re.compile(r"[‒-―]")

CAST = """Pim: a small, timid, endlessly optimistic ghost. Tries very hard, overthinks, gets excited, is bad at being
scary, loves cozy things, wants to belong. Speaks in short, eager, sometimes nervous lines.
Soot: Pim's deadpan black cat. Unbothered, dry, sarcastic but secretly fond of Pim. Says very little. Often gets
the punchline with two or three words, or a look."""

SYSTEM = f"""You write a daily webcomic called Pim & Soot for Instagram. Original, warm, genuinely funny gags with
a clean setup and a sharp punchline, in the spirit of the best four-panel webcomics.

The cast:
{CAST}

Rules:
- First brainstorm 5 different premises, then choose the funniest one. Premises must be new: never reuse or
  closely echo a premise from the "already used" list.
- Ground it in everyday life people relate to (home, food, weather, work-from-home, sleep, chores, holidays,
  friendships, small social awkwardness), seen through a ghost and a cat. Seasonal or holiday hooks are welcome
  when today's date makes them timely.
- The last panel lands the punchline. Earlier panels build to it. A silent panel (no lines) is allowed for timing.
- At most 2 lines per panel, each at most 10 words, plain spoken English. Only characters in a panel's cast may
  speak in that panel.
- Family friendly. No real people, brands, or other creators' characters. No em or en dashes.
- The art can show only the listed rooms, props, moods, positions and sizes, so the joke must work with what
  can be drawn: the dialogue and the characters' moods carry the comedy. Never rely on an action or object the
  art cannot show (no "look at this tangled sheet" unless the panel can simply show Pim holding a sheet).
- Use only the rooms, props, moods, positions and sizes listed in the schema. When both characters share a
  panel, give them different positions.
- "caption": one or two short, funny lines for the Instagram caption, no hashtags.
- "hashtags": 5 hashtags relevant to this gag (webcomic audience), each starting with #.
Return JSON only."""


def schema(n_panels):
    S, A = {"type": "STRING"}, lambda t, **k: {"type": "ARRAY", "items": t, **k}
    E = lambda vals: {"type": "STRING", "enum": list(vals)}
    who = E(["Pim", "Soot"])
    member = {"type": "OBJECT", "properties": {
        "who": who, "mood": E(sorted(set(GHOST_MOODS + CAT_MOODS))), "pos": E(list(X)), "size": E(list(SIZE)),
        "flip": {"type": "BOOLEAN"}, "holding": E(PROPS)}, "required": ["who", "mood", "pos", "size"]}
    line = {"type": "OBJECT", "properties": {"who": who, "text": S}, "required": ["who", "text"]}
    prop = {"type": "OBJECT", "properties": {"name": E(PROPS), "spot": E(["left", "center", "right"])}, "required": ["name", "spot"]}
    panel = {"type": "OBJECT", "properties": {"room": E(list(ROOMS)), "props": A(prop), "cast": A(member, minItems=1),
                                              "lines": A(line)}, "required": ["room", "cast", "lines"]}
    return {"type": "OBJECT", "properties": {
        "candidates": A(S), "title": S, "premise": S, "caption": S, "hashtags": A(S),
        "panels": A(panel, minItems=n_panels[0], maxItems=n_panels[1])},
        "required": ["candidates", "title", "premise", "caption", "hashtags", "panels"]}


def used_premises(slug):
    out = []
    for f in sorted((ROOT / "channels" / slug / "episodes").glob("*.yaml"))[-120:]:
        try:
            ep = yaml.safe_load(f.read_text())
            out.append(ep.get("premise") or ep.get("title"))
        except Exception:
            pass
    return [p for p in out if p]


def check(spec, n_panels):
    errs = []
    ps = spec.get("panels") or []
    if not n_panels[0] <= len(ps) <= n_panels[1]:
        errs.append(f"Need {n_panels[0]} to {n_panels[1]} panels, got {len(ps)}.")
    for i, p in enumerate(ps):
        names = [c["who"] for c in p.get("cast", [])]
        if len(set(names)) != len(names):
            errs.append(f"Panel {i + 1} lists a character twice.")
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
        for c in p.get("cast", []):
            ok = GHOST_MOODS if c["who"] == "Pim" else CAT_MOODS
            if c.get("mood") not in ok:
                errs.append(f"Panel {i + 1}: {c['who']} cannot have mood {c.get('mood')}; use one of {ok}.")
    if not any(p.get("lines") for p in ps):
        errs.append("Nobody speaks.")
    return errs


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
    n_panels = (4, 4) if kind == "image" else (3, 4)
    used = used_premises(brand["slug"]) + list(rec.get("avoid", []))
    user = (f"Today is {date.today():%A %d %B %Y}. Write today's {'four-panel comic' if kind == 'image' else 'short animated episode (3 or 4 panels)'}.\n"
            f"Already used premises (do not repeat or echo):\n- " + "\n- ".join(used[-80:] or ["none yet"]))
    errs = []
    for attempt in range(3):
        prompt = user + ("\n\nYour last answer had these problems, fix them:\n- " + "\n- ".join(errs) if errs else "")
        spec = generate(SYSTEM, prompt, schema(n_panels))
        errs = check(spec, n_panels)
        if not errs:
            break
        print(f"  strip check failed ({rec['id']}):", "; ".join(errs[:4]), flush=True)
    if errs:
        return None, "; ".join(errs[:4])
    for p in spec["panels"]:
        p.setdefault("props", [])
        for ln in p["lines"]:
            ln["text"] = DASHES.sub(", ", ln["text"]).strip()
    tags = [h if h.startswith("#") else "#" + h for h in spec.get("hashtags", [])][:5]
    caption = DASHES.sub(", ", spec["caption"]).strip()
    ep = {
        "format": "strip", "kind": kind, "title": spec["title"], "premise": spec["premise"],
        "panels": spec["panels"],
        "caption": instagram_caption(brand, caption, tags),
        "description": {"summary": caption},
    }
    return ep, None
