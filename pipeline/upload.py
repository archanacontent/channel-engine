"""Collects rendered Shorts, stores them, uploads them to YouTube as private,
and keeps the Sunday review issue up to date.

    python -m pipeline.upload --collect artifacts --release week-2026-11-16
    python -m pipeline.upload            # daily catch-up: upload what's still pending

YouTube allows 100 uploads a day per project, so at most CAP go up per Pacific
day; the rest wait in the GitHub release and go up on the next run.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from publish.youtube import upload_private

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue" / "current.json"
USED = ROOT / "state" / "used.json"
STAGE = ROOT / "staging"
PT = ZoneInfo("America/Los_Angeles")
CAP = 95


def sh(*args, check=True):
    return subprocess.run(list(args), capture_output=True, text=True, check=check)


def load(p, default):
    return json.loads(p.read_text()) if p.exists() else default


def asset(e):
    ext = Path(e.get("file", e["stem"] + ".mp4")).suffix or ".mp4"
    return f"{e['slug']}--{e['stem']}{ext}"


def collect(src, release, queue):
    STAGE.mkdir(exist_ok=True)
    used = set(load(USED, []))
    known = {(e["slug"], e["stem"]) for e in queue}
    files = []
    for man in sorted(Path(src).glob("*/manifest.json")):
        chan_out = man.parent
        for e in json.loads(man.read_text()):
            if (e["slug"], e["stem"]) in known:
                continue
            mp4 = chan_out / e.get("file", f"{e['stem']}.mp4")
            if not mp4.exists():
                continue
            if e.get("platform") == "instagram":
                e["status"] = "ready"   # Instagram has no private uploads; it posts straight from storage at its slot
            dst = STAGE / asset(e)
            shutil.copy(mp4, dst)
            files.append(str(dst))
            e["release"] = release
            queue.append(e)
            used.add(e["record_id"])
            ep = chan_out / "episodes" / f"{e['stem']}.yaml"
            if ep.exists():
                (ROOT / "channels" / e["slug"] / "episodes").mkdir(parents=True, exist_ok=True)
                shutil.copy(ep, ROOT / "channels" / e["slug"] / "episodes" / ep.name)
    if files:
        if sh("gh", "release", "view", release, check=False).returncode != 0:
            sh("gh", "release", "create", release, "--title", release, "--prerelease",
               "--notes", "Rendered Shorts waiting for upload. Safe to delete after the week ends.")
        for i in range(0, len(files), 20):
            sh("gh", "release", "upload", release, "--clobber", *files[i:i + 20])
    USED.parent.mkdir(exist_ok=True)
    USED.write_text(json.dumps(sorted(used), indent=0))
    print(f"collected {len(files)} new Shorts into {release}")


def remove_replaced(queue):
    """Old copies of re-rendered Shorts come off YouTube first, before any upload, so a
    broken version can never go live even if the fixed one has to wait for upload room."""
    from publish.youtube import client
    for e in sorted(queue, key=lambda x: x["publish_at"]):
        if not e.get("replace"):
            continue
        try:
            client(e["slug"]).videos().delete(id=e["replace"]).execute()
            print("deleted old version", e["slug"], e["replace"])
            e.pop("replace")
        except Exception as ex:
            if "notFound" in str(ex) or "404" in str(ex):
                e.pop("replace")
                continue
            print("could not delete old version", e["replace"], str(ex)[:120])
            if "quota" in str(ex).lower():
                break


def upload_pending(queue):
    remove_replaced(queue)
    today = datetime.now(PT).date().isoformat()
    done_today = sum(1 for e in queue if (e.get("uploaded_at") or "")[:10] == today)
    budget = CAP - done_today
    capped = set()  # channels that hit YouTube's own daily upload limit
    now = datetime.now(timezone.utc)
    for e in sorted(queue, key=lambda x: x["publish_at"]):
        if e["status"] != "rendered" or budget <= 0 or e["slug"] in capped:
            continue
        if datetime.fromisoformat(e["publish_at"]) < now - timedelta(hours=6):
            e["status"] = "expired"  # its slot passed before it could upload
            continue
        if not os.environ.get("YT_REFRESH_" + e["slug"].upper().replace("-", "_")):
            if e["slug"] not in capped:
                print(f"{e['slug']}: no YouTube connection yet, keeping its Shorts for later")
            capped.add(e["slug"])
            continue
        f = STAGE / asset(e)
        if not f.exists():
            STAGE.mkdir(exist_ok=True)
            r = sh("gh", "release", "download", e["release"], "--pattern", asset(e), "--dir", str(STAGE), check=False)
            if r.returncode != 0:
                print("missing asset", asset(e))
                continue
        from render.seo import with_keywords
        e["meta"]["youtube_description"] = with_keywords(e["slug"], e["meta"])
        e["keywords_done"] = True
        when = datetime.fromisoformat(e["publish_at"]).astimezone(timezone.utc)
        at = when.strftime("%Y-%m-%dT%H:%M:%SZ") if when > now + timedelta(minutes=15) else None
        try:
            e["video_id"] = upload_private(e["slug"], str(f), e["meta"], publish_at=at)
        except Exception as ex:
            print("upload failed", asset(e), ex)
            if "quota" in str(ex).lower():
                break
            if "uploadLimitExceeded" in str(ex) or "exceeded the number of videos" in str(ex):
                capped.add(e["slug"])
                print(f"{e['slug']} reached its daily upload limit; the rest go up tomorrow")
            continue
        e["status"] = "scheduled" if at else "uploaded"   # "uploaded" = due now; the slot check releases it
        e["uploaded_at"] = datetime.now(PT).isoformat()
        budget -= 1
        print("uploaded", e["slug"], e["stem"], e["video_id"])
    left = sum(1 for e in queue if e["status"] == "rendered")
    print(f"{left} Shorts still waiting for upload")


from review.approvals import TICK, review_body, ticked  # noqa: E402


def week_of(e):
    d = datetime.fromisoformat(e["publish_at"]).date()
    return (d - timedelta(days=d.weekday())).isoformat()


def update_issues(queue):
    """One review issue per posting week (Monday to Sunday)."""
    sh("gh", "label", "create", "review", "--color", "1D76DB", "--force", check=False)
    for week in sorted({week_of(e) for e in queue}):
        entries = [e for e in queue if week_of(e) == week]
        title = f"Stop list: week of {week}"
        found = json.loads(sh("gh", "issue", "list", "--label", "review", "--state", "open", "--search",
                              f'"{title}" in:title', "--json", "number,title,body").stdout or "[]")
        found = [i for i in found if i["title"] == title]
        ticks = ticked(found[0]["body"], entries) if found else set()
        body = review_body(entries, ticks)
        if found:
            sh("gh", "issue", "edit", str(found[0]["number"]), "--body", body)
        elif any(e.get("video_id") for e in entries):
            sh("gh", "issue", "create", "--title", title, "--label", "review", "--body", body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect")
    ap.add_argument("--release")
    a = ap.parse_args()
    queue = load(QUEUE, [])
    if a.collect:
        collect(a.collect, a.release, queue)
    upload_pending(queue)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=21)).isoformat()
    queue = [e for e in queue if not (e["status"] == "published" and e["publish_at"] < cutoff)]
    QUEUE.parent.mkdir(exist_ok=True)
    QUEUE.write_text(json.dumps(queue, indent=1, ensure_ascii=False))
    update_issues(queue)


if __name__ == "__main__":
    main()
