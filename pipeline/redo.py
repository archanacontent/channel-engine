"""Re-renders queued Shorts after a fix and swaps them in.

    python -m pipeline.redo asked-and-answered:2026-11-12-1800 breach-brief:2026-11-14-1300 ...

Each item is rendered again from its saved script, the stored file is replaced,
and if it was already on YouTube the old video is marked for replacement: the
next upload run deletes it and uploads the fixed one with the same release time.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from pipeline.upload import QUEUE, ROOT, STAGE, asset, load, sh


def main(items):
    queue = load(QUEUE, [])
    STAGE.mkdir(exist_ok=True)
    for item in items:
        slug, stem = item.split(":")
        e = next((x for x in queue if x["slug"] == slug and x["stem"] == stem), None)
        if not e:
            print("not in queue", item)
            continue
        ep = ROOT / "channels" / slug / "episodes" / f"{stem}.yaml"
        r = subprocess.run([sys.executable, "-m", "render.build", str(ep), "--out", "redo"], capture_output=True, text=True)
        mp4 = Path("redo") / slug / f"{stem}.mp4"
        if r.returncode != 0 or not mp4.exists():
            print("render failed", item, r.stderr[-300:])
            continue
        meta = json.loads((Path("redo") / slug / f"{stem}.json").read_text())
        dst = STAGE / asset(e)
        shutil.copy(mp4, dst)
        sh("gh", "release", "upload", e["release"], "--clobber", str(dst))
        e["meta"] = meta
        srt = Path("redo") / slug / f"{stem}.srt"
        if srt.exists():
            e["srt"] = srt.read_text()
        if e.get("video_id") and e["status"] in ("scheduled", "uploaded", "held"):
            e["replace"] = e.pop("video_id")
        if e["status"] != "published":
            e["status"] = "rendered"
        for k in ("playlist_done", "captions_done", "uploaded_at"):
            e.pop(k, None)
        print("re-rendered", item, "(replaces " + e["replace"] + ")" if e.get("replace") else "")
    QUEUE.write_text(json.dumps(queue, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
