from PIL import Image, ImageDraw

from render.lib import (W, H, alpha_rect, arrow, blur_glow, clamp, ease, font, mix, prog,
                        rgb, supersample, text_c, tw, wrap)
from render.painters.base import Painter

SG = "SpaceGrotesk[wght].ttf"
IN = "Inter[opsz,wght].ttf"


class AskedPainter(Painter):
    tag_font = (SG, 700)
    caption_style = {"font": IN, "weight": 600, "size": 64, "text": "#FAFAF7",
                     "colors": {"highlight": "#F59E0B"},
                     "pill": {"color": "#1E1B4B", "opacity": 0.7}}

    def __init__(self, *a):
        super().__init__(*a)
        self.tag_text_color = "#FAFAF7"

    def make_bg(self):
        img = Image.new("RGB", (W, H), self.p["background"])
        glow = blur_glow((W, H), (W - 120, 380, 360), self.p["accent"], radius=180, alpha=38)
        img.paste(glow, (0, 0), glow)
        glow = blur_glow((W, H), (100, 1600, 420), (90, 80, 200), radius=200, alpha=60)
        img.paste(glow, (0, 0), glow)
        return img

    def logo(self, size):
        bg, acc = self.p["background"], self.p["accent"]

        def draw(d, s):
            S = size * s
            d.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=mix(bg, (255, 255, 255), 0.08),
                                outline=acc, width=max(2, int(S * 0.035)))
            cx = S / 2
            # Hook of the question mark.
            r, w = S * 0.17, int(S * 0.085)
            box = (cx - r, S * 0.17, cx + r, S * 0.17 + 2 * r)
            d.arc(box, start=180, end=60, fill=acc, width=w)
            d.line([(cx + r * 0.5, S * 0.17 + r * 1.86), (cx, S * 0.17 + r * 2.35), (cx, S * 0.6)], fill=acc, width=w,
                   joint="curve")
            # The dot is a speech bubble.
            bw, bh, by = S * 0.2, S * 0.13, S * 0.67
            d.rounded_rectangle((cx - bw / 2, by, cx + bw / 2, by + bh), radius=int(bh * 0.35), fill=acc)
            d.polygon([(cx - bw * 0.15, by + bh - 1), (cx - bw * 0.42, by + bh + S * 0.07), (cx + bw * 0.1, by + bh - 1)],
                      fill=acc)

        return supersample(draw, (size, size))

    # ---- beats ----
    def beat(self, img, d, i, t, dur):
        getattr(self, f"b{i}")(img, d, t, dur)

    def search_pill(self, img, d, x, y, w, k, accent=False):
        if k <= 0:
            return
        h = 96
        ww = max(h, w * k)
        fill = (250, 250, 247)
        d.rounded_rectangle((x, y, x + ww, y + h), radius=h // 2, fill=fill,
                            outline=self.p["accent"] if accent else None, width=5 if accent else 0)
        d.ellipse((x + 30, y + 30, x + 62, y + 62), outline=self.p["secondary"], width=5)
        d.line((x + 58, y + 58, x + 70, y + 70), fill=self.p["secondary"], width=5)
        # Text stand-ins: grey bars, no invented query wording.
        bx = x + 96
        while bx + 70 < x + ww - 40:
            seg = min(110, x + ww - 40 - bx)
            d.rounded_rectangle((bx, y + 40, bx + seg - 16, y + 56), radius=8, fill=(203, 207, 222))
            bx += seg

    def b0(self, img, d, t, dur):
        lab = font(IN, 40, 500)
        k1, k2, k3 = prog(t, 0.1, 0.5), prog(t, 0.6, 1.4), prog(t, 1.8, 0.5)
        if k1 > 0:
            d.text((100, 430), "Classic search", font=lab, fill=self.p["muted_text"])
            self.search_pill(img, d, 100, 490, 280, k1)
        if k2 > 0:
            d.text((100, 650), "AI Mode", font=lab, fill=self.p["accent"])
            self.search_pill(img, d, 100, 710, 840, k2, accent=True)
        if k3 > 0:
            big = font(SG, int(200 + 40 * k3), 700)
            text_c(d, W / 2, 880, "3×", big, self.p["accent"])
            text_c(d, W / 2, 1150, "longer queries", font(IN, 44, 500), self.p["text"])

    def b1(self, img, d, t, dur):
        k = prog(t, 0.0, 1.6)
        val = 1.0 * k
        num = f"{val:.1f}B+" if k < 1 else "1B+"
        text_c(d, W / 2, 420, num, font(SG, 260, 700), self.p["text"])
        if t > 0.8:
            text_c(d, W / 2, 750, "monthly AI Mode users", font(IN, 52, 500), self.p["muted_text"])
        if t > 1.4:
            text_c(d, W / 2, 830, "Google, I/O 2026", font(IN, 40, 600), self.p["accent"])
        if t > dur * 0.55:
            k2 = prog(t, dur * 0.55, 0.5)
            alpha_rect(img, (160, 960, 920, 1060), self.p["accent"], 0.15 * k2, radius=50)
            text_c(d, W / 2, 985, "a year after its US launch", font(IN, 40, 500), self.p["text"])

    def b2(self, img, d, t, dur):
        split = prog(t, dur * 0.25, 0.8)
        y0 = 420
        if split < 1:
            self.search_pill(img, d, 110, y0, 860, 1 - 0.0 * split, accent=True)
        xs = [110, 405, 700]
        for j, x in enumerate(xs):
            kj = prog(t, dur * 0.25 + j * 0.15, 0.6)
            if kj <= 0:
                continue
            y = y0 + (640 - y0) * kj
            self.search_pill(img, d, x, y, 270, 1)
        for j, x in enumerate(xs):
            kc = prog(t, dur * 0.5 + j * 0.35, 0.5)
            if kc <= 0:
                continue
            cx = x + 135
            arrow(d, (cx, 750), (cx, 820 + 0 * kc), self.p["muted_text"], width=4)
            top = 840
            d.rounded_rectangle((x, top, x + 270, top + 250), radius=22, fill=(250, 250, 247))
            for r in range(5):
                wv = 210 if r < 4 else 130
                d.rounded_rectangle((x + 30, top + 40 + r * 38, x + 30 + wv, top + 56 + r * 38), radius=8,
                                    fill=(203, 207, 222))
            if kc >= 1 and t > dur * 0.62 + j * 0.35:
                d.rounded_rectangle((x + 60, top - 26, x + 210, top + 26), radius=26, fill=self.p["accent"])
                text_c(d, cx, top - 18, "Cited", font(IN, 32, 700), self.p["background"])
        if split <= 0:
            text_c(d, W / 2, 560, "one long question", font(IN, 38, 500), self.p["muted_text"])

    def card(self, d, box, title, body, dark, k):
        x0, y0, x1, y1 = box
        fill = mix(self.p["background"], (255, 255, 255), 0.1) if dark else (250, 250, 247)
        d.rounded_rectangle(box, radius=28, fill=fill)
        tf = font(IN, 34, 700)
        d.text((x0 + 40, y0 + 34), title, font=tf, fill=self.p["muted_text"] if dark else self.p["accent"])
        bf = font(IN, 40, 400)
        col = self.p["muted_text"] if dark else self.p["background"]
        lines = wrap(body, bf, x1 - x0 - 80)
        shown = int(len(lines) * clamp(k * 1.2)) or (1 if k > 0 else 0)
        for j, ln in enumerate(lines[:shown]):
            d.text((x0 + 40, y0 + 96 + j * 54), ln, font=bf, fill=col)

    def b3(self, img, d, t, dur):
        before = "It's basically the opposite of the usual data pipeline, and as we covered earlier, more and more teams are starting to use it…"
        after = "Reverse ETL is the process of copying data from a central warehouse, such as Snowflake or BigQuery, back into the operational tools teams use every day…"
        self.card(d, (80, 300, 1000, 640), "BEFORE", before, True, prog(t, 0.0, 0.8))
        if t > dur * 0.12:
            self.card(d, (80, 680, 1000, 1110), "AFTER", after, False, prog(t, dur * 0.12, 1.0))
        checks = [("Answers first", 0.25), ("Names the subject", 0.5), ("Stands alone", 0.75)]
        cf = font(IN, 32, 700)
        widths = [tw(cf, "✓ " + c[0]) + 40 for c in checks]
        x = 80 + (920 - (sum(widths) + 12 * (len(widths) - 1))) / 2
        for (label, at), wdt in zip(checks, widths):
            if t > dur * at:
                txt = "✓ " + label
                d.rounded_rectangle((x, 1150, x + wdt, 1214), radius=32, fill=self.p["accent"])
                d.text((x + 20, 1162), txt, font=cf, fill=self.p["background"])
            x += wdt + 12
        src = font(IN, 26, 500)
        d.text((80, 1236), "Example: The Citable Passage Standard, Asked", font=src, fill=self.p["muted_text"])

    def b4(self, img, d, t, dur):
        k = prog(t, 0, 0.6)
        size = int(220 + 80 * k)
        lg = self.logo_big.resize((size, size))
        img.paste(lg, ((W - size) // 2, 560 - size // 2), lg)
        text_c(d, W / 2, 760, "Asked", font(SG, 130, 700), self.p["text"])
        if t > 0.8:
            text_c(d, W / 2, 940, "Free AEO and GEO question finder", font(IN, 44, 500), self.p["muted_text"])
        if t > 1.4:
            text_c(d, W / 2, 1020, "Link in the description", font(IN, 44, 700), self.p["accent"])
