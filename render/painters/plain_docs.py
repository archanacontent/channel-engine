import numpy as np
from PIL import Image, ImageDraw

from render.lib import (W, H, alpha_rect, clamp, ease, font, mix, prog, rgb, supersample, text_c, tw, wrap)
from render.painters.base import Painter

SR = "SourceSerif4[opsz,wght].ttf"
SS = "SourceSans3[wght].ttf"

ORIGINAL = "fatal: refusing to merge unrelated histories"
LINE1 = "Git stopped the merge because these two branches share no commit history."
LINE2 = "If you meant to combine them, run:"
CODE = "git pull --allow-unrelated-histories"


class DocsPainter(Painter):
    tag_font = (SR, 600)
    tag_text_color = "#1F2937"
    caption_style = {"font": SS, "weight": 700, "size": 62, "text": "#1F2937",
                     "colors": {"highlight": "#FFE066"}, "marker": "highlighter",
                     "pill": {"color": "#FFFFFF", "opacity": 0.88}}

    def make_bg(self):
        rng = np.random.default_rng(3)
        base = np.array(self.p["background"], np.int16)
        noise = rng.integers(-5, 6, (H, W, 1))
        arr = np.clip(base + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr, "RGB")
        d = ImageDraw.Draw(img)
        rule = mix(self.p["background"], (180, 170, 150), 0.25)
        for y in range(300, 1260, 64):
            d.line((60, y, W - 60, y), fill=rule, width=1)
        d.line((120, 260, 120, 1280), fill=mix(self.p["background"], self.p["edit"], 0.25), width=2)
        return img

    def logo(self, size):
        ink, red, paper = self.p["text"], self.p["edit"], self.p["background"]

        def draw(d, s):
            S = size * s
            d.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=paper,
                                outline=mix(paper, ink, 0.25), width=max(2, int(S * 0.02)))
            f = font(SR, int(S * 0.42), 700)
            tx = (S - f.getlength("PD")) / 2
            d.text((tx, S * 0.16), "PD", font=f, fill=ink)
            cx, by = S / 2, S * 0.86
            d.line([(cx - S * 0.14, by), (cx, S * 0.68), (cx + S * 0.14, by)], fill=red, width=max(3, int(S * 0.06)),
                   joint="curve")

        return supersample(draw, (size, size))

    def beat(self, img, d, i, t, dur):
        getattr(self, f"b{i}")(img, d, t, dur)

    def original(self, img, d, top, t_hl=0.0, strike=0.0, compact=False, k=1.0):
        x0, x1 = 150, 990
        lab = font(SR, 40 if compact else 48, 600)
        d.text((x0, top), "Git error message", font=lab, fill=self.p["text"])
        f = font(SS, 52 if compact else 60, 600)
        lines = wrap(ORIGINAL, f, x1 - x0 - 80)
        ph = 70 + 74 * len(lines)
        box = (x0, top + 70, x1, top + 70 + ph)
        d.rounded_rectangle(box, radius=18, fill=(241, 236, 225), outline=mix((241, 236, 225), self.p["text"], 0.15),
                            width=2)
        y = top + 105
        for ln in lines:
            if t_hl > 0:
                wv = tw(f, ln) * clamp(t_hl)
                alpha_rect(img, (x0 + 34, y + 14, x0 + 46 + wv, y + 66), self.p["highlight"], 0.85, radius=6)
            d.text((x0 + 40, y), ln, font=f, fill=self.p["text"])
            y += 74
        if strike > 0:
            ws = tw(f, "fatal:")
            yy = top + 105 + 38
            d.line((x0 + 36, yy, x0 + 44 + ws * strike, yy), fill=self.p["edit"], width=7)
        d.text((x0, top + 82 + ph), "Source: git/git (GPL-2.0)", font=font(SS, 28, 400), fill=self.p["muted_text"])
        return top + 70 + ph

    def note(self, d, x, y, text, k):
        if k <= 0:
            return
        f = font(SR, 56, 700)
        d.text((x, y + (1 - k) * 16), text, font=f, fill=mix(self.p["background"], self.p["edit"], k))

    def typed(self, d, x, y, text, f, k, col, maxw):
        n = int(len(text) * clamp(k))
        lines = wrap(text, f, maxw)
        out, used = [], 0
        for ln in lines:
            take = max(0, min(len(ln), n - used))
            out.append(ln[:take])
            used += len(ln) + 1
        lh = int(f.size * 1.32)
        for j, ln in enumerate(out):
            d.text((x, y + j * lh), ln, font=f, fill=col)
        return y + lh * len(lines)

    def b0(self, img, d, t, dur):
        self.original(img, d, 420)

    def b1(self, img, d, t, dur):
        self.original(img, d, 420, t_hl=prog(t, 0.2, 0.9))
        self.note(d, 150, 820, "Why?", prog(t, dur * 0.35, 0.4))
        self.note(d, 150, 920, "What do I do now?", prog(t, dur * 0.6, 0.4))

    def rewrite(self, img, d, t, dur, stage, strike=0.0):
        bottom = self.original(img, d, 290, compact=True, strike=strike)
        y = bottom + 90
        d.text((150, y), "REWRITE", font=font(SS, 34, 700), fill=self.p["edit"])
        y += 60
        f = font(SS, 50, 500)
        k1 = 1.0 if stage > 0 else prog(t, 0.6, dur * 0.55)
        y = self.typed(d, 150, y, LINE1, f, k1, self.p["text"], 840)
        if stage >= 1:
            k2 = 1.0 if stage > 1 else prog(t, 0.5, dur * 0.35)
            y = self.typed(d, 150, y + 26, LINE2, f, k2, self.p["text"], 840)
            kc = 1.0 if stage > 1 else prog(t, 0.5 + dur * 0.35, 0.6)
            if kc > 0:
                cf = font(SS, 42, 700)
                wv = tw(cf, CODE) + 50
                alpha_rect(img, (150, y + 14, 150 + wv * kc, y + 86), self.p["text"], 0.92, radius=14)
                if kc >= 1:
                    d.text((175, y + 26), CODE, font=cf, fill=self.p["background"])

    def b2(self, img, d, t, dur):
        self.rewrite(img, d, t, dur, 0)

    def b3(self, img, d, t, dur):
        self.rewrite(img, d, t, dur, 1)

    def b4(self, img, d, t, dur):
        self.rewrite(img, d, t, dur, 2, strike=prog(t, 0.6, 0.6))

    def b5(self, img, d, t, dur):
        d.text((150, 420), "THE RULE", font=font(SS, 40, 700), fill=self.p["edit"])
        f = font(SR, 84, 600)
        lines = ["A good error", "message names", "the problem and", "the way out."]
        marks = {2: "the problem", 3: "the way out"}
        for j, ln in enumerate(lines):
            k = prog(t, 0.1 + j * 0.2, 0.4)
            y = 500 + j * 118
            if j in marks and t > dur * 0.5:
                wv = tw(f, marks[j]) * prog(t, dur * 0.5 + (j - 2) * 0.4, 0.5)
                alpha_rect(img, (146, y + 30, 154 + wv, y + 104), self.p["highlight"], 0.9, radius=8)
            d.text((150, y + (1 - k) * 14), ln, font=f, fill=mix(self.p["background"], self.p["text"], k))
