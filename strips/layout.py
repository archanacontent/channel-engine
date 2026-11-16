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


# Where the face sits on each kind of character, in its own units from the point it stands on:
# (centre y, half width, half height). Anything not listed has a person-shaped head.
FACE = {"Pim": (-30, 66, 62), "Soot": (-40, 62, 52), "Biscuit": (-55, 64, 56), "Gus": (-40, 50, 46),
        "Mort": (-80, 48, 50), "Fern": (83, 60, 42)}


def face_boxes(who, x, y, s, k=1.0, tx=0.0, ty=0.0):
    """(whole face, eyes and mouth) as rectangles; in scene units unless a camera is given."""
    cy, hw, hh = FACE.get(who, (-80, 72, 78))
    cx, cy = x, y + cy * s
    box = lambda w, h: [round(k * (cx - w * s) + tx, 1), round(k * (cy - h * s) + ty, 1),
                        round(k * (cx + w * s) + tx, 1), round(k * (cy + h * s) + ty, 1)]
    return box(hw, hh) + box(hw * 0.68, hh * 0.55)


def sfx_spot(text, faces, wanted):
    """The sound word goes where it covers the least face, and never eyes or mouth when there is a choice."""
    t = text.upper()[:12]
    fs = 92 if len(t) <= 5 else 70 if len(t) <= 8 else 54
    w, h = len(t) * fs * 0.62, fs
    pref = {"left": (120, 560), "center": (256, 560), "right": (380, 560)}.get(wanted, (380, 560))
    best = None
    for at in [pref, (380, 560), (120, 560), (256, 560), (392, 615), (120, 615), (392, 470), (120, 470), (256, 615)]:
        r = [at[0] - w / 2, at[1] - h * 0.85, at[0] + w / 2, at[1] + h * 0.15]
        r = [max(r[0], 8), r[1], min(r[2], PW - 8), r[3]]
        sc = sum(overlap(r, f[:4]) + 8 * overlap(r, f[4:]) for f in faces)
        if best is None or sc < best[0] - 1:
            best = (sc, at)
    return best[1]


def sfx_group(text, wanted, faces):
    """The sound word, wrapped so the page script can move it off faces and words."""
    t = text.upper()[:12]
    fs = 92 if len(t) <= 5 else 70 if len(t) <= 8 else 54
    at = sfx_spot(text, faces, wanted)
    pref = {"left": (120, 560), "center": (256, 560), "right": (380, 560)}.get(wanted, (380, 560))
    return (f'<g class="sfxg" data-w="{len(t) * fs * 0.62:.0f}" data-h="{fs}" data-pref="{json.dumps(list(pref))}" '
            f'transform="translate({at[0]},{at[1]})">{sfx(text, at=(0, 0))}</g>')


def overlap(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0


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
    heads, spots = {}, []
    for j, c in enumerate(p.get("cast", [])):
        x, y, s, head = place(c, room, extras)
        heads.setdefault(c["who"], head)
        spots.append((c["who"], x, y, s))
        info = who_info(c["who"], extras)
        draw = info["draw"]
        for cls, talk, blink in (("quiet", False, False), ("talk", True, False), ("half", 1, False), ("blink", False, True)):
            chars.append(f'<g class="layer char c{j} {cls}" data-who="{html.escape(c["who"])}">'
                         f'{draw(x, y, s, c.get("mood", "neutral"), c.get("flip", False), talking=talk, prop=c.get("holding"), blink=blink)}</g>')
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
    faces = [face_boxes(w, x, y, s) for w, x, y, s in spots]
    cam = f'<g class="cam" transform="translate({tx:.1f},{ty:.1f}) scale({k})">'
    art = [f'<g class="layer bg">{cam}{bg}</g></g>', *[f"{cam}{c}</g>" for c in chars],
           f'<g class="layer fg">{cam}{"".join(front)}</g></g>',
           f'<g class="layer fg sfxl">{sfx_group(p["sfx"], p.get("sfx_spot", "right"), [face_boxes(w, x, y, s, k, tx, ty) for w, x, y, s in spots]) if p.get("sfx") else ""}</g>']
    wheads = dict(heads)
    heads = {w: (k * h[0] + tx, k * h[1] + ty) for w, h in heads.items()}
    bubbles = []
    lines = p.get("lines", [])
    for kk, ln in enumerate(lines):
        hx, hy = heads.get(ln["who"], (256, 300))
        wx, wy = wheads.get(ln["who"], ((256 - tx) / k, (300 - ty) / k))
        words = len(ln["text"].split())
        fs = 38 if words <= 8 else 34 if words <= 14 else 30
        shout = " shout" if ln.get("style") == "shout" else " think" if ln.get("style") == "thought" else ""
        bubbles.append(f'<div class="b layer bub{kk}{shout}" data-wx="{wx:.1f}" data-wy="{wy:.1f}" style="font-size:{fs + (6 if shout == " shout" else 0)}px">'
                       f'{html.escape(ln["text"])}</div>')
    nar = (f'<div class="nar layer narr">{html.escape(p["narration"])}</div>' if p.get("narration") else "")
    return (f'<div class="p" id="p{i}" data-faces="{html.escape(json.dumps(faces))}" data-cam="{html.escape(json.dumps([k, round(tx, 1), round(ty, 1)]))}"><svg class="art" viewBox="0 0 {PW} {PH}" width="{PW}" height="{PH}">{"".join(art)}</svg>'
            f'<svg class="tails" viewBox="0 0 {PW} {PH}" width="{PW}" height="{PH}"></svg>{nar}{"".join(bubbles)}</div>')


SCRIPT = """
function ov(a, b) {
  const w = Math.min(a[2], b[2]) - Math.max(a[0], b[0]), h = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
  return w > 0 && h > 0 ? w * h : 0;
}
// faces and speaker points arrive in scene units; a camera (k, tx, ty) maps them into the panel
const viaCam = (r, c) => [c[0] * r[0] + c[1], c[0] * r[1] + c[2], c[0] * r[2] + c[1], c[0] * r[3] + c[2]];
function cover(r, faces) {   // how much face a rectangle hides; eyes and mouth count eight times over
  let s = 0, feat = 0;
  for (const f of faces) { s += ov(r, f.slice(0, 4)); feat += ov(r, f.slice(4, 8)); }
  return [s + 8 * feat, feat];
}
function plan(bs, dims, faces, cam, taken0) {
  // every bubble in reading order: try each width and position, keep the one that hides the least face,
  // sits near its speaker and as high as it can
  const taken = taken0.slice(), out = [];
  let prev = null, total = 0, feat = 0;
  bs.forEach((b, k) => {
    const hx = cam[0] * +b.dataset.wx + cam[1];
    let best = null;
    dims[k].forEach(([mw, w, h], wi) => {
      for (let t = 14; t + h <= PH * 0.66; t += 6) {
        if (prev && t < prev.t) continue;
        for (let l = 14; l + w <= PW - 14; l += 8) {
          if (prev && t < prev.t + prev.h + 10 && l < prev.l + prev.w + 10) continue;
          const r = [l, t, l + w, t + h];
          if (taken.some(q => ov(r, q) > 0)) continue;
          const [c, fe] = cover(r, faces);
          const s = c + Math.abs(l + w / 2 - hx) * 3 + t * 2 + wi * 500;
          if (!best || s < best.s) best = {s, c, fe, mw, t, l, w, h};
        }
      }
    });
    if (!best) {   // nothing fits: stack under the previous bubble
      const [mw, w, h] = dims[k][0];
      const t = prev ? prev.t + prev.h + 14 : 22;
      best = {s: 1e7, c: 1e6, fe: 1e5, mw, t, l: Math.min(Math.max(hx - w / 2, 14), PW - w - 14), w, h};
    }
    taken.push([best.l - 6, best.t - 6, best.l + best.w + 6, best.t + best.h + 6]);
    prev = best; total += best.s; feat += best.fe; out.push(best);
  });
  return {out, total, feat, taken};
}
function layout() {
  for (const p of document.querySelectorAll('.p')) {
    const tails = p.querySelector('.tails'); tails.innerHTML = '';
    const nar = p.querySelector('.nar');
    const wfaces = JSON.parse(p.dataset.faces || '[]');
    const cam0 = JSON.parse(p.dataset.cam || '[1,0,0]');
    const taken0 = nar ? [[0, 0, nar.offsetLeft + nar.offsetWidth + 10, nar.offsetTop + nar.offsetHeight + 12]] : [];
    const bs = [...p.querySelectorAll('.b')];
    const dims = bs.map(b => [400, 330, 260].map(mw => { b.style.maxWidth = mw + 'px'; return [mw, b.offsetWidth, b.offsetHeight]; }));
    // a close shot that leaves no clean room for the words pulls back a little, up to the full wide view
    const cams = REZOOM && cam0[0] > 1 ? [0, 0.35, 0.7, 1].map(u => [cam0[0] + (1 - cam0[0]) * u, cam0[1] * (1 - u), cam0[2] * (1 - u)]) : [cam0];
    let pick = null;
    for (const [ci, cam] of cams.entries()) {
      const faces = wfaces.map(f => viaCam(f.slice(0, 4), cam).concat(viaCam(f.slice(4, 8), cam)));
      const r = plan(bs, dims, faces, cam, taken0);
      r.cam = cam; r.faces = faces; r.score = r.total + ci * 2500;
      if (!pick || r.score < pick.score) pick = r;
      if (r.feat === 0 && r.out.every(o => o.c < 1800)) break;
    }
    if (pick.cam !== cam0)
      p.querySelectorAll('g.cam').forEach(g => g.setAttribute('transform', `translate(${pick.cam[1].toFixed(1)},${pick.cam[2].toFixed(1)}) scale(${pick.cam[0].toFixed(3)})`));
    bs.forEach((b, k) => {
      const o = pick.out[k], left = o.l, top = o.t, w = o.w, h = o.h;
      const hx = pick.cam[0] * +b.dataset.wx + pick.cam[1], hy = pick.cam[0] * +b.dataset.wy + pick.cam[2];
      b.style.maxWidth = o.mw + 'px'; b.style.left = left + 'px'; b.style.top = top + 'px';
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
    });
    // the sound word goes where it hides the least face and stays clear of the words
    const g = p.querySelector('g.sfxg');
    if (g) {
      const w = +g.dataset.w, h = +g.dataset.h, pref = JSON.parse(g.dataset.pref);
      const spots = [pref, [380, 560], [120, 560], [256, 560], [392, 615], [120, 615], [392, 470], [120, 470], [256, 615],
                     [392, 140], [120, 140], [256, 140], [392, 300], [120, 300]];
      const block = REZOOM ? pick.taken : [];
      let best = null;
      for (const [i, at] of spots.entries()) {
        const r = [Math.max(at[0] - w / 2, 8), at[1] - h * 0.85, Math.min(at[0] + w / 2, PW - 8), at[1] + h * 0.15];
        if (block.some(q => ov(r, q) > 0)) continue;
        const s = cover(r, pick.faces)[0] + i * 40;
        if (!best || s < best.s) best = {s, at};
      }
      if (best) g.setAttribute('transform', `translate(${best.at[0]},${best.at[1]})`);
    }
  }
}
function only(sel) {  // show just the matching layers (for Reel compositing)
  document.querySelectorAll('.layer').forEach(e => e.style.visibility = e.matches(sel) ? 'visible' : 'hidden');
  document.body.style.background = 'transparent'; document.documentElement.style.background = 'transparent';
  document.querySelectorAll('.p, .sheet').forEach(e => { e.style.background = 'transparent'; e.style.outlineColor = 'transparent'; });
}
function still() { document.querySelectorAll('.talk, .half, .blink').forEach(e => e.style.display = 'none'); }
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
<script>const PW={PW}, PH={PH}, INK="{INK}", REZOOM={"false" if single else "true"};{SCRIPT}document.fonts.ready.then(() => {{ layout(); document.body.dataset.ready = 1; }});</script></body></html>'''
