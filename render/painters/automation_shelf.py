import math

from PIL import Image, ImageDraw

from render.lib import (W, H, alpha_rect, blur_glow, clamp, ease, font, mix, prog, rgb,
                        supersample, text_c, tw, wrap)
from render.painters.base import Painter

MR = "Manrope[wght].ttf"
JB = "JetBrainsMono[wght].ttf"


class ShelfPainter(Painter):
    tag_font = (MR, 700)
    caption_style = {"font": MR, "weight": 700, "size": 62, "text": "#FFFFFF",
                     "colors": {"highlight": "#14B8A6"}, "marker": "underline", "shadow": "#05070B"}

    def make_bg(self):
        img = Image.new("RGB", (W, H), self.p["background"])
        d = ImageDraw.Draw(img)
        dot = mix(self.p["background"], (255, 255, 255), 0.09)
        for y in range(20, H, 48):
            for x in range(20, W, 48):
                d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=dot)
        glow = blur_glow((W, H), (540, 760, 380), self.p["accent"], radius=200, alpha=26)
        img.paste(glow, (0, 0), glow)
        return img

    def logo(self, size):
        acc, line = self.p["accent"], self.p["line"]

        def draw(d, s):
            S = size * s
            d.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=(17, 24, 39),
                                outline=mix((17, 24, 39), (255, 255, 255), 0.25), width=max(2, int(S * 0.02)))
            bw, gap, base = S * 0.19, S * 0.06, S * 0.66
            x0 = (S - (3 * bw + 2 * gap)) / 2
            for j in range(3):
                x = x0 + j * (bw + gap)
                if j == 1:
                    d.polygon([(x, base - bw * 1.25), (x, base), (x + bw, base - bw * 0.625)], fill=acc)
                else:
                    d.rounded_rectangle((x, base - bw, x + bw, base), radius=int(S * 0.025), fill=acc)
            d.rounded_rectangle((S * 0.16, base + S * 0.04, S * 0.84, base + S * 0.085), radius=int(S * 0.02),
                                fill=line)

        return supersample(draw, (size, size))

    def beat(self, img, d, i, t, dur):
        getattr(self, f"b{i}")(img, d, t, dur)

    def node(self, img, d, y, title, sub, lit, k):
        if k <= 0:
            return
        x0, x1, h = 150, 930, 180
        yy = y + (1 - k) * 30
        if lit > 0:
            alpha_rect(img, (x0 - 14, yy - 14, x1 + 14, yy + h + 14), self.p["accent"], 0.18 * lit, radius=40)
        d.rounded_rectangle((x0, yy, x1, yy + h), radius=30, fill=(28, 37, 54),
                            outline=mix((75, 85, 99), self.p["accent"], lit), width=4 + int(3 * lit))
        d.rounded_rectangle((x0 + 30, yy + 40, x0 + 130, yy + 140), radius=20,
                            fill=mix((55, 65, 81), self.p["accent"], lit))
        d.text((x0 + 160, yy + 42), title, font=font(JB, 42, 600), fill=self.p["text"])
        d.text((x0 + 160, yy + 104), sub, font=font(JB, 30, 400), fill=self.p["muted_text"])

    def icon_rss(self, d, x, y, col):
        d.ellipse((x, y + 58, x + 16, y + 74), fill=col)
        for r in (34, 58):
            d.arc((x - r + 8, y + 66 - r, x + r + 8, y + 66 + r), 270, 360, fill=col, width=9)

    def icon_sheet(self, d, x, y, col):
        d.rounded_rectangle((x, y, x + 64, y + 76), radius=8, outline=col, width=6)
        for yy in (y + 26, y + 48):
            d.line((x + 6, yy, x + 58, yy), fill=col, width=5)
        d.line((x + 30, y + 6, x + 30, y + 70), fill=col, width=5)

    def flow(self, img, d, t, dur, lit1, lit2, ys=(420, 790)):
        k1, k2 = prog(t, 0.0, 0.5), prog(t, 0.0, 0.5)
        self.node(img, d, ys[0], "RSS Feed Trigger", "New Competitor Post", lit1, k1)
        self.node(img, d, ys[1], "Google Sheets", "Log Post to Sheet", lit2, k2)
        self.icon_rss(d, 192, ys[0] + 52, (255, 255, 255))
        self.icon_sheet(d, 198, ys[1] + 52, (255, 255, 255))
        cx, a, b = 540, ys[0] + 180, ys[1]
        d.line((cx, a, cx, b), fill=self.p["line"], width=5)
        ph = (t * 0.7) % 1
        py = a + (b - a) * ph
        d.ellipse((cx - 13, py - 13, cx + 13, py + 13), fill=self.p["accent"])

    def b0(self, img, d, t, dur):
        hf = font(MR, 96, 800)
        lines = wrap("Still checking competitor blogs by hand?", hf, 900)
        for j, ln in enumerate(lines):
            k = prog(t, 0.1 + j * 0.15, 0.5)
            d.text((90, 340 + j * 112 + (1 - k) * 20), ln, font=hf,
                   fill=mix(self.p["background"], self.p["text"], k))
        base = 340 + len(lines) * 112 + 70
        for j in range(4):
            k = prog(t, 0.6 + j * 0.25, 0.4)
            if k <= 0:
                continue
            x, y = 110 + j * 46, base + j * 60
            d.rounded_rectangle((x, y, x + 760, y + 330 - j * 20), radius=24, fill=(28, 37, 54),
                                outline=(75, 85, 99), width=3)
            d.rounded_rectangle((x + 24, y + 22, x + 220, y + 58), radius=18, fill=(55, 65, 81))
            d.text((x + 44, y + 25), "blog", font=font(JB, 26, 500), fill=self.p["muted_text"])
            for r in range(3):
                d.rounded_rectangle((x + 30, y + 100 + r * 46, x + 500 - r * 90, y + 118 + r * 46), radius=9,
                                    fill=(55, 65, 81))

    def b1(self, img, d, t, dur):
        self.flow(img, d, t, dur, 0, 0)
        text_c(d, W / 2, 1050, "2 steps · runs on its own", font(JB, 38, 500), self.p["line"])

    def b2(self, img, d, t, dur):
        lit = prog(t, 0.6, 0.5)
        self.flow(img, d, t, dur, lit, 0)
        if lit > 0:
            bf = font(JB, 34, 600)
            txt = "every hour"
            wdt = tw(bf, txt) + 48
            x, y = 930 - wdt, 360
            d.rounded_rectangle((x, y, x + wdt, y + 60), radius=30, fill=self.p["accent"])
            d.text((x + 24, y + 10), txt, font=bf, fill=self.p["background"])
            r = 120 + 60 * ((t * 0.8) % 1)
            a = 1 - ((t * 0.8) % 1)
            d.ellipse((250 - r, 510 - r, 250 + r, 510 + r), outline=mix(self.p["background"], self.p["accent"], a * 0.6),
                      width=3)

    def b3(self, img, d, t, dur):
        self.flow(img, d, t, dur, 0.35, prog(t, 0.4, 0.5), ys=(330, 600))
        x0, x1, top = 110, 970, 860
        cols = ["Date", "Title", "Link", "Summary"]
        cw = [170, 230, 200, 260]
        hf = font(JB, 30, 600)
        kh = prog(t, 0.8, 0.4)
        if kh <= 0:
            return
        d.rounded_rectangle((x0, top, x1, top + 360), radius=22, fill=(28, 37, 54), outline=(75, 85, 99), width=3)
        x = x0
        for c, w in zip(cols, cw):
            d.text((x + 22, top + 22), c, font=hf, fill=self.p["accent"])
            x += w
            if x < x1 - 10:
                d.line((x, top, x, top + 360), fill=(55, 65, 81), width=2)
        d.line((x0, top + 76, x1, top + 76), fill=(75, 85, 99), width=2)
        for r in range(3):
            k = prog(t, 1.4 + r * 0.9, 0.4)
            if k <= 0:
                continue
            y = top + 96 + r * 88
            x = x0
            for w in cw:
                d.rounded_rectangle((x + 22, y + 18, x + 22 + (w - 50) * k, y + 40), radius=10,
                                    fill=mix((55, 65, 81), self.p["line"], 0.25 if r == 2 else 0))
                x += w
        d.text((x0, top + 380), "Sheet: Competitor Content Log", font=font(JB, 28, 500), fill=self.p["muted_text"])

    def b4(self, img, d, t, dur):
        k = prog(t, 0, 0.6)
        size = int(220 + 80 * k)
        lg = self.logo_big.resize((size, size))
        img.paste(lg, ((W - size) // 2, 560 - size // 2), lg)
        text_c(d, W / 2, 760, "Free template", font(MR, 96, 800), self.p["text"])
        chips = [("Validated in n8n", 0.6), ("Link in description", 1.2)]
        cf = font(JB, 36, 600)
        y = 930
        for label, at in chips:
            if t > at:
                wdt = tw(cf, label) + 60
                x = (W - wdt) / 2
                d.rounded_rectangle((x, y, x + wdt, y + 76), radius=38, outline=self.p["accent"], width=4)
                d.text((x + 30, y + 16), label, font=cf, fill=self.p["line"])
            y += 100
