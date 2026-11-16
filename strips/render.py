"""Renders a comic spec as an Instagram image (4 panels, 1080 x 1350) or as a Reel.

    python -m strips.render spec.json --image out.png
    python -m strips.render spec.json --reel out.mp4
"""
import argparse
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from strips.layout import page

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "assets" / "fonts" / "PatrickHand-Regular.woff2"


def browser():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    ch = os.environ.get("STRIPS_BROWSER")   # e.g. "chrome" to use an installed browser
    return pw, pw.chromium.launch(**({"channel": ch} if ch else {}))


def render_image(spec, out):
    pw, b = browser()
    html = page(spec, FONT.as_uri())
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
    pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
    pg.goto(Path(f.name).as_uri())
    pg.wait_for_selector("body[data-ready]")
    pg.evaluate("still()")
    png = pg.locator(".sheet").screenshot()
    b.close(); pw.stop()
    im = Image.open(io.BytesIO(png)).convert("RGB")
    k = min(1080 / im.width, 1350 / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    canvas = Image.new("RGB", (1080, 1350), (255, 253, 247))
    canvas.paste(im, ((1080 - im.width) // 2, (1350 - im.height) // 2))
    canvas.save(out, "JPEG", quality=95, subsampling=0)
    return out


# ------------------------------------------------------------------ Reel

FPS = 30
RW, RH = 1080, 1920
SCALE = 1080 / 512                       # panel units to pixels
PY = 250                                  # panel top in the Reel frame
CAP_Y = 1455                              # caption centre: over the floor, above Instagram's own buttons


ACT = ("quiet", "talk", "half", "blink")   # the four drawn frames of every character
PAD = 70                                    # room around a sprite for stretch and tilt


def layers(spec):
    """Per panel: background, foreground, narration box, and every character as a cropped sprite sheet
    (quiet, talking, half-open, blinking) with the point where its feet touch the floor."""
    from strips.layout import camera, place
    pw, b = browser()
    html = page(spec, FONT.as_uri(), single=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
    pg = b.new_page(viewport={"width": 512, "height": 647}, device_scale_factor=SCALE)
    pg.goto(Path(f.name).as_uri())
    pg.wait_for_selector("body[data-ready]")
    extras = {e["name"]: e for e in spec.get("extras") or []}
    out = []
    for i, p in enumerate(spec["panels"]):
        loc = pg.locator(f"#p{i}")
        grab = lambda sel: Image.open(io.BytesIO(
            (pg.evaluate(f"only({json.dumps(sel)})"), loc.screenshot(omit_background=True))[1])).convert("RGBA")
        L = {"bg": grab(f"#p{i} .bg"), "fg": grab(f"#p{i} .fg:not(.sfxl)"), "chars": []}
        if p.get("sfx"):
            L["sfx"] = grab(f"#p{i} .sfxl")
        L["bg"] = Image.alpha_composite(Image.new("RGBA", L["bg"].size, (255, 255, 255, 255)), L["bg"])
        W, H = L["bg"].size
        spots, heads = [], {}
        for c in p.get("cast", []):
            x, y, s, head = place(c, p["room"], extras)
            heads.setdefault(c["who"], head)
            spots.append((x, y, s, head))
        k, tx, ty = camera(p, heads, p.get("cast", []))
        for j, c in enumerate(p.get("cast", [])):
            full = {a: grab(f"#p{i} .c{j}.{a}") for a in ACT}
            boxes = [im.getbbox() for im in full.values() if im.getbbox()]
            x, y, s, head = spots[j]
            if not boxes:
                continue
            x0 = max(0, min(bx[0] for bx in boxes) - PAD); y0 = max(0, min(bx[1] for bx in boxes) - PAD)
            x1 = min(W, max(bx[2] for bx in boxes) + PAD); y1 = min(H, max(bx[3] for bx in boxes) + PAD)
            L["chars"].append({
                "who": c["who"], "mood": c.get("mood", "neutral"), "j": j, "at": (x0, y0),
                "img": {a: im.crop((x0, y0, x1, y1)) for a, im in full.items()},
                "feet": ((k * x + tx) * SCALE, (k * (y + 124 * s) + ty) * SCALE),
                "head": ((k * head[0] + tx) * SCALE, (k * (head[1] + 70 * s) + ty) * SCALE)})
        if p.get("narration"):
            L["nar"] = grab(f"#p{i} .narr")
        out.append(L)
    b.close(); pw.stop()
    return out


def speak(text, voice, tmp):
    from render.audio import SR, kokoro, trim
    import soundfile as sf
    s, sr = kokoro().create(text, voice=voice["voice"], speed=voice.get("speed", 1.0), lang=voice.get("lang", "en-us"))
    s = trim(np.asarray(s, np.float32))
    pitch = voice.get("pitch", 1.0)
    if abs(pitch - 1.0) > 0.01:
        a, bb = Path(tmp) / "in.wav", Path(tmp) / "out.wav"
        sf.write(a, s, SR)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(a), "-af",
                        f"asetrate={int(SR * pitch)},aresample={SR},atempo={1 / pitch:.4f}", str(bb)], check=True)
        s, _ = sf.read(bb, dtype="float32")
    return s


EXTRA_VOICES = {
    "young_man": {"voice": "am_adam", "speed": 1.05}, "young_woman": {"voice": "af_sarah", "speed": 1.05},
    "teen": {"voice": "af_nova", "speed": 1.1, "pitch": 1.06}, "kid": {"voice": "af_sky", "speed": 1.1, "pitch": 1.25},
    "old_man": {"voice": "bm_lewis", "speed": 0.92, "pitch": 0.92}, "doctor": {"voice": "am_michael", "speed": 1.0},
    "barista": {"voice": "am_echo", "speed": 1.0}, "businessman": {"voice": "bm_george", "speed": 1.02},
    "delivery": {"voice": "am_fenrir", "speed": 1.05}, "fitness": {"voice": "am_puck", "speed": 1.12, "pitch": 0.96},
}
NARRATOR = {"voice": "bm_george", "speed": 1.0}
LOUD = {"shocked", "angry", "panic"}


def voice_for(who, voices, spec):
    if who in voices:
        return voices[who]
    look = next((e.get("look") for e in spec.get("extras") or [] if e["name"] == who), "young_man")
    return EXTRA_VOICES.get(look, EXTRA_VOICES["young_man"])


def zoom(img, z, fx=0.5, fy=0.5, dx=0, dy=0):
    """Crop into img by factor z around (fx, fy) and scale back up; dx, dy shift the frame in pixels."""
    if z <= 1.001 and not dx and not dy:
        return img
    W, H = img.size
    w, h = W / z, H / z
    x0 = min(max(fx * W - w / 2 - dx / z, 0), W - w)
    y0 = min(max(fy * H - h / 2 - dy / z, 0), H - h)
    return img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))


def pose(img, ax, ay, sx=1.0, sy=1.0, deg=0.0):
    """Stretch and tilt a sprite around the point where its feet touch the floor."""
    if abs(sx - 1) < 0.003 and abs(sy - 1) < 0.003 and abs(deg) < 0.05:
        return img
    r = np.deg2rad(deg)
    co, si = np.cos(r), np.sin(r)
    a, b, d, e = co / sx, si / sx, -si / sy, co / sy       # output pixel -> source pixel
    return img.transform(img.size, Image.AFFINE, (a, b, ax - a * ax - b * ay, d, e, ay - d * ax - e * ay), Image.BICUBIC)


def put(dst, src, x, y):
    """alpha_composite that accepts positions partly off the canvas."""
    x, y = int(round(x)), int(round(y))
    l, t = max(0, -x), max(0, -y)
    r, b = min(src.width, dst.width - x), min(src.height, dst.height - y)
    if r > l and b > t:
        dst.alpha_composite(src.crop((l, t, r, b)) if (l, t, r, b) != (0, 0, src.width, src.height) else src, (x + l, y + t))


def chunks(text, t0, t1, max_words=3, max_chars=17):
    """Split a spoken line into short caption cards, timed by their share of the letters."""
    words, cards, cur = text.split(), [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(cur + [w])) > max_chars):
            cards.append(" ".join(cur)); cur = []
        cur.append(w)
        if w[-1] in ".!?," and len(cur) >= 2:
            cards.append(" ".join(cur)); cur = []
    if cur:
        cards.append(" ".join(cur))
    total = sum(len(c) + 2 for c in cards)
    out, t = [], t0
    for c in cards:
        d = (t1 - t0) * (len(c) + 2) / total
        out.append((t, t + d, c)); t += d
    return out


_CARDS = {}


def caption_card(text, shout):
    """One caption card as an image: heavy capitals, white (yellow for a shout), thick ink outline."""
    from PIL import ImageDraw
    from render.lib import font, tw
    key = (text, shout)
    if key not in _CARDS:
        size = 96 if shout else 82
        t = text.upper()
        f = font("Sora[wght].ttf", size, 800)
        while tw(f, t) > RW - 150 and size > 44:
            size -= 6; f = font("Sora[wght].ttf", size, 800)
        w, h = int(tw(f, t)) + 80, size + 80
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.text((w / 2 + 5, h / 2 + 7), t, font=f, anchor="mm", fill=(29, 26, 34, 255), stroke_width=13, stroke_fill=(29, 26, 34, 255))
        d.text((w / 2, h / 2), t, font=f, anchor="mm", fill=(255, 221, 87) if shout else (255, 253, 247),
               stroke_width=11, stroke_fill=(29, 26, 34))
        _CARDS[key] = im
    return _CARDS[key]


LIVELY = {"happy", "laughing", "proud", "love", "excited"}
STILL = {"sleeping", "sleepy"}
ROOTED = {"Fern"}          # hops into frame instead of walking


def render_reel(spec, voices, out, brand):
    """A Reel that plays like a cartoon: characters walk in, blink, breathe and react; mouths follow the
    voice; the camera cuts toward whoever is speaking; each line lands as bold captions on screen."""
    from render.audio import SR, mixdown
    from render.music import bed_for
    from render.lib import font, tw
    L = layers(spec)
    tmp = tempfile.mkdtemp()
    panels = spec["panels"]
    last = len(panels) - 1
    # timeline: per panel, enter, optional narration, each line, then a beat; a longer beat before the punchline
    parts, events, t = [np.zeros(int(SR * 0.3), np.float32)], [], 0.3
    starts, nars = [], {}
    for i, p in enumerate(panels):
        pad = 0.55 if i == last else 0.35
        parts.append(np.zeros(int(SR * pad), np.float32)); t += pad
        starts.append(t - (0.0 if i == last else 0.2))
        if i == 0 or (p["room"] == panels[i - 1]["room"] and
                      {c["who"] for c in p.get("cast", [])} - {c["who"] for c in panels[i - 1].get("cast", [])}):
            parts.append(np.zeros(int(SR * 0.45), np.float32)); t += 0.45      # time for the walk-in
        if p.get("narration"):
            s = speak(p["narration"], voices.get("Narrator", NARRATOR), tmp)
            nars[i] = t
            parts += [s, np.zeros(int(SR * 0.2), np.float32)]; t += len(s) / SR + 0.2
        for k, ln in enumerate(p.get("lines", [])):
            s = speak(ln["text"], voice_for(ln["who"], voices, spec), tmp)
            d = len(s) / SR
            events.append((i, k, ln["who"], t, t + d, s, ln.get("style"), ln["text"]))
            parts += [s, np.zeros(int(SR * 0.26), np.float32)]; t += d + 0.26
        hold = 1.2 if i == last else 0.45
        parts.append(np.zeros(int(SR * hold), np.float32)); t += hold
    end_card = 1.6
    total = t + end_card
    voice = np.concatenate(parts)
    voice = voice / (np.max(np.abs(voice)) + 1e-9) * 0.9
    stem = Path(out).stem
    bed, _ = bed_for(brand["slug"], stem, total, ROOT / "channels" / brand["slug"] / "music")
    wav = Path(tmp) / "mix.wav"
    mixdown(voice, bed, brand["music"]["gain_db"], wav)
    n = int(total * FPS)
    # loudness per video frame drives the mouths and the squash and stretch
    hop = SR // FPS
    env = np.array([np.abs(voice[max(0, f * hop - 300):f * hop + hop]).mean() if f * hop < len(voice) else 0.0 for f in range(n)])
    env = np.minimum(1.0, env / 0.16)
    cards = [(a, b, txt, e[6] == "shout", e[0]) for e in events for a, b, txt in chunks(e[7], e[3], e[4])]
    title_f = font("SourceSerif4[opsz,wght].ttf", 54, 700)
    small_f = font("Inter[opsz,wght].ttf", 36, 600)
    from PIL import ImageDraw
    bgc = tuple(int(brand["palette"]["background"][i:i + 2], 16) for i in (1, 3, 5))
    base = Image.new("RGBA", (RW, RH), bgc + (255,))
    d = ImageDraw.Draw(base)
    title = spec.get("title") or brand["series_title"]
    title = title if tw(title_f, title) < RW - 80 else brand["series_title"]
    d.text(((RW - tw(title_f, title)) / 2, 120), title, font=title_f, fill=(255, 253, 247))
    foot = brand["handle"]
    d.text(((RW - tw(small_f, foot)) / 2, 1740), foot, font=small_f, fill=(200, 190, 220))
    # per panel camera: transition style, drift direction, whether it opens with a jolt
    cams = []
    for i, p in enumerate(panels):
        moods = {c.get("mood") for c in p.get("cast", [])}
        fx = set(p.get("fx") or [])
        jolt = bool(moods & LOUD or fx & {"impact", "speed_lines"} or p.get("sfx"))
        style = "rise" if i == 0 else "smash" if i == last else ("whip" if i % 2 else "slide")
        cams.append({"jolt": jolt, "style": style, "dir": (-1) ** i, "punch": i == last or p.get("shot") in ("close", "extreme_close")})
    # who walks in: everyone in the opening panel, and anyone new while the scene stays in the same room
    rng = np.random.default_rng(7)
    for i, Lp in enumerate(L):
        prev = {c["who"] for c in panels[i - 1].get("cast", [])} if i else set()
        same_room = i > 0 and panels[i]["room"] == panels[i - 1]["room"]
        for ch in Lp["chars"]:
            ch["enters"] = ch["mood"] not in STILL and (i == 0 or (same_room and ch["who"] not in prev))
            ch["side"] = -1 if ch["feet"][0] < RW / 2 else 1
            ch["phase"] = float(rng.uniform(0, 6.28))
            # blinks: one every two to four seconds
            bl, tb = [], float(rng.uniform(0.8, 2.4))
            while tb < total:
                bl.append(tb); tb += float(rng.uniform(2.0, 4.2))
            ch["blinks"] = bl
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}",
                            "-r", str(FPS), "-i", "-", "-i", str(wav), "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "160k",
                            "-shortest", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    held = None
    PWp, PHp = L[0]["bg"].size
    cam_i, cz, cx, cy = -1, 1.0, 0.5, 0.5
    for fi in range(n):
        tt = fi / FPS
        i = max(j for j, s0 in enumerate(starts) if s0 <= tt) if tt >= starts[0] else 0
        Lp, cam = L[i], cams[i]
        dt = tt - starts[i]
        dur = (starts[i + 1] if i < last else total - end_card) - starts[i]
        frame = base.copy()
        panel = Lp["bg"].copy()
        live = [e for e in events if e[0] == i and e[3] <= tt < e[4]]
        speaker = live[0][2] if live else None
        shouts = [tt - e[3] for e in events if e[0] == i and e[6] == "shout" and 0 <= tt - e[3] < 0.45]
        focus = None
        for ch in Lp["chars"]:
            who, mood = ch["who"], ch["mood"]
            talking = who == speaker
            v = env[fi] if talking else 0.0
            act = "talk" if v > 0.42 else "half" if v > 0.1 else "quiet"
            if act == "quiet" and any(0 <= tt - b0 < 0.11 for b0 in ch["blinks"]) and mood not in STILL:
                act = "blink"
            dx = dy = deg = 0.0
            sx = sy = 1.0
            ph = ch["phase"]
            # breathing, and Pim's float
            sy += 0.012 * np.sin(tt * 2.2 + ph)
            if who == "Pim":
                dy += np.sin(tt * 2.2 + ph) * 9; deg += np.sin(tt * 1.3 + ph) * 1.6
            elif mood not in STILL:
                deg += np.sin(tt * 1.1 + ph) * 0.5
            if mood in LIVELY and not talking:
                dy -= abs(np.sin(tt * 5.5 + ph)) * 7
            if mood == "laughing":
                dy -= abs(np.sin(tt * 12)) * 9; sy += 0.03 * np.sin(tt * 24)
            if mood in ("panic", "nervous"):
                dx += np.sin(tt * 38 + ph) * 3
            # walking into frame: a few bouncy steps from the nearest edge
            if ch["enters"] and dt < 0.7:
                u = max(0.0, dt / 0.7)
                k = 1 - (1 - u) ** 3
                far = (ch["feet"][0] + ch["img"]["quiet"].width) if ch["side"] < 0 else (PWp - ch["feet"][0] + ch["img"]["quiet"].width)
                dx += ch["side"] * (1 - k) * far
                steps = 2 if who in ROOTED else 3
                dy -= abs(np.sin(u * np.pi * steps)) * (34 if who in ROOTED else 20) * (1 - u * 0.5)
                deg += -ch["side"] * 5 * (1 - k)
                land = (dt - 0.7 + 0.12) / 0.12
                if 0 < land < 1:
                    sy -= 0.06 * np.sin(land * np.pi); sx += 0.04 * np.sin(land * np.pi)
            # speaking: the body pumps with the voice and leans toward the scene
            if talking:
                sy += 0.045 * v; sx -= 0.02 * v; dy -= 5 * v
                deg += (-1.8 if ch["feet"][0] < PWp / 2 else 1.8) * min(1.0, (tt - live[0][3]) / 0.2)
                focus = ch
            # a loud panel opens with a jump; a shout makes everyone else flinch
            if cam["jolt"] and mood in LOUD and dt < 0.5:
                u = dt / 0.5
                dy -= np.sin(u * np.pi) * 46; sy += 0.10 * np.sin(u * np.pi * 2) * (1 - u)
            for st in shouts:
                if not talking:
                    u = st / 0.45
                    dy -= np.sin(u * np.pi) * 30; deg += (4 if ch["feet"][0] > PWp / 2 else -4) * np.sin(u * np.pi)
            ax, ay = ch["feet"][0] - ch["at"][0], ch["feet"][1] - ch["at"][1]
            put(panel, pose(ch["img"][act], ax, ay, sx, sy, deg), ch["at"][0] + dx, ch["at"][1] + dy)
        panel.alpha_composite(Lp["fg"])
        if "sfx" in Lp and dt < 1.1:      # the sound word slams in, then clears the way for the captions
            u = min(1.0, dt / 0.12)
            sc = (1.5 - 0.5 * u) * (1 + 0.04 * np.sin(dt * 40) * (1 - dt / 1.1))
            w = Lp["sfx"].resize((int(PWp * sc), int(PHp * sc)), Image.BILINEAR)
            if dt > 0.9:
                w.putalpha(Image.eval(w.getchannel("A"), lambda a, k=(1.1 - dt) / 0.2: int(a * k)))
            put(panel, w, (PWp - w.width) * 0.72, (PHp - w.height) * 0.86)
        if "nar" in Lp and tt >= nars.get(i, starts[i]) - 0.1:
            panel.alpha_composite(Lp["nar"])
        # camera: slow drift, a cut toward whoever is speaking, a punch-in on the punchline, a shake on loud moments
        prog = min(1.0, max(0.0, dt / max(dur, 0.1)))
        tz, tx_, ty_ = 1.0 + 0.05 * prog, 0.5 + cam["dir"] * 0.02 * (prog - 0.5), 0.5
        if focus is not None and len(Lp["chars"]) > 1:
            tz += 0.13
            tx_ = 0.5 + (focus["head"][0] / PWp - 0.5) * 0.75
            ty_ = 0.5 + (focus["head"][1] / PHp - 0.5) * 0.45
        elif focus is not None:
            tz += 0.06
        if cam_i != i:
            cam_i, cz, cx, cy = i, tz, tx_, ty_
        cz += (tz - cz) * 0.2; cx += (tx_ - cx) * 0.2; cy += (ty_ - cy) * 0.2
        z = cz
        if cam["punch"]:
            z += 0.16 * max(0.0, 1 - dt / 0.22) ** 2
        sxk = syk = 0
        shake_t = ([dt] if cam["jolt"] else []) + shouts
        for st in shake_t:
            if 0 <= st < 0.4:
                amp = 16 * (1 - st / 0.4)
                sxk += int(rng.uniform(-amp, amp)); syk += int(rng.uniform(-amp, amp))
        panel = zoom(panel, z, cx, cy, sxk, syk)
        x, y, alpha = 0, PY, 1.0
        if not (cam["style"] in ("whip", "slide") and dt < 0.24):
            held = panel
        if cam["style"] == "rise" and dt < 0.35:
            k = 1 - (1 - dt / 0.35) ** 3
            y, alpha = PY + int((1 - k) * 60), k
        elif cam["style"] in ("whip", "slide") and dt < 0.24:
            k = 1 - (1 - dt / 0.24) ** 3
            x = int((1 - k) * RW * (1 if cam["style"] == "whip" else -1))
            if held is not None:   # the previous panel leaves the other way
                put(frame, held, x - RW * (1 if cam["style"] == "whip" else -1), PY)
        if alpha < 1:
            panel.putalpha(Image.eval(panel.getchannel("A"), lambda a: int(a * alpha)))
        put(frame, panel, x, y)
        if cam["jolt"] and 0 <= dt < 2 / FPS:   # a white flash on impact
            frame.alpha_composite(Image.new("RGBA", (RW, RH), (255, 255, 255, 170)))
        # captions: the line being spoken, a few words at a time, popping in over the floor of the scene
        for a, b, txt, shout, pi in cards:
            if pi == i and a <= tt < b + (0.2 if b >= max(e[4] for e in events if e[0] == i) - 0.01 else 0.0):
                card = caption_card(txt, shout)
                pop = min(1.0, (tt - a) / 0.09)
                if pop < 1:
                    sc = 0.72 + 0.34 * pop if pop < 0.8 else 1.06 - 0.06 * (pop - 0.8) / 0.2
                    card = card.resize((max(2, int(card.width * sc)), max(2, int(card.height * sc))), Image.BILINEAR)
                put(frame, card, (RW - card.width) / 2, CAP_Y - card.height / 2)
                break
        if tt > total - end_card:
            k = min(1.0, (tt - (total - end_card)) / 0.35)
            ov = Image.new("RGBA", (RW, RH), bgc + (int(235 * k),))
            frame.alpha_composite(ov)
            dd = ImageDraw.Draw(frame)
            f1 = font("SourceSerif4[opsz,wght].ttf", 76, 700)
            for li, (txt, f, col) in enumerate(((brand["series_title"], f1, (255, 253, 247)),
                                                (brand["end_line"], small_f, (244, 208, 63)))):
                dd.text(((RW - tw(f, txt)) / 2, 840 + li * 120), txt, font=f, fill=col + (int(255 * k),))
        enc.stdin.write(frame.convert("RGB").tobytes())
    enc.stdin.close()
    assert enc.wait() == 0
    return total


if __name__ == "__main__":
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--image")
    ap.add_argument("--reel")
    ap.add_argument("--brand", default=str(ROOT / "channels" / "comicsofy" / "brand.yaml"))
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    brand = yaml.safe_load(Path(a.brand).read_text())
    if a.image:
        render_image(spec, a.image)
    if a.reel:
        print("reel", render_reel(spec, brand["voices"], a.reel, brand))
