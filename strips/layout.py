"""Turns a comic spec into an HTML page of panels with automatic speech bubbles.

spec = {"panels": [{"room": "dining_room",
                    "props": [{"name": "turkey", "spot": "left"}],
                    "cast": [{"who": "Pim", "mood": "excited", "pos": "right", "size": "medium", "flip": false}],
                    "lines": [{"who": "Pim", "text": "..."}]}]}
"""
import html
import json

from strips.art import CHARACTERS, FLOOR, FRONT, INK, PH, PW, ROOMS, SIZE, SURFACE, X, prop_svg
from strips.cast import extra_drawer
from strips.sets import PROPS as MORE_PROPS, SHOTS, fx_back, fx_front, sfx

PROP_REST = {"turkey": (52, 0.95), "pie": (70, 0.75), "mug": (46, 0.6), "laptop": (34, 0.7), "phone": (64, 0.55),
             "book": (40, 0.7), "pumpkin": (70, 0.8), "gift": (50, 0.75), "plant": (90, 0.75), "pizza": (40, 0.7),
             "candle": (50, 0.7), "umbrella": (130, 0.75), "snowman": (110, 0.9), "tv": (90, 0.75), "sheet": (70, 0.7),
             "sock": (60, 0.6), **{k: (v[1], v[2]) for k, v in MORE_PROPS.items()}}
PROP_X = {"left": 130, "center": 256, "right": 382, "far_left": 90, "far_right": 422}


def who_info(who, extras):
    """Drawing info for a cast member: a named character, or a one-off extra described in spec["extras"]."""
    if who in CHARACTERS:
        return CHARACTERS[who]
    look = (extras.get(who) or {}).get("look", "young_man")
    return {"draw": extra_drawer(look), "head": -158, "float": 0, "base": 124, "behind": 34,
            "scale": 0.72 if look == "kid" else 0.88 if look == "teen" else 0.92 if look == "old_man" else 1.0}


def place(c, room, extras=None):
    info = who_info(c["who"], extras or {})
    s = SIZE.get(c.get("size", "medium"), 0.95) * info.get("scale", 1.0)
    x = X.get(c.get("pos", "center"), 256)
    floor = FLOOR[room]
    if room in SURFACE:  # behind a table: hide only the bottom of the body
        y = SURFACE[room] - info.get("behind", 94) * s
    elif c["who"] == "Pim":
        y = floor - 124 * s - 26
    else:
        y = floor - 124 * s + 8
    return x, y, s, (x, y + info["head"] * s)


def spread(cast):
    """Characters in one panel stand apart so they never overlap."""
    if len(cast) == 2:
        order = sorted(range(2), key=lambda j: X.get(cast[j].get("pos", "center"), 256))
        cast[order[0]]["pos"], cast[order[1]]["pos"] = "left", "right"
    elif len(cast) >= 3:
        order = sorted(range(len(cast)), key=lambda j: X.get(cast[j].get("pos", "center"), 256))
        for slot, j in zip(("far_left", "center", "far_right"), order):
            cast[j]["pos"] = slot
            if cast[j].get("size") != "small":
                cast[j]["size"] = "small" if len(cast) > 2 else cast[j].get("size")
    if len(cast) >= 2:
        for c in cast:
            if c.get("size") == "large":
                c["size"] = "medium"
    return cast


def camera(p, heads, spec_cast):
    """Zoom and offset for the panel's shot: (k, tx, ty). Wide shots are (1, 0, 0)."""
    k = SHOTS.get(p.get("shot", "wide"), 1.0)
    if k == 1.0 or not heads:
        return 1.0, 0.0, 0.0
    focus = p.get("focus")
    if focus not in heads:
        focus = next((ln["who"] for ln in p.get("lines", []) if ln["who"] in heads), None) or next(iter(heads))
    if p.get("shot") == "medium" and len(heads) > 1:
        fx = sum(h[0] for h in heads.values()) / len(heads)
        fy = min(h[1] for h in heads.values()) + 70
    else:
        fx, fy = heads[focus][0], heads[focus][1] + 62
    tgt_y = {"medium": 380, "close": 410, "extreme_close": 440}[p["shot"]]
    tx, ty = 256 - k * fx, tgt_y - k * fy
    tx = min(0.0, max(PW - k * PW, tx))
    ty = min(0.0, max(PH - k * PH, ty))
    return k, tx, ty


def panel_html(i, p, extras=None):
    extras = extras or {}
    room = p["room"]
    spread(p.get("cast", []))
    fxs = p.get("fx") or []
    fxs = [fxs] if isinstance(fxs, str) else fxs
    bg = ROOMS[room]() + "".join(fx_back(f) for f in fxs)
    chars = []
    floor = FLOOR[room]
    heads = {}
    for j, c in enumerate(p.get("cast", [])):
        x, y, s, head = place(c, room, extras)
        heads.setdefault(c["who"], head)
        info = who_info(c["who"], extras)
        draw = info["draw"]
        for talk in (False, True):
            chars.append(f'<g class="layer char c{j}{" talk" if talk else " quiet"}" data-who="{html.escape(c["who"])}">'
                         f'{draw(x, y, s, c.get("mood", "neutral"), c.get("flip", False), talking=talk, prop=c.get("holding"))}</g>')
    front = [FRONT[room]()] if room in FRONT else []
    line = SURFACE.get(room, floor)
    taken = {X.get(c.get("pos", "center"), 256) for c in p.get("cast", [])}
    for pr in p.get("props", []):
        rest, sc = PROP_REST[pr["name"]]
        x = PROP_X.get(pr.get("spot", "left"), 130)
        if room not in SURFACE and any(abs(x - t) < 110 for t in taken):   # never stand a prop in front of someone
            free = [v for v in PROP_X.values() if all(abs(v - t) >= 110 for t in taken)]
            x = min(free, key=lambda v: abs(v - x)) if free else x
        taken.add(x)
        front.append(prop_svg(pr["name"], x, line + (34 if room in SURFACE else 10) - rest * sc, sc))
    front += [fx_front(f) for f in fxs]
    k, tx, ty = camera(p, heads, p.get("cast", []))
    cam = f'<g transform="translate({tx:.1f},{ty:.1f}) scale({k})">'
    art = [f'<g class="layer bg">{cam}{bg}</g></g>', *[f"{cam}{c}</g>" for c in chars],
           f'<g class="layer fg">{cam}{"".join(front)}</g>{sfx(p["sfx"], p.get("sfx_spot", "right")) if p.get("sfx") else ""}</g>']
    heads = {w: (k * h[0] + tx, k * h[1] + ty) for w, h in heads.items()}
    bubbles = []
    lines = p.get("lines", [])
    for kk, ln in enumerate(lines):
        hx, hy = heads.get(ln["who"], (256, 300))
        words = len(ln["text"].split())
        fs = 38 if words <= 8 else 34 if words <= 14 else 30
        shout = " shout" if ln.get("style") == "shout" else " think" if ln.get("style") == "thought" else ""
        bubbles.append(f'<div class="b layer bub{kk}{shout}" data-hx="{hx:.1f}" data-hy="{hy:.1f}" style="font-size:{fs + (6 if shout == " shout" else 0)}px">'
                       f'{html.escape(ln["text"])}</div>')
    nar = (f'<div class="nar layer narr">{html.escape(p["narration"])}</div>' if p.get("narration") else "")
    return (f'<div class="p" id="p{i}"><svg class="art" viewBox="0 0 {PW} {PH}" width="{PW}" height="{PH}">{"".join(art)}</svg>'
            f'<svg class="tails" viewBox="0 0 {PW} {PH}" width="{PW}" height="{PH}"></svg>{nar}{"".join(bubbles)}</div>')


SCRIPT = """
function layout() {
  for (const p of document.querySelectorAll('.p')) {
    const tails = p.querySelector('.tails'); tails.innerHTML = '';
    const nar = p.querySelector('.nar'); let top = nar ? nar.offsetHeight + 34 : 22;
    const bs = [...p.querySelectorAll('.b')];
    bs.forEach((b, k) => {
      const hx = +b.dataset.hx, hy = +b.dataset.hy;
      const w = b.offsetWidth, h = b.offsetHeight;
      let left = Math.min(Math.max(hx - w / 2, 14), PW - w - 14);
      if (bs.length > 1) left = Math.min(Math.max(hx - w / 2 + (k % 2 ? 30 : -30), 14), PW - w - 14);
      top = Math.max(top, Math.min(hy - 60 - h, PH * 0.42 - h));   // sit close above the speaker
      b.style.left = left + 'px'; b.style.top = top + 'px';
      const bx = Math.min(Math.max(hx, left + 40), left + w - 40), by = top + h - 8;
      const ty = Math.max(by + 20, Math.min(hy - 10, by + 70));
      const tx = hx + (bx - hx) * 0.15;
      const ns = 'http://www.w3.org/2000/svg';
      const t = document.createElementNS(ns, b.classList.contains('think') ? 'g' : 'path');
      if (b.classList.contains('think')) {
        [[0.35, 11], [0.7, 7]].forEach(([f, r]) => { const c = document.createElementNS(ns, 'circle');
          c.setAttribute('cx', bx + (tx - bx) * f); c.setAttribute('cy', by + 8 + (ty - by) * f); c.setAttribute('r', r);
          c.setAttribute('fill', '#fff'); c.setAttribute('stroke', INK); c.setAttribute('stroke-width', '4'); t.appendChild(c); });
      } else t.setAttribute('d', `M${bx - 22},${by} L${tx},${ty} L${bx + 22},${by} Z`);
      t.setAttribute('fill', '#fff'); t.setAttribute('stroke', INK); t.setAttribute('stroke-width', '5');
      t.setAttribute('stroke-linejoin', 'round'); t.setAttribute('class', 'layer bub' + k);
      tails.appendChild(t);
      top += h + 14;
    });
  }
}
function only(sel) {  // show just the matching layers (for Reel compositing)
  document.querySelectorAll('.layer').forEach(e => e.style.visibility = e.matches(sel) ? 'visible' : 'hidden');
  document.body.style.background = 'transparent'; document.documentElement.style.background = 'transparent';
  document.querySelectorAll('.p, .sheet').forEach(e => { e.style.background = 'transparent'; e.style.outlineColor = 'transparent'; });
}
function still() { document.querySelectorAll('.talk').forEach(e => e.style.display = 'none'); }
"""


def page(spec, font_url, sig="@comicsofy", single=False):
    M, G = 20, 16
    ex = {e["name"]: e for e in spec.get("extras") or []}
    panels = [panel_html(i, p, ex) for i, p in enumerate(spec["panels"])]
    cols = 1 if single else 2
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: Hand; src: url("{font_url}"); }}
html, body {{ margin: 0; background: #fffdf7; }}
.sheet {{ display: inline-block; background: #fffdf7; padding: {0 if single else M}px {0 if single else M}px 0; }}
.grid {{ display: grid; grid-template-columns: repeat({cols}, {PW}px); gap: {G}px; }}
.p {{ position: relative; width: {PW}px; height: {PH}px; overflow: hidden; outline: 6px solid {INK}; outline-offset: -3px; background: #fff; }}
.p svg {{ position: absolute; left: 0; top: 0; display: block; }}
.b {{ position: absolute; max-width: 400px; min-width: 120px; width: max-content; background: #fff; border: 5px solid {INK};
      border-radius: 44px; padding: 18px 26px; box-sizing: border-box; text-align: center; font-family: Hand;
      line-height: 1.08; color: {INK}; text-transform: uppercase; letter-spacing: 0.5px; }}
.b.shout {{ border-radius: 14px; border-width: 7px; background: #fff7c2; transform: rotate(-2deg); font-weight: bold; }}
.b.think {{ border-radius: 60px; border-style: dashed; }}
.nar {{ position: absolute; left: 14px; top: 14px; max-width: 360px; background: #ffd166; border: 5px solid {INK};
        padding: 8px 16px; font-family: Hand; font-size: 30px; color: {INK}; text-transform: uppercase; box-shadow: 5px 5px 0 {INK}; }}
.sig {{ font-family: Hand; font-size: 30px; color: #8a7f9c; text-align: right; padding: 6px 4px 10px 0; }}
</style></head><body><div class="sheet"><div class="grid">{"".join(panels)}</div>
{"" if single else f'<div class="sig">{sig}</div>'}</div>
<script>const PW={PW}, PH={PH}, INK="{INK}";{SCRIPT}document.fonts.ready.then(() => {{ layout(); document.body.dataset.ready = 1; }});</script></body></html>'''
