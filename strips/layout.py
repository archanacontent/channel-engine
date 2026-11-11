"""Turns a comic spec into an HTML page of panels with automatic speech bubbles.

spec = {"panels": [{"room": "dining_room",
                    "props": [{"name": "turkey", "spot": "left"}],
                    "cast": [{"who": "Pim", "mood": "excited", "pos": "right", "size": "medium", "flip": false}],
                    "lines": [{"who": "Pim", "text": "..."}]}]}
"""
import html
import json

from strips.art import CHARACTERS, FLOOR, FRONT, INK, PH, PW, ROOMS, SIZE, SURFACE, X, prop_svg

PROP_REST = {"turkey": (52, 0.95), "pie": (70, 0.75), "mug": (46, 0.6), "laptop": (34, 0.7), "phone": (64, 0.55),
             "book": (40, 0.7), "pumpkin": (70, 0.8), "gift": (50, 0.75), "plant": (90, 0.75), "pizza": (40, 0.7),
             "candle": (50, 0.7), "umbrella": (130, 0.75), "snowman": (110, 0.9), "tv": (90, 0.75), "sheet": (70, 0.7),
             "sock": (60, 0.6)}
PROP_X = {"left": 130, "center": 256, "right": 382, "far_left": 90, "far_right": 422}


def place(c, room):
    s = SIZE.get(c.get("size", "medium"), 0.95)
    x = X.get(c.get("pos", "center"), 256)
    floor = FLOOR[room]
    if room in SURFACE:  # behind a table: hide only the bottom of the body
        y = SURFACE[room] - (80 if c["who"] == "Pim" else 94) * s
    elif c["who"] == "Pim":
        y = floor - 124 * s - 26
    else:
        y = floor - 124 * s + 8
    head = (x, y + CHARACTERS[c["who"]]["head"] * s)
    return x, y, s, head


def spread(cast):
    """Two characters in one panel stand at the far sides so they never overlap."""
    if len(cast) == 2:
        order = sorted(range(2), key=lambda j: X.get(cast[j].get("pos", "center"), 256))
        cast[order[0]]["pos"], cast[order[1]]["pos"] = "left", "right"
        for c in cast:
            if c.get("size") == "large":
                c["size"] = "medium"
    return cast


def panel_html(i, p):
    room = p["room"]
    spread(p.get("cast", []))
    art = [f'<g class="layer bg">{ROOMS[room]()}</g>']
    floor = FLOOR[room]
    heads = {}
    for j, c in enumerate(p.get("cast", [])):
        x, y, s, head = place(c, room)
        heads.setdefault(c["who"], head)
        draw = CHARACTERS[c["who"]]["draw"]
        for talk in (False, True):
            art.append(f'<g class="layer char c{j}{" talk" if talk else " quiet"}" data-who="{c["who"]}">'
                       f'{draw(x, y, s, c.get("mood", "happy"), c.get("flip", False), talking=talk, prop=c.get("holding"))}</g>')
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
    art.append(f'<g class="layer fg">{"".join(front)}</g>')
    bubbles = []
    lines = p.get("lines", [])
    for k, ln in enumerate(lines):
        hx, hy = heads.get(ln["who"], (256, 300))
        words = len(ln["text"].split())
        fs = 38 if words <= 8 else 34 if words <= 14 else 30
        bubbles.append(f'<div class="b layer bub{k}" data-hx="{hx}" data-hy="{hy}" style="font-size:{fs}px">'
                       f'{html.escape(ln["text"])}</div>')
    return (f'<div class="p" id="p{i}"><svg class="art" viewBox="0 0 {PW} {PH}" width="{PW}" height="{PH}">{"".join(art)}</svg>'
            f'<svg class="tails" viewBox="0 0 {PW} {PH}" width="{PW}" height="{PH}"></svg>{"".join(bubbles)}</div>')


SCRIPT = """
function layout() {
  for (const p of document.querySelectorAll('.p')) {
    const tails = p.querySelector('.tails'); tails.innerHTML = '';
    let top = 22;
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
      const t = document.createElementNS(ns, 'path');
      t.setAttribute('d', `M${bx - 22},${by} L${tx},${ty} L${bx + 22},${by} Z`);
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
    panels = [panel_html(i, p) for i, p in enumerate(spec["panels"])]
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
.sig {{ font-family: Hand; font-size: 30px; color: #8a7f9c; text-align: right; padding: 6px 4px 10px 0; }}
</style></head><body><div class="sheet"><div class="grid">{"".join(panels)}</div>
{"" if single else f'<div class="sig">{sig}</div>'}</div>
<script>const PW={PW}, PH={PH}, INK="{INK}";{SCRIPT}document.fonts.ready.then(() => {{ layout(); document.body.dataset.ready = 1; }});</script></body></html>'''
