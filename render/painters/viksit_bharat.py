"""Viksit Bharat On Record: one look per Short, picked from rotating parts.

Each episode carries a `look` (set by pipeline/looks.py):
  palette  one of PALETTES, built from the logo's blue, saffron and cream plus India green
  motion   one of MOTIONS, the moving background layer
  hook     one of the hook styles for the first beat, which doubles as the thumbnail frame

Fixed on every Short: the logo and name top left, the source line under it,
Sora for numbers and headlines, Inter for captions, and the end frame.
"""
import math
import random

from PIL import Image, ImageDraw

from render.lib import H, W, alpha_rect, clamp, ease, font, rgb, text_c, tw
from render.painters.base import Painter
from render.scenes import F, fit, lh

SO = "Sora[wght].ttf"
IN = "Inter[opsz,wght].ttf"

BLUE, SAFFRON, CREAM, GREEN = "#004AAD", "#FF751F", "#EFF5CD", "#138808"

PALETTES = {
    "saffron_on_blue": dict(family="blue", background=BLUE, text="#FFFFFF", accent=SAFFRON,
                            highlight="#FFC08F", muted_text="#C9D8F2", pill="#002F70"),
    "blue_on_saffron": dict(family="saffron", background=SAFFRON, text="#0B1F3A", accent="#003A8C",
                            highlight="#FFFFFF", muted_text="#5A2608", pill="#FFE3CF"),
    "green_on_cream": dict(family="cream", background=CREAM, text="#12301A", accent="#0F7A06",
                           highlight="#E0600F", muted_text="#4F5E45", pill="#FFFFFF"),
    "cream_on_green": dict(family="green", background="#0E5F07", text=CREAM, accent="#FF8A3D",
                           highlight="#FFFFFF", muted_text="#BFD9B5", pill="#0A4205"),
    "saffron_on_charcoal": dict(family="charcoal", background="#1C1C1C", text="#F5F5F5", accent=SAFFRON,
                                highlight="#5B9BFF", muted_text="#A5A5A5", pill="#000000"),
    "blue_on_cream": dict(family="cream", background=CREAM, text="#0B1F3A", accent=BLUE,
                          highlight="#D9560A", muted_text="#55606E", pill="#FFFFFF"),
    "cream_on_navy": dict(family="navy", background="#0B1F3A", text=CREAM, accent=SAFFRON,
                          highlight="#3FC94A", muted_text="#9FB0C8", pill="#06142A"),
    "tricolour": dict(family="white", background="#FFFFFF", text="#0B1F3A", accent=BLUE,
                      highlight="#E0600F", muted_text="#5A6575", pill="#F1F3F7", bands=True),
}
MOTIONS = ["sweep", "rings", "grid", "ribbon", "rays", "bars", "tiles", "waves"]
HOOKS_FOR = {
    "stat": ["stat_punch", "stat_ring", "stat_ribbon"],
    "compare": ["contrast_split", "contrast_stack"],
    "headline": ["myth_stamp", "challenge"],
}
OY = 0  # hook layouts sit a little lower so the first frame works as a thumbnail
DEFAULT_LOOK = {"palette": "saffron_on_blue", "motion": "ribbon", "hook": "stat_punch"}


def rgba(c, a):
    return tuple(rgb(c)) + (int(a),) if isinstance(c, str) else tuple(c) + (int(a),)


class VBPainter(Painter):
    tag_font = (SO, 700)

    def __init__(self, brand, episode, timing):
        self.look = dict(DEFAULT_LOOK, **(episode.get("look") or {}))
        pal = PALETTES[self.look["palette"]]
        self.pal = pal
        brand = dict(brand, palette={k: pal[k] for k in ("background", "text", "accent", "highlight",
                                                          "muted_text")})
        super().__init__(brand, episode, timing)
        self.tag_text_color = pal["text"]
        self.caption_style = {"font": IN, "weight": 700, "size": 60, "text": pal["text"],
                              "colors": {"numbers": pal["accent"], "highlight": pal["accent"]},
                              "pill": {"color": pal["pill"], "opacity": 0.92}}
        self.rng = random.Random(episode.get("record_id", "vb"))
        self.seed = self.rng.random() * 10

    # ---------- background ----------
    def make_bg(self):
        img = Image.new("RGB", (W, H), self.p["background"])
        if self.pal.get("bands"):
            d = ImageDraw.Draw(img)
            d.rectangle((0, 0, W, 220), fill=rgb("#FF9933"))
            d.rectangle((0, H - 220, W, H), fill=rgb(GREEN))
        return img

    def background(self, t):
        img = self.bg.copy()
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        getattr(self, "m_" + self.look["motion"])(ImageDraw.Draw(layer), t)
        img.paste(layer, (0, 0), layer)
        return img

    def _a(self, light_alpha, dark_alpha):
        return light_alpha if sum(self.p["background"]) > 600 else dark_alpha

    def m_sweep(self, d, t):
        c = rgba(self.p["accent"], self._a(16, 20))
        off = (t * 45) % 260
        for x in range(-H, W + 260, 260):
            x0 = x + off
            d.polygon([(x0, 0), (x0 + 110, 0), (x0 + 110 + H * 0.55, H), (x0 + H * 0.55, H)], fill=c)

    def m_rings(self, d, t):
        cx, cy = W + 60, H * 0.82
        for k in range(9):
            r = ((t * 70 + k * 210) % (9 * 210))
            a = clamp(1 - r / (9 * 210)) * self._a(70, 80)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=rgba(self.p["accent"], a), width=7)

    def m_grid(self, d, t):
        c = rgba(self.p["muted_text"], self._a(70, 60))
        ox, oy = (t * 14) % 72, (t * 9) % 72
        for y in range(-72, H + 72, 72):
            for x in range(-72, W + 72, 72):
                wob = 2 + 2 * math.sin(t * 1.6 + (x + y) * 0.01 + self.seed)
                d.ellipse((x + ox - wob, y + oy - wob, x + ox + wob, y + oy + wob), fill=c)

    def m_ribbon(self, d, t):
        base = H - 330 if not self.pal.get("bands") else H - 420
        cols = [rgb("#FF9933"), rgb("#FFFFFF"), rgb(GREEN)]
        for j, col in enumerate(cols):
            pts_top, pts_bot = [], []
            for x in range(-20, W + 40, 20):
                y = base + j * 34 + 46 * math.sin(x / 210 + t * 1.3 + self.seed) + 18 * math.sin(x / 90 - t)
                pts_top.append((x, y))
                pts_bot.append((x, y + 36))
            d.polygon(pts_top + pts_bot[::-1], fill=col + (235,))

    def m_rays(self, d, t):
        cx, cy = W / 2, -260
        c = rgba(self.p["highlight"], self._a(22, 18))
        for k in range(18):
            a0 = math.radians(k * 20 + t * 4)
            a1 = a0 + math.radians(8)
            R = H * 1.4
            d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)),
                       (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=c)

    def m_bars(self, d, t):
        n = 12
        bw = W / n
        bottom = H - (220 if self.pal.get("bands") else 0)
        for k in range(n):
            h = 160 + 120 * (0.5 + 0.5 * math.sin(k * 1.7 + self.seed)) + 40 * math.sin(t * 1.4 + k)
            h *= ease(min(1.0, t / 1.2 + 0.4))
            d.rectangle((k * bw + 8, bottom - h, (k + 1) * bw - 8, bottom),
                        fill=rgba(self.p["accent"], self._a(48, 56)))

    def m_tiles(self, d, t):
        s = 270
        for j in range(8):
            for i in range(4):
                v = 0.5 + 0.5 * math.sin(t * 0.9 + i * 1.3 + j * 0.7 + self.seed * (i + 1))
                d.rectangle((i * s + 6, j * s + 6, (i + 1) * s - 6, (j + 1) * s - 6),
                            fill=rgba(self.p["accent"], self._a(26, 30) * v))

    def m_waves(self, d, t):
        for k in range(7):
            y0 = 260 + k * 250
            pts = [(x, y0 + 34 * math.sin(x / 160 + t * 1.1 + k * 0.8 + self.seed)) for x in range(-20, W + 40, 16)]
            d.line(pts, fill=rgba(self.p["highlight"], self._a(90, 70)), width=5)

    # ---------- fixed brand pieces ----------
    def logo(self, size):
        return Image.new("RGBA", (size, size), rgb(BLUE) + (255,))

    def tag(self, img, d):
        top = 96
        img.paste(self.logo_small, (56, top), self.logo_small)
        d.text((144, top + 2), self.brand["name"], font=font(SO, 34, 700), fill=rgb(self.pal["text"]))
        src = self.ep.get("source_label")
        if src:
            d.text((144, top + 44), "Source: " + src, font=font(IN, 26, 600), fill=rgb(self.pal["muted_text"]))

    # ---------- hook: the first beat, also the thumbnail frame ----------
    def scene_beat(self, img, d, i, t, dur):
        if i == 0:
            sc = self.ep["beats"][0].get("scene") or {}
            hook = self.look["hook"]
            fam = next((k for k, v in HOOKS_FOR.items() if hook in v), "headline")
            if fam == "stat" and sc.get("type") != "stat":
                hook = "myth_stamp" if sc.get("type") != "compare" else "contrast_split"
            if fam == "compare" and sc.get("type") != "compare":
                hook = "stat_punch" if sc.get("type") == "stat" else "challenge"
            if fam == "headline" and sc.get("type") in ("stat", "compare"):
                hook = "stat_punch" if sc.get("type") == "stat" else "contrast_split"
            return getattr(self, "h_" + hook)(img, d, sc, t, dur, self.ep["beats"][0])
        return super().scene_beat(img, d, i, t, dur)

    def chip(self, d, cx, y, text, fill, ink, size=32):
        f = font(IN, size, 700)
        w = tw(f, text) + 48
        d.rounded_rectangle((cx - w / 2, y, cx + w / 2, y + size + 30), radius=(size + 30) // 2, fill=fill)
        text_c(d, cx, y + 13, text, f, ink)

    def released(self, d, y):
        if self.ep.get("released"):
            self.chip(d, W / 2, y, "Released " + self.ep["released"], rgb(self.pal["pill"]),
                      rgb(self.pal["text"]), 30)

    def kicker(self, d, y):
        """Series chip with the release date right under it: every hook carries its date."""
        self.chip(d, W / 2, y, self.ep.get("series", "").upper(), self.p["accent"],
                  rgb("#FFFFFF") if sum(self.p["accent"]) < 450 else self.p["background"], 34)
        self.released(d, y + 78)

    def pulse(self, t):
        return 1 + 0.035 * math.sin(min(t, 3.0) * 2.2)

    def h_stat_punch(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        self.kicker(d, 330 + OY)
        f, _ = fit(sc.get("value", ""), th["head"], int(270 * self.pulse(t)), 120, 960, 1)
        text_c(d, W / 2, 600 + OY, str(sc.get("value", "")), f, th["accent"])
        lf, lines = fit(sc.get("label", ""), th["head"], 64, 42, 900, 3)
        y = 600 + OY + f.size + 60
        for j, ln in enumerate(lines):
            text_c(d, W / 2, y + j * lh(lf), ln, lf, th["text"])

    def h_stat_ring(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        self.kicker(d, 330 + OY)
        cx, cy, R = W / 2, 760 + OY, int(235 * self.pulse(t))
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=th["accent"], width=22)
        d.arc((cx - R - 34, cy - R - 34, cx + R + 34, cy + R + 34), -90, -90 + 360 * clamp(0.35 + t / 3),
              fill=th["text"], width=7)
        f, _ = fit(sc.get("value", ""), th["head"], 170, 80, 2 * R - 80, 1)
        text_c(d, cx, cy - f.size * 0.62, str(sc.get("value", "")), f, th["text"])
        lf, lines = fit(sc.get("label", ""), th["head"], 54, 38, 900, 2)
        for j, ln in enumerate(lines):
            text_c(d, W / 2, cy + 235 + 60 + j * lh(lf), ln, lf, th["text"])

    def h_stat_ribbon(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        self.kicker(d, 330 + OY)
        lf, lines = fit(sc.get("label", ""), th["head"], 60, 40, 900, 2)
        y = 600 + OY
        for j, ln in enumerate(lines):
            text_c(d, W / 2, y + j * lh(lf), ln, lf, th["text"])
        band_y = y + len(lines) * lh(lf) + 40
        sk = 40
        d.polygon([(0, band_y + sk), (W, band_y), (W, band_y + 300), (0, band_y + 300 + sk)], fill=th["accent"])
        f, _ = fit(sc.get("value", ""), th["head"], int(220 * self.pulse(t)), 100, 960, 1)
        ink = (255, 255, 255) if sum(th["accent"]) < 450 else th["bg"]
        text_c(d, W / 2, band_y + 150 + sk / 2 - f.size * 0.62, str(sc.get("value", "")), f, ink)

    def h_contrast_split(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        self.kicker(d, 330 + OY)
        halves = [(sc.get("left_label", ""), sc.get("left_text", ""), th["muted"], 590 + OY),
                  (sc.get("right_label", ""), sc.get("right_text", ""), th["accent"], 930 + OY)]
        for lab, txt, col, y in halves:
            text_c(d, W / 2, y, str(lab).upper(), F(th["bold"], 44), th["text"])
            f, lines = fit(txt, th["head"], int(140 * (self.pulse(t) if col == th["accent"] else 1)), 60, 940, 1)
            for j, ln in enumerate(lines):
                text_c(d, W / 2, y + 62 + j * lh(f), ln, f, col)
        ar = 850 + OY
        d.polygon([(W / 2 - 34, ar - 24), (W / 2 + 34, ar - 24), (W / 2, ar + 20)], fill=th["text"])

    def h_contrast_stack(self, img, d, sc, t, dur, beat, bare=False):
        th = self.scene_theme()
        top = 470 if bare else 600 + OY
        if not bare:
            self.kicker(d, 330 + OY)
        cols = [(sc.get("left_label", ""), sc.get("left_text", ""), th["muted"], W * 0.27),
                (sc.get("right_label", ""), sc.get("right_text", ""), th["accent"], W * 0.73)]
        d.line((W / 2, top, W / 2, top + 440), fill=th["panel_line"], width=4)
        for lab, txt, col, cx in cols:
            text_c(d, cx, top + 20, str(lab).upper(), F(th["bold"], 46), th["text"])
            f, lines = fit(txt, th["head"], 130, 54, 440, 3)
            for j, ln in enumerate(lines):
                text_c(d, cx, top + 110 + j * lh(f), ln, f, col)

    def h_myth_stamp(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        self.chip(d, W / 2, 330 + OY, "MYTH", th["text"], th["bg"], 40)
        self.released(d, 330 + OY + 84)
        f, lines = fit(sc.get("text") or beat["caption"], th["head"], 116, 64, 920, 3)
        y = 620 + OY
        for j, ln in enumerate(lines):
            text_c(d, W / 2, y + j * lh(f), ln, f, th["text"])
        # stamped across the myth, complete from the first frame so the thumbnail shows it
        stamp = Image.new("RGBA", (600, 180), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp)
        sd.rounded_rectangle((8, 8, 592, 172), radius=24, outline=th["accent"] + (255,), width=13)
        text_c(sd, 300, 40, "CHECKED", font(SO, 90, 800), th["accent"] + (255,))
        s = 1.0 + 0.25 * (1 - ease(clamp(t / 0.35))) if t > 0.05 else 1.0
        stamp = stamp.resize((int(600 * s), int(180 * s))).rotate(-11, expand=True, resample=Image.BICUBIC)
        sy = y + len(lines) * lh(f) - stamp.height * 0.12
        img.paste(stamp, (int(W / 2 - stamp.width / 2), int(sy)), stamp)

    def h_challenge(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        self.kicker(d, 330 + OY)
        f, lines = fit(sc.get("text") or beat["caption"], th["head"], 88, 52, 820, 4)
        bh = len(lines) * lh(f) + 110
        y0 = 600 + OY
        alpha_rect(img, (70, y0, W - 70, y0 + bh), th["panel"], 0.96, radius=48)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((70, y0, W - 70, y0 + bh), radius=48, outline=th["accent"], width=10)
        d.polygon([(190, y0 + bh - 6), (290, y0 + bh - 6), (170, y0 + bh + 80)], fill=th["accent"])
        for j, ln in enumerate(lines):
            text_c(d, W / 2, y0 + 55 + j * lh(f), ln, f, th["text"])

    def sc_compare(self, img, d, sc, t, dur, beat):
        """Short figures side by side get the big two-column layout; long text keeps the shared panels."""
        if max(len(str(sc.get("left_text", ""))), len(str(sc.get("right_text", "")))) > 16:
            return super().sc_compare(img, d, sc, t, dur, beat)
        return self.h_contrast_stack(img, d, sc, t, dur, beat, bare=True)
