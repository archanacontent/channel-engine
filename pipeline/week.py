"""Writes and renders one channel's Shorts for a run of days.

    python -m pipeline.week --slug breach-brief --start 2026-11-16 --days 7 --out out

For each day and each of the channel's three slots it takes the slot's series,
fetches the next unused record (falling back to the channel's other series),
writes the script, renders the Short and records it in out/<slug>/manifest.json.
"""
import argparse
import time
import json
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from pipeline.write import QuotaSpent, write_episode
from sources.fetch import UA, next_record

ROOT = Path(__file__).resolve().parent.parent
ET = ZoneInfo("America/New_York")


def load_used():
    p = ROOT / "state" / "used.json"
    return set(json.loads(p.read_text())) if p.exists() else set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default="out")
    ap.add_argument("--max", type=int, default=99, help="stop after this many Shorts")
    a = ap.parse_args()

    chan = ROOT / "channels" / a.slug
    brand = yaml.safe_load((chan / "brand.yaml").read_text())
    if brand.get("format") == "comic":
        from pipeline.comic import write_comic as writer
    else:
        writer = write_episode
    out = Path(a.out) / a.slug
    (out / "media").mkdir(parents=True, exist_ok=True)
    used = load_used()
    qp = ROOT / "queue" / "current.json"
    queued = {e["stem"] for e in (json.loads(qp.read_text()) if qp.exists() else []) if e["slug"] == a.slug}
    taken, manifest, failures = set(), [], []
    spent = False
    start = date.fromisoformat(a.start)

    for day in range(a.days):
        d = start + timedelta(days=day)
        for slot in brand["series"]:
            hh, mm = map(int, slot["slot"].split(":"))
            if f"{d.isoformat()}-{slot['slot'].replace(':', '')}" in queued or len(manifest) >= a.max or spent:
                continue
            when = datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET)
            t0 = time.time()
            rec = next_record(a.slug, slot["name"], used, taken)
            print(f"  fetched in {time.time() - t0:.0f}s", flush=True)
            if not rec:
                failures.append(f"{d} {slot['slot']}: no new source material")
                continue
            taken.add(rec["id"])
            print(f"writing {d} {slot['slot']} {rec['series']} {rec['id']}", flush=True)
            try:
                ep, err = writer(brand, rec)
            except QuotaSpent as e:
                failures.append(f"Stopped at {d} {slot['slot']}: {e}. The next run picks up from here.")
                spent = True
                continue
            except Exception as e:
                ep, err = None, str(e)
            if not ep:
                failures.append(f"{d} {slot['slot']} {rec['series']} ({rec['id']}): {err}")
                # One more try with the next record, so the slot isn't left empty.
                rec = next_record(a.slug, slot["name"], used, taken)
                if not rec:
                    continue
                taken.add(rec["id"])
                try:
                    ep, err = writer(brand, rec)
                except QuotaSpent as e:
                    failures.append(f"Stopped at {d} {slot['slot']}: {e}. The next run picks up from here.")
                    spent = True
                    continue
                except Exception as e:
                    ep, err = None, str(e)
                if not ep:
                    failures.append(f"{d} {slot['slot']} retry ({rec['id']}): {err}")
                    continue
            stem = f"{d.isoformat()}-{slot['slot'].replace(':', '')}"
            ep.update({"series": rec["series"], "record_id": rec["id"], "auto": True,
                       "instagram_hashtags_rotating": []})
            if rec.get("image_url") and not ep.get("media"):
                img = out / "media" / f"{stem}.jpg"
                try:
                    req = urllib.request.Request(rec["image_url"], headers={"User-Agent": UA})
                    img.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                    ep["media"] = {"image": str(img.resolve()), "credit": rec.get("credit", "NASA")}
                except Exception as e:
                    failures.append(f"{stem}: image download failed ({e}); image scenes fall back to text")
            ep_path = chan / "episodes" / f"{stem}.yaml"
            ep_text = yaml.safe_dump(ep, sort_keys=False, allow_unicode=True, width=1000)
            ep_path.write_text(ep_text)
            (out / "episodes").mkdir(exist_ok=True)
            (out / "episodes" / f"{stem}.yaml").write_text(ep_text)
            print(f"  script ready in {time.time() - t0:.0f}s", flush=True)
            r = subprocess.run([sys.executable, "-m", "render.build", str(ep_path), "--out", a.out],
                               capture_output=True, text=True)
            if r.returncode != 0 or not (out / f"{stem}.mp4").exists():
                failures.append(f"{stem}: render failed: {r.stderr[-400:]}")
                continue
            meta = json.loads((out / f"{stem}.json").read_text())
            manifest.append({
                "slug": a.slug, "channel": brand["name"], "series": rec["series"], "title": meta["title"],
                "stem": stem, "record_id": rec["id"], "publish_at": when.isoformat(),
                "meta": meta, "srt": (out / f"{stem}.srt").read_text(), "status": "rendered",
            })
            (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
            (out / "failures.txt").write_text("\n".join(failures))
            print(f"{a.slug} {stem} {rec['series']}: {meta['title']}", flush=True)

    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    (out / "failures.txt").write_text("\n".join(failures))
    print(f"{a.slug}: {len(manifest)} Shorts rendered, {len(failures)} issues")
    for f in failures:
        print("  -", f)


if __name__ == "__main__":
    main()
