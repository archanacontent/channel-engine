"""Render one episode into a finished Short.

    python -m render.build channels/<slug>/episodes/<file>.yaml [--stills 2.0,9.5]
"""
import argparse
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

from render import audio
from render.lib import FPS, H, W, caption_timeline, draw_caption

PAINTERS = {
    "asked-and-answered": ("render.painters.asked_and_answered", "AskedPainter"),
    "automation-shelf": ("render.painters.automation_shelf", "ShelfPainter"),
    "breach-brief": ("render.painters.breach_brief", "BreachPainter"),
    "plain-docs": ("render.painters.plain_docs", "DocsPainter"),
    "deep-field": ("render.painters.deep_field", "FieldPainter"),
}
MARK_KEYS = {"highlight": "highlight", "threat": "threat", "fix": "fix", "numbers": "numbers"}
END = 1.0  # seconds of branded end frame


def load(ep_path):
    ep_path = Path(ep_path)
    chan_dir = ep_path.parent.parent
    brand = yaml.safe_load((chan_dir / "brand.yaml").read_text())
    ep = yaml.safe_load(ep_path.read_text())
    return chan_dir, brand, ep


def frame_at(painter, captions, timing, total, t):
    img = painter.background(t)
    d = ImageDraw.Draw(img)
    end_start = total - END
    if t >= end_start:
        painter.end(img, d, t - end_start)
        return img
    bi = 0
    for j, (s, speech, bd) in enumerate(timing):
        if t >= s:
            bi = j
    s, speech, bd = timing[bi]
    painter.beat(img, d, bi, max(0.0, t - s), bd)
    painter.tag(img, d)
    for (t0, t1, toks) in captions:
        if t0 <= t < t1:
            draw_caption(img, toks, painter.caption_style, t - t0)
            break
    return img


def fill_template(template, fields):
    """Fill the brand's description template; a line whose field is missing is dropped."""
    out = []
    for line in template.splitlines():
        keys = re.findall(r"{(\w+)}", line)
        if all(k in fields and fields[k] for k in keys):
            out.append(line.format(**{k: fields[k] for k in keys}))
        elif not keys:
            out.append(line)
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def metadata(brand, ep):
    series = ep["series"]
    yt = brand["hashtags"].get("youtube") or brand["hashtags"]["youtube_by_series"][series]
    fields = {k: v for k, v in ep["description"].items() if k != "sources"}
    srcs = ep["description"].get("sources", [])
    fields["source_links"] = "\n".join(f"- {s}" for s in srcs) if srcs else ""
    fields["youtube_hashtags"] = " ".join(yt)
    if "original" in ep:
        fields.setdefault("source_link", ep["original"]["source"])
        fields.setdefault("license", ep["original"]["license"])
    ig = brand["hashtags"]["instagram_anchors"] + ep.get("instagram_hashtags_rotating", [])[:3]
    return {
        "channel": brand["name"],
        "series": series,
        "title": ep["title"],
        "youtube_description": fill_template(brand["description_template"], fields),
        "instagram_caption": f"{ep['title']}\n\n" + " ".join(ig[:5]),
        "altered_content": "No",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--out", default="out")
    ap.add_argument("--stills", default="")
    a = ap.parse_args()

    chan_dir, brand, ep = load(a.episode)
    slug = brand["slug"]
    out = Path(a.out) / slug
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(a.episode).stem

    voice, timing = audio.speak_beats(ep["beats"], brand["voice"])
    total = timing[-1][0] + timing[-1][2] + END
    mod, cls = PAINTERS[slug]
    painter = getattr(importlib.import_module(mod), cls)(brand, ep, timing)

    captions = []
    for b, (s, speech, bd) in zip(ep["beats"], timing):
        marks = {MARK_KEYS[k]: b[k] for k in MARK_KEYS if k in b}
        captions += caption_timeline(b["caption"], speech, s, marks)

    if a.stills:
        for ts in a.stills.split(","):
            frame_at(painter, captions, timing, total, float(ts)).save(out / f"{stem}_{float(ts):05.1f}.jpg", quality=90)
        print("timing", [(round(s, 2), round(bd, 2)) for s, _, bd in timing], "total", round(total, 2))
        return

    bed, bed_name = audio.load_bed(slug, chan_dir / "music", total)
    wav = out / f"{stem}.wav"
    audio.mixdown(voice, bed, brand["music"]["gain_db"], wav)

    tmp = out / f"{stem}.video.part.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                            "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    n = int(round(total * FPS))
    for i in range(n):
        enc.stdin.write(frame_at(painter, captions, timing, total, i / FPS).tobytes())
        if i % 300 == 0:
            print(f"{slug}: frame {i}/{n}", flush=True)
    enc.stdin.close()
    assert enc.wait() == 0
    final = out / f"{stem}.part.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(final)],
                   check=True)
    final.rename(out / f"{stem}.mp4")
    tmp.unlink()
    wav.unlink()
    meta = metadata(brand, ep)
    meta.update({"duration_s": round(total, 2), "music": bed_name})
    (out / f"{stem}.json").write_text(json.dumps(meta, indent=2))
    print("done", out / f"{stem}.mp4", round(total, 1), "s")


if __name__ == "__main__":
    main()
