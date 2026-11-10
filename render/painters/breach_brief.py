import numpy as np
from PIL import Image, ImageDraw

from render.lib import (W, H, alpha_rect, arrow, blur_glow, clamp, ease, font, mix, prog, rgb,
                        supersample, text_c, tw, wrap)
from render.painters.base import Painter

PB = "IBMPlexSansCondensed-Bold.ttf"
PS = "IBMPlexSansCondensed-SemiBold.ttf"
PM = "IBMPlexMono-Medium.ttf"


class BreachPainter(Painter):
    tag_font = (PB, None)
    caption_style = {"font": PS, "size": 64, "text": "#F0F3F6",
                     "colors": {"threat": "#E5484D", "fix": "#3DD68C"},
                     "pill": {"color": "#05080C", "opacity": 0.78}}

    def __init__(self, *a):
        super().__init__(*a)
        self.tag_text_color = "#F0F3F6"
        self.p.setdefault("muted_text", self.p["secondary"])

    def make_bg(self):
        # A larger network layer that drifts slowly behind every frame.
        BW, BH = W + 240, H + 240
        img = Image.new("RGB", (BW, BH), self.p["background"])
        d = ImageDraw.Draw(img)
        rng = np.random.default_rng(11)
        pts = rng.uniform(0, 1, (110, 2)) * [BW, BH]
        line = mix(self.p["background"], self.p["secondary"], 0.16)
        dot = mix(self.p["background"], self.p["secondary"], 0.4)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                if np.hypot(*(pts[i] - pts[j])) < 210:
                    d.line((*pts[i], *pts[j]), fill=line, width=2)
        for x, y in pts:
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=dot)
        glow = blur_glow((BW, BH), (BW - 160, 260, 300), self.p["threat"], radius=200, alpha=30)
        img.paste(glow, (0, 0), glow)
        return img

    def background(self, t):
        ox = int(120 + 100 * np.sin(t * 0.05))
        oy = int(120 + 110 * np.cos(t * 0.04))
        return self.bg.crop((ox, oy, ox + W, oy + H))

    def logo(self, size):
        red, ink = self.p["threat"], self.p["text"]

        def draw(d, s):
            S = size * s
            d.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=(11, 15, 20))
            cx, top, bot, w = S / 2, S * 0.17, S * 0.85, S * 0.3
            shield = [(cx, top), (cx + w, top + S * 0.09), (cx + w, S * 0.5), (cx, bot), (cx - w, S * 0.5),
                      (cx - w, top + S * 0.09)]
            d.polygon(shield, outline=ink, width=max(3, int(S * 0.05)))
            d.rectangle((cx - w * 1.35, S * 0.47, cx + w * 1.35, S * 0.55), fill=red)

        return supersample(draw, (size, size))

    def beat(self, img, d, i, t, dur):
        getattr(self, f"b{i}")(img, d, t, dur)

    def panel(self, img, box, k=1.0):
        alpha_rect(img, box, (18, 24, 33), 0.92 * k, radius=26)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(box, radius=26, outline=mix((11, 15, 20), self.p["secondary"], 0.5 * k), width=2)

    def b0(self, img, d, t, dur):
        k = prog(t, 0.1, 0.4)
        tf = font(PB, 40)
        txt = "ACTIVELY EXPLOITED"
        wdt = tw(tf, txt) + 56
        d.rounded_rectangle((90, 430, 90 + wdt * k, 500), radius=12, fill=self.p["threat"])
        if k >= 1:
            d.text((118, 439), txt, font=tf, fill=(11, 15, 20))
        k2 = prog(t, 0.5, 0.5)
        d.text((86, 540 + (1 - k2) * 30), "OpenSSH", font=font(PB, 190), fill=mix(self.p["background"], self.p["text"], k2))
        k3 = prog(t, 1.0, 0.5)
        d.text((92, 780), "authentication bypass", font=font(PS, 76), fill=mix(self.p["background"], self.p["secondary"], k3))
        k4 = prog(t, 1.4, 0.8)
        d.rectangle((92, 900, 92 + 760 * k4, 916), fill=self.p["threat"])
        if t > 2.0:
            d.text((92, 950), "Source: CISA Known Exploited Vulnerabilities catalog", font=font(PS, 34),
                   fill=self.p["secondary"])

    def b1(self, img, d, t, dur):
        self.panel(img, (80, 360, 1000, 1150), prog(t, 0, 0.4))
        rows = [("CVE ID", "CVE-2026-123158", self.p["threat"]),
                ("Product", "OpenBSD OpenSSH", self.p["text"]),
                ("Flaw", "Authentication bypass", self.p["text"]),
                ("Added to KEV", "2026-11-09", self.p["text"]),
                ("Federal due date", "2026-11-12", self.p["threat"])]
        lf, vf = font(PS, 34), font(PM, 50)
        for j, (lab, val, col) in enumerate(rows):
            k = prog(t, 0.3 + j * 0.35, 0.4)
            if k <= 0:
                continue
            y = 410 + j * 146
            d.text((130, y), lab.upper(), font=lf, fill=self.p["secondary"])
            shown = val[: max(1, int(len(val) * k))]
            d.text((130, y + 46), shown, font=vf, fill=col)
            if j < len(rows) - 1:
                d.line((130, y + 126, 950, y + 126), fill=(36, 44, 56), width=2)

    def box(self, img, d, y, text, k, col=None, mono=False, fill=None):
        if k <= 0:
            return
        f = font(PM, 44) if mono else font(PS, 48)
        x0, x1 = 120, 960
        h = 128
        yy = y + (1 - k) * 24
        if fill:
            alpha_rect(img, (x0, yy, x1, yy + h), fill, 0.22, radius=22)
        d.rounded_rectangle((x0, yy, x1, yy + h), radius=22, outline=col or (70, 80, 92), width=4 if col else 3)
        lines = wrap(text, f, x1 - x0 - 60)
        lh = 54
        ty = yy + (h - lh * len(lines)) / 2 - 4
        for j, ln in enumerate(lines):
            text_c(d, (x0 + x1) / 2, ty + j * lh, ln, f, col or self.p["text"])

    def b2(self, img, d, t, dur):
        steps = [(330, "Server checks passwords without PAM", None, False, None),
                 (530, "Password longer than 256 bytes", None, False, None),
                 (730, "crypt() returns  *", None, True, None),
                 (930, "Accounts with no password store  *", None, False, None),
                 (1130, "*  =  *    login accepted", self.p["threat"], True, self.p["threat"])]
        ats = [0.0, 0.18, 0.36, 0.55, 0.8]
        for j, ((y, txt, col, mono, fill), at) in enumerate(zip(steps, ats)):
            k = prog(t, dur * at, 0.5)
            self.box(img, d, y, txt, k, col, mono, fill)
            if j and k > 0:
                arrow(d, (540, y - 66), (540, y - 6), self.p["secondary"], width=4, head=14)
        d.text((120, 1268), "How it works: Alpine Linux advisory, Nov 5, 2026", font=font(PS, 28), fill=self.p["secondary"])

    def b3(self, img, d, t, dur):
        d.text((100, 420), "EXPLOITABLE WHEN", font=font(PB, 44), fill=self.p["secondary"])
        rows = ["PasswordAuthentication yes (default)",
                "sshd without PAM, or UsePAM no",
                "An account with no password, like root"]
        for j, r in enumerate(rows):
            k = prog(t, 0.2 + j * 0.45, 0.4)
            if k <= 0:
                continue
            y = 520 + j * 170
            self.panel(img, (100, y, 980, y + 136), k)
            d.ellipse((136, y + 52, 168, y + 84), fill=self.p["threat"])
            f = font(PM, 33) if j < 2 else font(PS, 44)
            for li, ln in enumerate(wrap(r, f, 760)):
                d.text((196, y + 44 + li * 46 - (23 if len(wrap(r, f, 760)) > 1 else 0)), ln, font=f, fill=self.p["text"])

    def b4(self, img, d, t, dur):
        d.text((100, 380), "WHAT TO DO", font=font(PB, 48), fill=self.p["fix"])
        rows = [("1", "Upgrade openssh", 0.0), ("2", "Restart sshd", 0.25)]
        for num, txt, at in rows:
            k = prog(t, dur * at, 0.4)
            if k <= 0:
                continue
            y = 470 + int(num) * 0 + (0 if num == "1" else 170)
            self.panel(img, (100, y, 980, y + 140), k)
            d.ellipse((132, y + 34, 204, y + 106), fill=self.p["fix"])
            text_c(d, 168, y + 38, num, font(PB, 54), (11, 15, 20))
            d.text((236, y + 40), txt, font=font(PM, 50), fill=self.p["text"])
        if t > dur * 0.62:
            k = prog(t, dur * 0.62, 0.4)
            d.text((100, 860), "CAN'T PATCH TODAY?", font=font(PB, 44), fill=self.p["secondary"])
            self.panel(img, (100, 930, 980, 1070), k)
            d.text((136, 970), "PasswordAuthentication no", font=font(PM, 48), fill=self.p["fix"])
            d.text((100, 1100), "Then restart sshd.", font=font(PS, 38), fill=self.p["secondary"])

    def b5(self, img, d, t, dur):
        k = prog(t, 0, 0.5)
        d.text((90, 420), "Nov 12", font=font(PB, int(200 + 30 * k)), fill=self.p["threat"])
        d.text((96, 690), "Federal due date, CISA BOD 26-04", font=font(PS, 46), fill=self.p["text"])
        if t > 0.8:
            src = ["CISA KEV catalog", "Alpine Linux advisory", "NVD CVE-2026-123158"]
            d.text((96, 850), "SOURCES IN DESCRIPTION", font=font(PB, 36), fill=self.p["secondary"])
            for j, s in enumerate(src):
                d.text((96, 910 + j * 58), "· " + s, font=font(PS, 42), fill=self.p["text"])
