"""Shared drawing, caption and timing helpers for every channel."""
import math
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

# Shorts and Reels draw their own buttons on the right and text at the bottom,
# so captions sit above that band and visuals stay between these lines.
SAFE_TOP, SAFE_BOTTOM, CAPTION_Y = 250, 1500, 1330


def rgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


@lru_cache(maxsize=256)
def font(file, size, weight=None, opsz=None):
    f = ImageFont.truetype(str(FONTS / file), size)
    try:
        axes = f.get_variation_axes()
    except OSError:
        return f
    vals = []
    for ax in axes:
        name = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
        if name.lower().startswith("weight"):
            vals.append(weight if weight else ax["default"])
        elif name.lower().startswith("optical"):
            vals.append(max(ax["minimum"], min(ax["maximum"], opsz or size)))
        else:
            vals.append(ax["default"])
    f.set_variation_by_axes(vals)
    return f


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def prog(t, start, dur):
    return ease((t - start) / dur) if dur > 0 else float(t >= start)


def tw(f, text):
    return f.getlength(text)


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if tw(f, trial) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_c(d, cx, y, text, f, fill):
    d.text((cx - tw(f, text) / 2, y), text, font=f, fill=fill)


def alpha_rect(img, box, color, opacity, radius=0):
    x0, y0, x1, y1 = [int(v) for v in box]
    if x1 <= x0 or y1 <= y0:
        return
    tile = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius=radius,
                                           fill=color + (int(255 * opacity),))
    img.paste(tile, (x0, y0), tile)


def fade_paste(img, layer, xy, opacity):
    """Paste an RGBA layer with an overall opacity."""
    if opacity <= 0:
        return
    if opacity < 1:
        a = layer.getchannel("A").point(lambda v: int(v * opacity))
        layer = layer.copy()
        layer.putalpha(a)
    img.paste(layer, xy, layer)


# ---------- captions ----------

def _norm(w):
    return re.sub(r"[^a-z0-9,]+", "", w.lower()).strip(",")


def mark_words(words, phrases):
    marks = [False] * len(words)
    normed = [_norm(w) for w in words]
    for p in phrases or []:
        pw = [_norm(x) for x in str(p).split()]
        n = len(pw)
        for i in range(len(words) - n + 1):
            if normed[i:i + n] == pw:
                for j in range(i, i + n):
                    marks[j] = True
    return marks


def chunk_caption(text, max_words=4, max_chars=24):
    words = text.split()
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        joined = " ".join(words[j] for j in cur)
        end_punct = w[-1] in ".?!:"
        soft = w[-1] in ","
        nxt_len = len(joined) + 1 + (len(words[i + 1]) if i + 1 < len(words) else 0)
        if end_punct or len(cur) >= max_words or nxt_len > max_chars or (soft and len(cur) >= 2):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return words, chunks


def caption_timeline(beat_caption, speech_dur, start, mark_sets):
    """Return [(t0, t1, [(word, color_key)])] spread over the spoken time by length."""
    words, chunks = chunk_caption(beat_caption)
    marks = {k: mark_words(words, v) for k, v in mark_sets.items()}
    weights = [sum(len(words[i]) + 1 for i in c) + 4 for c in chunks]
    total = sum(weights)
    out, t = [], start
    for c, wgt in zip(chunks, weights):
        dur = speech_dur * wgt / total
        toks = []
        for i in c:
            key = None
            for k, m in marks.items():
                if m[i]:
                    key = k
            toks.append((words[i], key))
        out.append((t, t + dur, toks))
        t += dur
    return out


def draw_caption(img, toks, style, t_in):
    """Draw one caption chunk centred at CAPTION_Y with a short pop-in."""
    d = ImageDraw.Draw(img)
    size = style["size"]
    f = font(style["font"], size, style.get("weight"))
    space = tw(f, " ")
    widths = [tw(f, w) for w, _ in toks]
    total = sum(widths) + space * (len(toks) - 1)
    if total > 960:
        f = font(style["font"], int(size * 960 / total), style.get("weight"))
        widths = [tw(f, w) for w, _ in toks]
        space = tw(f, " ")
        total = sum(widths) + space * (len(toks) - 1)
    k = ease(t_in / 0.12)
    y = CAPTION_Y + int((1 - k) * 14)
    x0 = (W - total) / 2
    asc, desc = f.getmetrics()
    if style.get("pill"):
        pad_x, pad_y = 30, 18
        alpha_rect(img, (x0 - pad_x, y - pad_y, x0 + total + pad_x, y + asc + desc + pad_y),
                   rgb(style["pill"]["color"]), style["pill"]["opacity"], radius=26)
    x = x0
    for (w, key), wd in zip(toks, widths):
        col = rgb(style["colors"].get(key, style["text"])) if key else rgb(style["text"])
        if key and style.get("marker") == "highlighter":
            alpha_rect(img, (x - 6, y + asc * 0.25, x + wd + 6, y + asc + desc * 0.6),
                       rgb(style["colors"][key]), 1.0, radius=6)
            col = rgb(style["text"])
        if style.get("shadow"):
            sh = rgb(style["shadow"])
            for dx, dy in ((0, 4), (2, 3), (-2, 3)):
                d.text((x + dx, y + dy), w, font=f, fill=sh)
        d.text((x, y), w, font=f, fill=col)
        if key and style.get("marker") == "underline":
            d.rectangle((x, y + asc + desc - 2, x + wd, y + asc + desc + 5), fill=col)
        x += wd + space


# ---------- shared shapes ----------

def arrow(d, p0, p1, fill, width=4, head=16):
    d.line([p0, p1], fill=fill, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    a1, a2 = ang + math.radians(150), ang - math.radians(150)
    d.polygon([p1, (p1[0] + head * math.cos(a1), p1[1] + head * math.sin(a1)),
               (p1[0] + head * math.cos(a2), p1[1] + head * math.sin(a2))], fill=fill)


def supersample(draw_fn, size, scale=3):
    """Draw at 3x then shrink, for smooth logos and circles."""
    big = Image.new("RGBA", (size[0] * scale, size[1] * scale), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(big), scale)
    return big.resize(size, Image.LANCZOS)


def blur_glow(size, xy_r, color, radius=40, alpha=120):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y, r = xy_r
    d.ellipse((x - r, y - r, x + r, y + r), fill=color + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(radius))
