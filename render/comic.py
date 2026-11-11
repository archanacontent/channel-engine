"""Motion-comic renderer: pans across a scanned comic page panel by panel while
each line is voiced in its character's voice, with a narrator hook up front and
a closing line at the end.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from render import audio
from render.lib import FPS, H, W, alpha_rect, ease_io, font, rgb, tw, wrap

STAGE = (40, 250, 1040, 1450)          # where the page is shown
SW, SH = STAGE[2] - STAGE[0], STAGE[3] - STAGE[1]
MOVE = 0.55                            # seconds for the camera to travel to the next panel
LINE_GAP, PANEL_GAP, SILENT_PANEL = 0.22, 0.35, 1.3
END = 1.6


def fit_rect(box, iw, ih, pad=0.03):
    """Crop rect around a box (padded), clamped to the page, plus its on-screen rect.

    Wide panels get a wide, shorter frame and tall panels a tall one, so the
    panel fills the screen instead of showing its neighbours."""
    x0, y0, x1, y1 = box
    w, h = (x1 - x0) * (1 + pad * 2), (y1 - y0) * (1 + pad * 2)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    asp = max(0.62, min(w / h, SW / 560))          # screen frame from 744x1200 (tall) to 1000x560 (wide)
    if w / h > asp:
        h = w / asp
    else:
        w = h * asp
    x0 = min(max(cx - w / 2, 0), max(0, iw - w)) if w <= iw else (iw - w) / 2
    y0 = min(max(cy - h / 2, 0), max(0, ih - h)) if h <= ih else (ih - h) / 2
    dw, dh = (SW, SW / asp) if SW / asp <= SH else (SH * asp, SH)
    mid = (STAGE[1] + STAGE[3]) / 2
    disp = np.array([W / 2 - dw / 2, mid - dh / 2, W / 2 + dw / 2, mid + dh / 2], float)
    return np.concatenate([np.array([x0, y0, x0 + w, y0 + h], float), disp])


def build_timeline(ep, iw, ih, voices):
    """Shots [(t0, t1, rect)], lines [(t0, t1, speaker, voice, text)] and the voice track."""
    k = audio.kokoro()
    page = fit_rect((0, 0, iw, ih), iw, ih, pad=0.0)
    segs = [{"rect": page, "lines": [{"speaker": "Narrator", "voice": "narrator", "text": ep["hook"]}]}]
    for p in ep["panels"]:
        y0, x0, y1, x1 = p["box"]
        box = (x0 / 1000 * iw, y0 / 1000 * ih, x1 / 1000 * iw, y1 / 1000 * ih)
        segs.append({"rect": fit_rect(box, iw, ih), "lines": p["lines"]})
    segs.append({"rect": page, "lines": [{"speaker": "Narrator", "voice": "narrator", "text": ep["closer"]}]})

    parts, shots, lines, t = [np.zeros(int(audio.SR * 0.2), np.float32)], [], [], 0.2
    for i, seg in enumerate(segs):
        start = t
        if i > 0:  # let the camera arrive before anyone speaks
            parts.append(np.zeros(int(audio.SR * MOVE * 0.6), np.float32))
            t += MOVE * 0.6
        if not seg["lines"]:
            parts.append(np.zeros(int(audio.SR * SILENT_PANEL), np.float32))
            t += SILENT_PANEL
        for ln in seg["lines"]:
            v = voices.get(ln["voice"], voices["narrator"])
            s, sr = k.create(ln["text"], voice=v["voice"], speed=v.get("speed", 1.0), lang=v.get("lang", "en-us"))
            s = audio.trim(np.asarray(s, np.float32))
            d = len(s) / audio.SR
            lines.append((t, t + d, ln["speaker"], ln["voice"], ln["text"]))
            parts += [s, np.zeros(int(audio.SR * LINE_GAP), np.float32)]
            t += d + LINE_GAP
        parts.append(np.zeros(int(audio.SR * PANEL_GAP), np.float32))
        t += PANEL_GAP
        shots.append((start, t, seg["rect"]))
    total = t + END
    v = np.concatenate(parts)
    v = v / (np.max(np.abs(v)) + 1e-9) * 0.89
    return shots, lines, v, total


class ComicPainter:
    def __init__(self, brand, ep, page):
        self.brand, self.ep, self.page = brand, ep, page
        pal = brand["palette"]
        self.bg, self.text, self.accent = rgb(pal["background"]), rgb(pal["text"]), rgb(pal["accent"])
        self.muted, self.hi = rgb(pal["muted_text"]), rgb(pal["highlight"])
        cover = page.copy()
        s = max(W / cover.width, H / cover.height)
        cover = cover.resize((int(cover.width * s) + 1, int(cover.height * s) + 1))
        cover = cover.crop(((cover.width - W) // 2, (cover.height - H) // 2, (cover.width - W) // 2 + W,
                            (cover.height - H) // 2 + H)).filter(ImageFilter.GaussianBlur(28))
        self.backdrop = Image.blend(cover, Image.new("RGB", (W, H), self.bg), 0.72)
        d = ImageDraw.Draw(self.backdrop)
        f1 = font(brand["fonts"]["headline"]["file"], 50, brand["fonts"]["headline"].get("weight"))
        f2 = font(brand["fonts"]["caption"]["file"], 32, 500)
        name = ep["comic"].upper()
        while tw(f1, name) > 980 and f1.size > 30:
            f1 = font(brand["fonts"]["headline"]["file"], f1.size - 2, brand["fonts"]["headline"].get("weight"))
        d.text(((W - tw(f1, name)) / 2, 110), name, font=f1, fill=self.text)
        from datetime import date
        sub = f"{ep['creator'].split(' (')[0]}  ·  {date.fromisoformat(ep['date']).strftime('%B %-d, %Y')}"
        d.text(((W - tw(f2, sub)) / 2, 178), sub, font=f2, fill=self.muted)
        self.cap = font(brand["fonts"]["caption"]["file"], 58, 700)
        self.who = font(brand["fonts"]["caption"]["file"], 34, 700)
        self.colors = {k: rgb(v) for k, v in brand["speaker_colors"].items()}

    def rect_at(self, shots, t):
        for i, (t0, t1, r) in enumerate(shots):
            if t < t1 or i == len(shots) - 1:
                if i == 0:
                    r = r.copy()
                    zoom = 1 - 0.04 * min(1, t / max(t1, 0.1))
                    c = (r[:2] + r[2:4]) / 2
                    half = (r[2:4] - r[:2]) / 2 * zoom
                    r[:4] = np.concatenate([c - half, c + half])
                    return r
                prev = shots[i - 1][2]
                k = ease_io(min(1.0, max(0.0, (t - t0) / MOVE)))
                return prev + (r - prev) * k
        return shots[-1][2]

    def frame(self, shots, lines, total, t):
        img = self.backdrop.copy()
        r = self.rect_at(shots, t)
        crop, disp = r[:4], r[4:]
        dw, dh = int(round(disp[2] - disp[0])), int(round(disp[3] - disp[1]))
        view = self.page.transform((dw, dh), Image.EXTENT, tuple(crop), Image.BILINEAR, fillcolor=(18, 16, 14))
        x, y = int(round(disp[0])), int(round(disp[1]))
        alpha_rect(img, (x + 10, y + 16, x + dw + 10, y + dh + 16), (0, 0, 0), 0.55)
        img.paste(view, (x, y))
        d = ImageDraw.Draw(img)
        d.rectangle((x, y, x + dw, y + dh), outline=self.text, width=4)
        end_at = total - END
        if t >= end_at:
            self.end_card(img, d, t - end_at)
            return img
        for (t0, t1, who, voice, text) in lines:
            if t0 - 0.05 <= t < t1 + LINE_GAP:
                self.caption(d, img, who, voice, text, t - t0, t1 - t0)
                break
        return img

    def caption(self, d, img, who, voice, text, t_in, dur):
        rows = wrap(text, self.cap, 960)
        pages = [rows[i:i + 3] for i in range(0, len(rows), 3)]
        weights = [sum(len(x) for x in pg) for pg in pages]
        acc, idx = 0.0, 0
        for i, wgt in enumerate(weights):
            acc += dur * wgt / max(1, sum(weights))
            if t_in < acc:
                idx = i
                break
            idx = i
        pg = pages[idx]
        col = self.colors.get(voice, self.hi)
        y = 1500
        if who and who.lower() != "narrator":
            label = who.upper()
            wl = tw(self.who, label)
            d.rounded_rectangle(((W - wl) / 2 - 18, y, (W + wl) / 2 + 18, y + 52), 14, fill=col)
            d.text(((W - wl) / 2, y + 7), label, font=self.who, fill=self.bg)
        y += 72
        for row in pg:
            x = (W - tw(self.cap, row)) / 2
            for dx, dy in ((0, 4), (2, 3), (-2, 3)):
                d.text((x + dx, y + dy), row, font=self.cap, fill=(0, 0, 0))
            d.text((x, y), row, font=self.cap, fill=self.text if who.lower() != "narrator" else self.hi)
            y += 72

    def end_card(self, img, d, t):
        k = min(1.0, t / 0.4)
        overlay = Image.new("RGB", (W, H), self.bg)
        img.paste(Image.blend(img, overlay, 0.85 * k))
        d = ImageDraw.Draw(img)
        f1 = font(self.brand["fonts"]["headline"]["file"], 76, self.brand["fonts"]["headline"].get("weight"))
        f2 = font(self.brand["fonts"]["caption"]["file"], 40, 600)
        for i, (txt, f, c) in enumerate(((self.brand["name"], f1, self.text),
                                         (self.brand["end_line"], f2, self.hi))):
            for j, row in enumerate(wrap(txt, f, 940)):
                d.text(((W - tw(f, row)) / 2, 820 + i * 170 + j * 88), row, font=f, fill=c)


def render_comic(brand, ep, chan_dir, out, stem, metadata, srt):
    page = Image.open(ep["media"]["image"]).convert("RGB")
    voices = brand["voices"]
    shots, lines, voice, total = build_timeline(ep, page.width, page.height, voices)
    if total > 178:
        raise SystemExit(f"Too long for a Short: {total:.0f}s")
    painter = ComicPainter(brand, ep, page)
    bed, bed_name = audio.load_bed(brand["slug"], chan_dir / "music", total, stem)
    wav = out / f"{stem}.wav"
    audio.mixdown(voice, bed, brand["music"]["gain_db"], wav)
    tmp = out / f"{stem}.video.part.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                            "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    n = int(round(total * FPS))
    for i in range(n):
        enc.stdin.write(painter.frame(shots, lines, total, i / FPS).tobytes())
        if i % 450 == 0:
            print(f"{brand['slug']}: frame {i}/{n}", flush=True)
    enc.stdin.close()
    assert enc.wait() == 0
    final = out / f"{stem}.part.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    final.rename(out / f"{stem}.mp4")
    tmp.unlink()
    wav.unlink()
    captions = [(t0, t1, [(w, None) for w in (text if who.lower() == "narrator" else f"{who}: {text}").split()])
                for (t0, t1, who, voice_, text) in lines]
    meta = metadata(brand, ep)
    meta.update({"duration_s": round(total, 2), "music": bed_name})
    (out / f"{stem}.json").write_text(json.dumps(meta, indent=2))
    (out / f"{stem}.srt").write_text(srt(captions))
    print("done", out / f"{stem}.mp4", round(total, 1), "s")
