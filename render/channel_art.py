"""Channel artwork from each brand file: profile image, banner and video watermark.

    python -m render.channel_art --out art
"""
import argparse
import importlib
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

from render.build import PAINTERS
from render.lib import font, rgb, tw, wrap

ROOT = Path(__file__).resolve().parent.parent
BW, BH = 2560, 1440          # YouTube banner
SAFE_W, SAFE_H = 1546, 423   # area visible on every device


def painter_for(slug):
    brand = yaml.safe_load((ROOT / "channels" / slug / "brand.yaml").read_text())
    mod, cls = PAINTERS[slug]
    return brand, getattr(importlib.import_module(mod), cls)(brand, {}, [(0, 1, 1)])


def banner(brand, pt):
    bg = pt.background(0).resize((BW, int(BW * 1920 / 1080)))
    top = (bg.height - BH) // 2
    img = bg.crop((0, top, BW, top + BH)).convert("RGB")
    d = ImageDraw.Draw(img)
    size = 300
    lg = pt.logo(size)
    name_size = 120
    while tw(font(pt.tag_font[0], name_size, 700), brand["name"]) > SAFE_W - size - 120:
        name_size -= 4
    name_f = font(pt.tag_font[0], name_size, 700)
    line_f = font(pt.tag_font[0], 46, 500)
    name_w = tw(name_f, brand["name"])
    block = size + 60 + max(name_w, 900)
    x0 = (BW - block) / 2
    cy = BH / 2
    img.paste(lg, (int(x0), int(cy - size / 2)), lg)
    tx = x0 + size + 60
    d.text((tx, cy - 150), brand["name"], font=name_f, fill=rgb(pt.tag_text_color))
    muted = pt.p.get("muted_text", pt.p.get("secondary"))
    for j, ln in enumerate(wrap(brand["positioning"], line_f, 900)):
        d.text((tx, cy + 10 + j * 60), ln, font=line_f, fill=muted)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="art")
    a = ap.parse_args()
    for slug in PAINTERS:
        brand, pt = painter_for(slug)
        out = Path(a.out) / slug
        out.mkdir(parents=True, exist_ok=True)
        # Profile: full-bleed square in the channel's background, mark inside the circle crop.
        pt.bare = True
        prof = Image.new("RGB", (800, 800), pt.p["background"])
        mark = pt.logo(640)
        prof.paste(mark, (80, 80), mark)
        prof.save(out / "profile-800.png")
        pt.bare = False
        pt.logo(150).save(out / "watermark-150.png")
        banner(brand, pt).save(out / "banner-2560x1440.jpg", quality=92)
        print("art", slug)


if __name__ == "__main__":
    main()
