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
    canvas.save(out, quality=95)
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


def render_reel(spec, voices, out, brand):
    from render.audio import SR, mixdown
    from render.music import bed_for
    from render.lib import font, tw
    L = layers(spec)
    tmp = tempfile.mkdtemp()
    # timeline: per panel, enter 0.45s, then each line, then a beat
    parts, events, t = [np.zeros(int(SR * 0.3), np.float32)], [], 0.3
    starts = []
    for i, p in enumerate(spec["panels"]):
        starts.append(t)
        pad = 0.45
        parts.append(np.zeros(int(SR * pad), np.float32)); t += pad
        for k, ln in enumerate(p.get("lines", [])):
            s = speak(ln["text"], voices[ln["who"]], tmp)
            d = len(s) / SR
            events.append((i, k, ln["who"], t, t + d, s))
            parts += [s, np.zeros(int(SR * 0.28), np.float32)]; t += d + 0.28
        hold = 0.9 if i == len(spec["panels"]) - 1 else 0.5
        parts.append(np.zeros(int(SR * hold), np.float32)); t += hold
    end_card = 1.6
    total = t + end_card
    voice = np.concatenate(parts)
    voice = voice / (np.max(np.abs(voice)) + 1e-9) * 0.9
    stem = Path(out).stem
    bed, _ = bed_for(brand["slug"], stem, total, ROOT / "channels" / brand["slug"] / "music")
    wav = Path(tmp) / "mix.wav"
    mixdown(voice, bed, brand["music"]["gain_db"], wav)
    # per-frame amplitude for mouth flaps
    env = np.abs(voice)
    title_f = font("SourceSerif4[opsz,wght].ttf", 54, 700)
    small_f = font("Inter[opsz,wght].ttf", 36, 600)
    from PIL import ImageDraw
    bgc = tuple(int(brand["palette"]["background"][i:i + 2], 16) for i in (1, 3, 5))
    base = Image.new("RGBA", (RW, RH), bgc + (255,))
    d = ImageDraw.Draw(base)
    title = brand["series_title"]
    d.text(((RW - tw(title_f, title)) / 2, 120), title, font=title_f, fill=(255, 253, 247))
    foot = brand["handle"]
    d.text(((RW - tw(small_f, foot)) / 2, 1740), foot, font=small_f, fill=(200, 190, 220))
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}",
                            "-r", str(FPS), "-i", "-", "-i", str(wav), "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "160k",
                            "-shortest", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    n = int(total * FPS)
    for fi in range(n):
        tt = fi / FPS
        i = max(j for j, s0 in enumerate(starts) if s0 <= tt) if tt >= starts[0] else 0
        Lp = L[i]
        frame = base.copy()
        k_in = min(1.0, (tt - starts[i]) / 0.35)
        ease = 1 - (1 - k_in) ** 3
        panel = Lp["bg"].copy()
        bob_t = tt * 2.2
        for j, c in enumerate(spec["panels"][i].get("cast", [])):
            talking = any(e[0] == i and e[2] == c["who"] and e[3] <= tt < e[4] and
                          env[int(tt * SR):int(tt * SR) + 800].mean() > 0.02 and int(tt * 10) % 2 == 0 for e in events)
            sprite = Lp[f"c{j}t" if talking else f"c{j}"]
            dy = int(np.sin(bob_t + j) * 8) if c["who"] == "Pim" else 0
            panel.alpha_composite(sprite, (0, dy))
        panel.alpha_composite(Lp["fg"])
        for e in events:
            if e[0] == i and tt >= e[3] - 0.1:
                b = Lp[f"b{e[1]}"]
                pop = min(1.0, (tt - e[3] + 0.1) / 0.18)
                if pop < 1:
                    sc = 0.85 + 0.15 * pop
                    bb = b.resize((int(b.width * sc), int(b.height * sc)))
                    tmpl = Image.new("RGBA", b.size, (0, 0, 0, 0))
                    tmpl.alpha_composite(bb, ((b.width - bb.width) // 2, (b.height - bb.height) // 2))
                    b = tmpl
                panel.alpha_composite(b)
        y = PY + int((1 - ease) * 60)
        if k_in < 1:
            panel.putalpha(Image.eval(panel.getchannel("A"), lambda a: int(a * ease)))
        frame.alpha_composite(panel, (0, y))
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
