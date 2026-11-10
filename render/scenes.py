"""Scene templates for automated episodes.

Each beat of an automated episode names one scene type and its fields. The same
templates serve every channel; the channel's palette, fonts and background make
them look like that channel.

Scene types and fields (all text short; long text is shrunk or cut to fit):
  headline  {kicker?, text}
  stat      {value, label, source?}
  card      {title, rows: [[label, value], ...]}         up to 5 rows
  list      {title, items: [...], style: check|number|bullet}   up to 4 items
  compare   {left_label, left_text, right_label, right_text}
  flow      {steps: [{title, note?}, ...]}                2 to 4 steps
  image     {credit?}                                     uses the episode's image
  sizes     {a_label, a_value, b_label, b_value, unit}    two bodies to scale
  quote     {text, highlight: [...]}
  cta       {line, subline?}
"""
import math
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from render.lib import W, H, alpha_rect, arrow, clamp, ease, font, mix, prog, rgb, text_c, tw, wrap

TOP, BOTTOM = 300, 1230  # visual zone, clear of the corner tag and the captions


def theme_for(brand, p):
    pal = brand["palette"]
    f = brand["fonts"]
    head = f["headline"]
    body = f.get("body") or f.get("caption")
    mono = f.get("data") or f.get("label") or body
    accent = rgb(pal.get("accent") or pal.get("threat") or pal.get("edit"))
    accent2 = rgb(pal.get("fix") or pal.get("highlight") or pal.get("line") or pal.get("accent"))
    bg = rgb(pal["background"])
    light = sum(bg) > 600
    return {
        "head": (head["file"], head.get("weight", 700)),
        "body": (body["file"], body.get("weight", 400)),
        "bold": (body["file"], 700 if body.get("weight") else None),
        "mono": (mono["file"], mono.get("weight", 500)),
        "text": rgb(pal["text"]),
        "muted": rgb(pal.get("muted_text") or pal.get("secondary")),
        "accent": accent,
        "accent2": accent2,
        "bg": bg,
        "panel": mix(bg, (0, 0, 0), 0.04) if light else mix(bg, (255, 255, 255), 0.07),
        "panel_line": mix(bg, (0, 0, 0), 0.14) if light else mix(bg, (255, 255, 255), 0.18),
        "on_accent": (255, 255, 255) if sum(accent) < 450 else bg,
        "light": light,
    }


def F(spec, size):
    file, weight = spec
    return font(file, int(size), weight)


def fit(text, spec, max_size, min_size, maxw, max_lines):
    """Largest size at which the text wraps into max_lines within maxw."""
    text = str(text or "").strip()
    size = max_size
    while size >= min_size:
        f = F(spec, size)
        lines = wrap(text, f, maxw)
        if len(lines) <= max_lines:
            return f, lines
        size -= 2
    f = F(spec, min_size)
    lines = wrap(text, f, maxw)[:max_lines]
    if lines:
        while tw(f, lines[-1] + "…") > maxw and " " in lines[-1]:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] += "…"
    return f, lines


def lh(f, k=1.22):
    return int(f.size * k)


def fade_col(th, col, k):
    return mix(th["bg"], col, clamp(k))


@lru_cache(maxsize=8)
def _load_image(path, w, h):
    im = Image.open(path).convert("RGB")
    s = max(w / im.width, h / im.height) * 1.12
    return im.resize((int(im.width * s) + 2, int(im.height * s) + 2), Image.LANCZOS)


class SceneMixin:
    """Mixed into a channel painter: draws automated beats from their scene spec."""

    def scene_theme(self):
        if not hasattr(self, "_th"):
            self._th = theme_for(self.brand, self.p)
        return self._th

    def scene_beat(self, img, d, i, t, dur):
        beat = self.ep["beats"][i]
        sc = beat.get("scene") or {"type": "headline", "text": beat["caption"]}
        fn = getattr(self, "sc_" + str(sc.get("type", "headline")), None) or self.sc_headline
        try:
            fn(img, d, sc, t, dur, beat)
        except Exception:
            self.sc_headline(img, d, {"text": beat["caption"]}, t, dur, beat)

    # ---- scene types ----
    def sc_headline(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        f, lines = fit(sc.get("text") or beat["caption"], th["head"], 104, 56, 900, 5)
        block = lh(f) * len(lines) + (140 if sc.get("kicker") else 0)
        y = max(TOP + 20, (TOP + BOTTOM) / 2 - block / 2 - 30)
        if sc.get("kicker"):
            kf = F(th["bold"], 38)
            k = prog(t, 0.0, 0.4)
            label = str(sc["kicker"]).upper()[:40]
            wv = tw(kf, label) + 48
            d.rounded_rectangle((90, y, 90 + wv * k, y + 66), radius=14, fill=th["accent"])
            if k >= 1:
                d.text((114, y + 12), label, font=kf, fill=th["on_accent"])
            y += 120
            y += 20
        block = lh(f) * len(lines)
        for j, ln in enumerate(lines):
            k = prog(t, 0.12 + j * 0.12, 0.45)
            d.text((90, y + j * lh(f) + (1 - k) * 22), ln, font=f, fill=fade_col(th, th["text"], k))
        k = prog(t, 0.5, 0.6)
        d.rectangle((92, y + block + 26, 92 + 220 * k, y + block + 36), fill=th["accent"])

    def sc_stat(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        value = str(sc.get("value", "")).strip()[:14]
        k = prog(t, 0.0, 1.0)
        m = re.fullmatch(r"([^\d]*)([\d,]+(?:\.\d+)?)(.*)", value)
        shown = value
        if m and k < 1:
            num = float(m.group(2).replace(",", ""))
            decimals = len(m.group(2).split(".")[1]) if "." in m.group(2) else 0
            cur = num * k
            body = f"{cur:,.{decimals}f}" if "," in m.group(2) else f"{cur:.{decimals}f}"
            shown = m.group(1) + body + m.group(3)
        f, _ = fit(value, th["head"], 250, 110, 920, 1)
        text_c(d, W / 2, 470, shown, f, th["accent"])
        lf, lines = fit(sc.get("label", ""), th["body"], 54, 38, 860, 3)
        for j, ln in enumerate(lines):
            kk = prog(t, 0.6 + j * 0.1, 0.4)
            text_c(d, W / 2, 790 + j * lh(lf), ln, lf, fade_col(th, th["text"], kk))
        if sc.get("source"):
            sf, sl = fit(sc["source"], th["body"], 34, 28, 860, 2)
            for j, ln in enumerate(sl):
                text_c(d, W / 2, 1010 + j * lh(sf), ln, sf, fade_col(th, th["muted"], prog(t, 1.0, 0.4)))

    def panel(self, img, box, k=1.0, accent=False):
        th = self.scene_theme()
        if k <= 0:
            return
        alpha_rect(img, box, th["panel"], 0.95 * k, radius=24)
        ImageDraw.Draw(img).rounded_rectangle(box, radius=24, outline=th["accent"] if accent else th["panel_line"],
                                              width=4 if accent else 2)

    def sc_card(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        rows = [r for r in (sc.get("rows") or []) if isinstance(r, (list, tuple)) and len(r) == 2][:5]
        tf, tl = fit(sc.get("title", ""), th["head"], 60, 40, 880, 2)
        rh = 150
        total = lh(tf) * len(tl) + 30 + rh * len(rows) + 20
        y = max(TOP + 20, (TOP + BOTTOM) / 2 - total / 2)
        for j, ln in enumerate(tl):
            d.text((90, y + j * lh(tf)), ln, font=tf, fill=fade_col(th, th["text"], prog(t, 0, 0.4)))
        y += lh(tf) * len(tl) + 30
        rh = min(150, (BOTTOM - y - 20) // max(1, len(rows)))
        self.panel(img, (80, y, 1000, y + rh * len(rows) + 20), prog(t, 0.1, 0.4))
        lf = F(th["bold"], 30)
        for j, (lab, val) in enumerate(rows):
            k = prog(t, 0.3 + j * min(0.5, dur * 0.6 / max(1, len(rows))), 0.4)
            if k <= 0:
                continue
            yy = y + 20 + j * rh
            d.text((120, yy + 10), str(lab).upper()[:32], font=lf, fill=th["muted"])
            vf, vl = fit(val, th["mono"], 46, 30, 840, 1 if rh < 140 else 2)
            for q, ln in enumerate(vl):
                d.text((120, yy + 52 + q * lh(vf)), ln[: max(1, int(len(ln) * k))], font=vf,
                       fill=th["accent"] if j == 0 else th["text"])
            if j < len(rows) - 1:
                d.line((120, yy + rh - 4, 960, yy + rh - 4), fill=th["panel_line"], width=2)

    def sc_list(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        items = [str(x) for x in (sc.get("items") or [])][:4]
        style = sc.get("style", "check")
        tf, tl = fit(sc.get("title", ""), th["head"], 60, 40, 900, 2) if sc.get("title") else (None, [])
        est = (lh(tf) * len(tl) + 36 if tl else 0) + len(items) * 190 + 22 * (len(items) - 1)
        y = max(TOP + 20, (TOP + BOTTOM) / 2 - est / 2)
        if sc.get("title"):
            for j, ln in enumerate(tl):
                d.text((90, y + j * lh(tf)), ln, font=tf, fill=fade_col(th, th["text"], prog(t, 0, 0.4)))
            y += lh(tf) * len(tl) + 36
        gap = 22
        ih = min(190, (BOTTOM - y - gap * (len(items) - 1)) // max(1, len(items)))
        step = max(0.35, min(1.2, dur * 0.7 / max(1, len(items))))
        for j, it in enumerate(items):
            k = prog(t, 0.25 + j * step, 0.4)
            if k <= 0:
                continue
            yy = y + j * (ih + gap) + (1 - k) * 20
            self.panel(img, (80, yy, 1000, yy + ih), k)
            cx, cy = 140, yy + ih / 2
            d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=th["accent2"] if style == "check" else th["accent"])
            mark = str(j + 1) if style == "number" else ("✓" if style == "check" else "•")
            mf = F(th["bold"], 34) if style == "number" else font("Inter[opsz,wght].ttf", 36, 700)
            text_c(d, cx, cy - mf.size * 0.62, mark, mf, th["on_accent"] if style != "check" else th["bg"])
            f, lines = fit(it, th["body"], 46, 32, 760, 3)
            ty = cy - lh(f) * len(lines) / 2
            for q, ln in enumerate(lines):
                d.text((200, ty + q * lh(f)), ln, font=f, fill=th["text"])

    def sc_compare(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        boxes = [(sc.get("left_label", "Before"), sc.get("left_text", ""), False, 0.0),
                 (sc.get("right_label", "After"), sc.get("right_text", ""), True, min(dur * 0.4, 2.5))]
        sizes = [fit(txt, th["body"], 46, 32, 820, 6) for _, txt, _, _ in boxes]
        est = sum(110 + lh(f) * len(ls) for f, ls in sizes) + 40
        y = max(TOP + 20, (TOP + BOTTOM) / 2 - est / 2)
        for (lab, txt, acc, at), (f, lines) in zip(boxes, sizes):
            k = prog(t, at, 0.5)
            hgt = 110 + lh(f) * len(lines)
            if k > 0:
                self.panel(img, (80, y, 1000, y + hgt), k, accent=acc)
                d.text((120, y + 30), str(lab).upper()[:30], font=F(th["bold"], 32),
                       fill=th["accent"] if acc else th["muted"])
                shown = max(1, int(len(lines) * clamp(k * 1.3)))
                for q, ln in enumerate(lines[:shown]):
                    d.text((120, y + 88 + q * lh(f)), ln, font=f, fill=th["text"] if acc else th["muted"])
            y += hgt + 40

    def sc_flow(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        steps = [s if isinstance(s, dict) else {"title": str(s)} for s in (sc.get("steps") or [])][:4]
        n = max(1, len(steps))
        bh, gap = 170, 70
        total = n * bh + (n - 1) * gap
        y0 = (TOP + BOTTOM) / 2 - total / 2
        lit_step = max(0.4, dur * 0.75 / n)
        for j, s in enumerate(steps):
            y = y0 + j * (bh + gap)
            k = prog(t, j * 0.25, 0.4)
            lit = prog(t, 0.4 + j * lit_step, 0.4)
            if k <= 0:
                continue
            if j:
                d.line((540, y - gap, 540, y), fill=th["accent2"], width=5)
            if lit > 0:
                alpha_rect(img, (136, y - 12, 944, y + bh + 12), th["accent"], 0.16 * lit, radius=36)
            d.rounded_rectangle((150, y, 930, y + bh), radius=28, fill=th["panel"],
                                outline=mix(th["panel_line"], th["accent"], lit), width=3 + int(3 * lit))
            d.ellipse((182, y + bh / 2 - 34, 250, y + bh / 2 + 34), fill=mix(th["panel_line"], th["accent"], lit))
            text_c(d, 216, y + bh / 2 - 24, str(j + 1), F(th["bold"], 38), th["bg"] if lit > 0.5 else th["text"])
            tf, tl = fit(s.get("title", ""), th["mono"], 42, 30, 620, 1)
            d.text((280, y + (34 if s.get("note") else bh / 2 - 26)), tl[0] if tl else "", font=tf, fill=th["text"])
            if s.get("note"):
                nf, nl = fit(s["note"], th["body"], 32, 26, 620, 2)
                for q, ln in enumerate(nl):
                    d.text((280, y + 92 + q * lh(nf)), ln, font=nf, fill=th["muted"])
        if steps:
            ph = (t * 0.6) % 1
            seg = int(ph * max(1, n - 1)) if n > 1 else 0
            if n > 1:
                yy = y0 + bh + seg * (bh + gap) + (ph * (n - 1) - seg) * gap
                d.ellipse((528, yy - 12, 552, yy + 12), fill=th["accent"])

    def sc_image(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        path = (self.ep.get("media") or {}).get("image")
        if not path or not Path(path).exists():
            return self.sc_headline(img, d, {"text": beat["caption"]}, t, dur, beat)
        bw, bh = 960, 860
        pic = _load_image(path, bw, bh)
        z = 1 + 0.06 * clamp(t / max(dur, 1))
        cw, ch = int(bw / z), int(bh / z)
        ox = int((pic.width - cw) * (0.3 + 0.4 * clamp(t / max(dur, 1))))
        oy = int((pic.height - ch) / 2)
        crop = pic.crop((ox, oy, ox + cw, oy + ch)).resize((bw, bh), Image.BILINEAR)
        m = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, bw - 1, bh - 1), radius=28, fill=int(255 * prog(t, 0, 0.5)))
        img.paste(crop, (60, TOP + 10), m)
        credit = sc.get("credit") or (self.ep.get("media") or {}).get("credit")
        if credit:
            cf, cl = fit("Credit: " + credit, th["body"], 28, 24, 940, 1)
            d.text((64, TOP + bh + 26), cl[0], font=cf, fill=th["muted"])

    def sc_sizes(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        try:
            a, b = float(sc["a_value"]), float(sc["b_value"])
        except (KeyError, TypeError, ValueError):
            return self.sc_headline(img, d, {"text": beat["caption"]}, t, dur, beat)
        big, small = (a, b) if a >= b else (b, a)
        big_lab, small_lab = (sc.get("a_label"), sc.get("b_label")) if a >= b else (sc.get("b_label"), sc.get("a_label"))
        R = 290
        r = max(6, R * small / big)
        cy = 820
        k = prog(t, 0.0, 0.8)
        kb = prog(t, 0.6, 0.8)
        d.ellipse((540 - R * k, cy - R * k, 540 + R * k, cy + R * k), outline=th["accent"], width=6,
                  fill=mix(th["bg"], th["accent"], 0.18))
        if kb > 0:
            sx = 540 + R + 40 + r if r < 150 else 540
            d.ellipse((sx - r * kb, cy - r * kb, sx + r * kb, cy + r * kb), fill=th["accent2"])
        lf = F(th["bold"], 40)
        text_c(d, W / 2, cy + R + 40, f"{big_lab}", lf, th["text"])
        ratio = big / small
        if t > 1.2:
            rf = F(th["head"], 96)
            text_c(d, W / 2, TOP + 10, f"{ratio:.1f}×" if ratio < 10 else f"{ratio:,.0f}×", rf, th["accent2"])
            text_c(d, W / 2, TOP + 130, f"{big_lab} vs {small_lab}", F(th["body"], 36), th["muted"])

    def sc_quote(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        f, lines = fit(sc.get("text", ""), th["head"], 92, 54, 880, 6)
        y = (TOP + BOTTOM) / 2 - lh(f, 1.3) * len(lines) / 2
        hl = [h.lower() for h in (sc.get("highlight") or [])]
        for j, ln in enumerate(lines):
            k = prog(t, 0.1 + j * 0.18, 0.45)
            yy = y + j * lh(f, 1.3)
            for h in hl:
                idx = ln.lower().find(h)
                if idx >= 0 and t > dur * 0.4:
                    x0 = 100 + tw(f, ln[:idx])
                    kk = prog(t, dur * 0.4, 0.5)
                    alpha_rect(img, (x0 - 6, yy + f.size * 0.35, x0 + tw(f, ln[idx: idx + len(h)]) * kk + 6,
                                     yy + f.size * 1.1), th["accent2"], 0.55, radius=8)
            d.text((100, yy + (1 - k) * 14), ln, font=f, fill=fade_col(th, th["text"], k))

    def sc_cta(self, img, d, sc, t, dur, beat):
        th = self.scene_theme()
        k = prog(t, 0, 0.6)
        size = int(300 + 60 * k)
        lg = self.logo_big.resize((size, size))
        img.paste(lg, ((W - size) // 2, 560 - size // 2), lg)
        f, lines = fit(sc.get("line", ""), th["head"], 64, 44, 900, 2)
        for j, ln in enumerate(lines):
            text_c(d, W / 2, 800 + j * lh(f), ln, f, th["text"])
        if sc.get("subline") and t > 0.6:
            sf, sl = fit(sc["subline"], th["bold"], 42, 32, 900, 2)
            for j, ln in enumerate(sl):
                text_c(d, W / 2, 820 + lh(f) * len(lines) + 30 + j * lh(sf), ln, sf, th["accent"])
