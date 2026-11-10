import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from render.lib import (W, H, alpha_rect, blur_glow, clamp, ease, font, mix, prog, rgb, supersample,
                        text_c, tw, wrap)
from render.painters.base import Painter

SO = "Sora[wght].ttf"
IN = "Inter[opsz,wght].ttf"
BANDS = [(233, 205, 168), (201, 142, 90), (241, 222, 193), (185, 118, 70), (226, 190, 150),
         (172, 110, 72), (238, 214, 180), (205, 150, 100)]


@lru_cache(maxsize=16)
def jupiter(d_px, spot=True):
    def draw(dr, s):
        D = d_px * s
        n = 22
        for j in range(n):
            y0 = D * j / n
            dr.rectangle((0, y0, D, y0 + D / n + 2), fill=BANDS[(j * 3 + j // 4) % len(BANDS)])
        if spot:
            dr.ellipse((D * 0.55, D * 0.62, D * 0.75, D * 0.71), fill=(196, 85, 58))

    sq = supersample(draw, (d_px, d_px), scale=2)
    mask = supersample(lambda dr, s: dr.ellipse((0, 0, d_px * s - 1, d_px * s - 1), fill=(255, 255, 255, 255)),
                       (d_px, d_px), scale=2).getchannel("A")
    shade = Image.new("L", (d_px, d_px), 0)
    sd = ImageDraw.Draw(shade)
    sd.ellipse((d_px * 0.45, -d_px * 0.1, d_px * 1.45, d_px * 1.1), fill=110)
    shade = shade.filter(ImageFilter.GaussianBlur(d_px * 0.12))
    sq = Image.composite(Image.new("RGBA", sq.size, (10, 8, 20, 255)), sq, shade)
    sq.putalpha(mask)
    return sq


@lru_cache(maxsize=16)
def earth(d_px):
    def draw(dr, s):
        D = d_px * s
        dr.ellipse((0, 0, D - 1, D - 1), fill=(46, 110, 214))
        dr.ellipse((D * 0.18, D * 0.2, D * 0.55, D * 0.5), fill=(74, 158, 92))
        dr.ellipse((D * 0.5, D * 0.55, D * 0.8, D * 0.85), fill=(74, 158, 92))
        dr.ellipse((D * 0.12, D * 0.04, D * 0.5, D * 0.2), fill=(235, 240, 248))

    return supersample(draw, (max(4, d_px), max(4, d_px)), scale=3)


class FieldPainter(Painter):
    tag_font = (SO, 600)
    caption_style = {"font": IN, "weight": 600, "size": 62, "text": "#F8FAFC",
                     "colors": {"numbers": "#FF8A3D"}, "shadow": "#02040C"}

    def __init__(self, *a):
        super().__init__(*a)
        self.tag_text_color = "#F8FAFC"

    def make_bg(self):
        BW, BH = W + 200, H + 200
        img = Image.new("RGB", (BW, BH), self.p["background"])
        d = ImageDraw.Draw(img)
        rng = np.random.default_rng(5)
        for _ in range(900):
            x, y = rng.uniform(0, BW), rng.uniform(0, BH)
            r = rng.choice([1, 1, 1, 2, 2, 3])
            b = int(rng.uniform(90, 255))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(b, b, min(255, b + 15)))
        glow = blur_glow((BW, BH), (200, 500, 420), self.p["accent"], radius=230, alpha=50)
        img.paste(glow, (0, 0), glow)
        return img

    def background(self, t):
        ox, oy = int(100 + 40 * math.sin(t * 0.03)), int(100 - t * 1.5) % 200
        return self.bg.crop((ox, oy, ox + W, oy + H))

    def logo(self, size):
        vio, org = self.p["accent"], self.p["highlight"]

        def draw(d, s):
            S = size * s
            if not self.bare: d.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=(7, 11, 26))
            c, r = S / 2, S * 0.32
            d.ellipse((c - r, c - r, c + r, c + r), outline=vio, width=max(3, int(S * 0.045)))
            pts = []
            for k in range(10):
                ang = -math.pi / 2 + k * math.pi / 5
                rr = S * 0.17 if k % 2 == 0 else S * 0.07
                pts.append((c + rr * math.cos(ang), c + rr * math.sin(ang)))
            d.polygon(pts, fill=org)

        return supersample(draw, (size, size))

    def beat(self, img, d, i, t, dur):
        getattr(self, f"b{i}")(img, d, t, dur)

    def put(self, img, layer, cx, cy, k=1.0):
        if k < 1:
            a = layer.getchannel("A").point(lambda v: int(v * k))
            layer = layer.copy()
            layer.putalpha(a)
        img.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)

    def label(self, d, y, big, small, k):
        if k <= 0:
            return
        text_c(d, W / 2, y, big, font(SO, 110, 700), mix(self.p["background"], self.p["highlight"], k))
        if small:
            text_c(d, W / 2, y + 130, small, font(SO, 40, 500), mix(self.p["background"], self.p["text"], k))

    def b0(self, img, d, t, dur):
        k = prog(t, 0, 1.2)
        size = int(560 + 80 * k)
        self.put(img, jupiter(size), W / 2, 740, k)
        text_c(d, W / 2, 330, "SCALE IT", font(SO, 40, 600), self.p["highlight"])

    def b1(self, img, d, t, dur):
        D = 880
        cy = 620
        self.put(img, jupiter(D), W / 2, cy)
        e = D // 11
        k = prog(t, 0.6, dur * 0.55)
        n = int(11 * k + 0.0001)
        d.line((100, cy, 980, cy), fill=self.p["highlight"], width=3)
        for j in range(n):
            self.put(img, earth(e), 100 + e / 2 + j * e, cy)
        self.label(d, 1085, "11×", "wider than Earth", prog(t, 0.6 + dur * 0.55, 0.4))

    def b2(self, img, d, t, dur):
        R, cy = 380, 700
        d.ellipse((W / 2 - R, cy - R, W / 2 + R, cy + R), outline=self.p["accent"], width=6)
        pts = []
        step = 21
        for y in range(-R + 10, R - 9, step):
            for x in range(-R + 10, R - 9, step):
                if x * x + y * y < (R - 12) ** 2:
                    pts.append((x, y))
        pts.sort(key=lambda p: p[0] ** 2 + p[1] ** 2)
        k = prog(t, 0.2, dur * 0.75)
        for x, y in pts[: int(len(pts) * k)]:
            d.ellipse((W / 2 + x - 6, cy + y - 6, W / 2 + x + 6, cy + y + 6), fill=(70, 140, 230))
        self.label(d, 1110, "~1,000", "Earths could fit inside", prog(t, 0.4, 0.5))

    def b3(self, img, d, t, dur):
        kb = prog(t, dur * 0.35, 0.8)
        ball_d = 560
        if kb > 0:
            def ball(dr, s):
                D = ball_d * s
                dr.ellipse((0, 0, D - 1, D - 1), fill=(222, 112, 40))
                w = max(2, int(D * 0.012))
                dr.line((D / 2, 0, D / 2, D), fill=(30, 20, 15), width=w)
                dr.line((0, D / 2, D, D / 2), fill=(30, 20, 15), width=w)
                dr.arc((-D * 0.45, D * 0.05, D * 0.45, D * 0.95), -70, 70, fill=(30, 20, 15), width=w)
                dr.arc((D * 0.55, D * 0.05, D * 1.45, D * 0.95), 110, 250, fill=(30, 20, 15), width=w)
            self.put(img, supersample(ball, (ball_d, ball_d)), 640, 680, kb)
            text_c(d, 640, 1000, "Jupiter = basketball", font(SO, 44, 600), self.p["highlight"])
        kg = prog(t, 0.2, 0.5)
        if kg > 0:
            def grape(dr, s):
                D = 52 * s
                dr.ellipse((0, 0, D - 1, D - 1), fill=(126, 176, 76))
                dr.ellipse((D * 0.2, D * 0.15, D * 0.45, D * 0.4), fill=(190, 222, 150))
            self.put(img, supersample(grape, (52, 52)), 190, 930, kg)
            text_c(d, 190, 1000, "Earth = grape", font(SO, 44, 600), self.p["text"])

    def b4(self, img, d, t, dur):
        ow, oh, cy = 640, 360, 640
        k = prog(t, 0.6, 0.8)
        if k > 0:
            def spot(dr, s):
                dr.ellipse((0, 0, ow * s - 1, oh * s - 1), fill=(196, 85, 58))
                dr.ellipse((ow * s * 0.12, oh * s * 0.18, ow * s * 0.88, oh * s * 0.82), fill=(214, 112, 76))
                dr.ellipse((ow * s * 0.3, oh * s * 0.33, ow * s * 0.7, oh * s * 0.67), fill=(228, 140, 100))
            self.put(img, supersample(spot, (ow, oh), scale=2), W / 2, cy, k)
            text_c(d, W / 2, cy - oh / 2 - 80, "Great Red Spot", font(SO, 48, 600), self.p["text"])
        ke = prog(t, dur * 0.3, 0.6)
        if ke > 0:
            e = ow // 2
            x0 = W / 2 - ow / 2
            for j in range(2):
                self.put(img, earth(e), x0 + e / 2 + j * e, 1000, ke)
            for x in (x0, x0 + ow):
                d.line((x, cy, x, 1000), fill=self.p["highlight"], width=3)
        if t > dur * 0.62:
            text_c(d, W / 2, 360 - 80, "Watched for 300+ years", font(SO, 44, 600), self.p["highlight"])

    def b5(self, img, d, t, dur):
        self.put(img, jupiter(420), W / 2, 640, prog(t, 0, 0.6))
        text_c(d, W / 2, 920, "Source: NASA, Jupiter facts", font(SO, 44, 600), self.p["text"])
        text_c(d, W / 2, 990, "science.nasa.gov/jupiter/facts", font(IN, 34, 500), self.p["muted_text"])
