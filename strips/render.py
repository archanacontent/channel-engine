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
    return pw, pw.chromium.launch()


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


def layers(spec):
    """Per panel: background, each character quiet/talking, each bubble, as RGBA images at 1080 wide."""
    pw, b = browser()
    html = page(spec, FONT.as_uri(), single=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
    pg = b.new_page(viewport={"width": 512, "height": 647}, device_scale_factor=SCALE)
    pg.goto(Path(f.name).as_uri())
    pg.wait_for_selector("body[data-ready]")
    out = []
    for i, p in enumerate(spec["panels"]):
        loc = pg.locator(f"#p{i}")
        grab = lambda sel: Image.open(io.BytesIO(
            (pg.evaluate(f"only({json.dumps(sel)})"), loc.screenshot(omit_background=True))[1])).convert("RGBA")
        L = {"bg": grab(f"#p{i} .bg"), "fg": grab(f"#p{i} .fg")}
        L["bg"] = Image.alpha_composite(Image.new("RGBA", L["bg"].size, (255, 255, 255, 255)), L["bg"])
        for j, c in enumerate(p.get("cast", [])):
            L[f"c{j}"] = grab(f"#p{i} .c{j}.quiet")
            L[f"c{j}t"] = grab(f"#p{i} .c{j}.talk")
        for k, _ in enumerate(p.get("lines", [])):
            L[f"b{k}"] = grab(f"#p{i} .bub{k}")
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


def render_reel(spec, voices, out, brand):
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
        if p.get("narration"):
            s = speak(p["narration"], voices.get("Narrator", NARRATOR), tmp)
            nars[i] = t
            parts += [s, np.zeros(int(SR * 0.2), np.float32)]; t += len(s) / SR + 0.2
        for k, ln in enumerate(p.get("lines", [])):
            s = speak(ln["text"], voice_for(ln["who"], voices, spec), tmp)
            d = len(s) / SR
            events.append((i, k, ln["who"], t, t + d, s, ln.get("style")))
            parts += [s, np.zeros(int(SR * 0.26), np.float32)]; t += d + 0.26
        hold = 1.1 if i == last else 0.45
        parts.append(np.zeros(int(SR * hold), np.float32)); t += hold
    end_card = 1.6
    total = t + end_card
    voice = np.concatenate(parts)
    voice = voice / (np.max(np.abs(voice)) + 1e-9) * 0.9
    stem = Path(out).stem
    bed, _ = bed_for(brand["slug"], stem, total, ROOT / "channels" / brand["slug"] / "music")
    wav = Path(tmp) / "mix.wav"
    mixdown(voice, bed, brand["music"]["gain_db"], wav)
    env = np.abs(voice)
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
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}",
                            "-r", str(FPS), "-i", "-", "-i", str(wav), "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "160k",
                            "-shortest", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    n = int(total * FPS)
    rng = np.random.default_rng(7)
    held = None
    for fi in range(n):
        tt = fi / FPS
        i = max(j for j, s0 in enumerate(starts) if s0 <= tt) if tt >= starts[0] else 0
        Lp, cam = L[i], cams[i]
        dt = tt - starts[i]
        dur = (starts[i + 1] if i < last else total - end_card) - starts[i]
        frame = base.copy()
        panel = Lp["bg"].copy()
        for j, c in enumerate(panels[i].get("cast", [])):
            talking = any(e[0] == i and e[2] == c["who"] and e[3] <= tt < e[4] and
                          env[int(tt * SR):int(tt * SR) + 800].mean() > 0.02 and int(tt * 10) % 2 == 0 for e in events)
            speaking = any(e[0] == i and e[2] == c["who"] and e[3] <= tt < e[4] for e in events)
            sprite = Lp[f"c{j}t" if talking else f"c{j}"]
            if c["who"] == "Pim":
                dy = int(np.sin(tt * 2.2 + j) * 8)
            else:
                dy = int(np.sin(tt * 2.6 + j * 1.7) * 3) - (int(abs(np.sin(tt * 9)) * 7) if speaking else 0)
            panel.alpha_composite(sprite, (0, dy))
        panel.alpha_composite(Lp["fg"])
        if "nar" in Lp and tt >= nars.get(i, starts[i]) - 0.1:
            panel.alpha_composite(Lp["nar"])
        for e in events:
            if e[0] == i and tt >= e[3] - 0.1:
                b = Lp[f"b{e[1]}"]
                pop = min(1.0, (tt - e[3] + 0.1) / 0.18)
                if pop < 1:
                    sc = (0.6 + 0.4 * pop) if e[6] == "shout" else (0.85 + 0.15 * pop)
                    bb = b.resize((int(b.width * sc), int(b.height * sc)))
                    tmpl = Image.new("RGBA", b.size, (0, 0, 0, 0))
                    tmpl.alpha_composite(bb, ((b.width - bb.width) // 2, (b.height - bb.height) // 2))
                    b = tmpl
                panel.alpha_composite(b)
        # camera: slow drift and push-in, a punch-in on close shots and the punchline, a shake on loud moments
        prog = min(1.0, max(0.0, dt / max(dur, 0.1)))
        z = 1.0 + 0.06 * prog
        if cam["punch"]:
            z += 0.16 * max(0.0, 1 - dt / 0.22) ** 2
        fxp = 0.5 + cam["dir"] * 0.02 * (prog - 0.5)
        sx = sy = 0
        shake_t = [dt] if cam["jolt"] else []
        shake_t += [tt - e[3] for e in events if e[0] == i and e[6] == "shout"]
        for st in shake_t:
            if 0 <= st < 0.4:
                amp = 16 * (1 - st / 0.4)
                sx += int(rng.uniform(-amp, amp)); sy += int(rng.uniform(-amp, amp))
        panel = zoom(panel, z, fxp, 0.5, sx, sy)
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
                frame.alpha_composite(held, (x - RW * (1 if cam["style"] == "whip" else -1), PY))
        if alpha < 1:
            panel.putalpha(Image.eval(panel.getchannel("A"), lambda a: int(a * alpha)))
        frame.alpha_composite(panel, (x, y))
        if cam["jolt"] and 0 <= dt < 2 / FPS:   # a white flash on impact
            frame.alpha_composite(Image.new("RGBA", (RW, RH), (255, 255, 255, 170)))
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
