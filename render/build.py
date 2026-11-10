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

from render import audio, seo
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


def metadata(brand, ep, use_autocomplete=True):
    series = ep["series"]
    yt_tags = seo.build_hashtags(brand, ep, seo.MAX_YT_HASHTAGS)
    ig_tags = seo.build_hashtags(brand, ep, seo.MAX_IG_HASHTAGS)
    fields = {k: v for k, v in ep["description"].items() if k != "sources"}
    srcs = ep["description"].get("sources", [])
    fields["source_links"] = "\n".join(f"- {s}" for s in srcs) if srcs else ""
    fields["youtube_hashtags"] = " ".join(yt_tags)
    if "original" in ep:
        fields.setdefault("source_link", ep["original"]["source"])
        fields.setdefault("license", ep["original"]["license"])
    first_line = next((str(v) for v in ep["description"].values() if isinstance(v, str)), ep["title"])
    return {
        "channel": brand["name"],
        "handle": brand.get("handle"),
        "series": series,
        "playlist": brand["seo"]["playlists"].get(series),
        "title": ep["title"][:100],
        "youtube_description": fill_template(brand["description_template"], fields)[:5000],
        "tags": seo.build_tags(brand, ep, use_autocomplete),
        "category_id": brand["seo"]["category_id"],
        "language": "en",
        "made_for_kids": False,
        "altered_content": "No",
        "instagram_caption": f"{first_line}\n\n" + " ".join(ig_tags),
    }


def srt(captions):
    def ts(t):
        ms = int(round(t * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    lines = []
    for i, (t0, t1, toks) in enumerate(captions, 1):
        lines += [str(i), f"{ts(t0)} --> {ts(t1)}", " ".join(w for w, _ in toks), ""]
    return "\n".join(lines)


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

    bed, bed_name = audio.load_bed(slug, chan_dir / "music", total, stem)
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
    (out / f"{stem}.srt").write_text(srt(captions))
    print("done", out / f"{stem}.mp4", round(total, 1), "s")


if __name__ == "__main__":
    main()
