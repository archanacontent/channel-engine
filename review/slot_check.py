"""Runs after each posting slot. Publishes every Short that is ticked in an open
review issue and whose slot time has passed, then marks it published.

A Short that is never ticked stays private.
"""
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone

from pipeline.upload import QUEUE, load, update_issues, week_of
from review.approvals import is_approved, ticked
from publish.youtube import publish


def approved_keys(queue):
    raw = subprocess.run(["gh", "issue", "list", "--label", "review", "--state", "open", "--json", "title,body",
                          "--limit", "20"], capture_output=True, text=True, check=True).stdout
    keys = set()
    for issue in json.loads(raw or "[]"):
        week = issue["title"].rsplit(" ", 1)[-1]
        keys |= ticked(issue["body"], [e for e in queue if week_of(e) == week])
    return keys


def post_instagram(e):
    from pipeline.upload import STAGE, asset
    from publish.instagram import publish as ig_publish
    STAGE.mkdir(exist_ok=True)
    f = STAGE / asset(e)
    if not f.exists():
        subprocess.run(["gh", "release", "download", e["release"], "--pattern", asset(e), "--dir", str(STAGE)], check=True)
    import yaml
    from pathlib import Path
    from strips.write import instagram_caption
    brand = yaml.safe_load((Path(__file__).resolve().parent.parent / "channels" / e["slug"] / "brand.yaml").read_text())
    old = e["meta"]["instagram_caption"]
    text = old.split("\n.\n")[0].split("\n\n#")[0].split("\n\n")[0].strip()
    gag = [w for w in old.split() if w.startswith("#")][-5:]
    return ig_publish(f, instagram_caption(brand, text, gag))


def main():
    queue = load(QUEUE, [])
    now = datetime.now(timezone.utc)
    ok = approved_keys(queue)
    changed = False
    now_slug = os.environ.get("POST_NOW", "").strip()   # post this channel's next item right away
    for e in sorted(queue, key=lambda x: x["publish_at"]):
        if e.get("status") not in ("uploaded", "ready") or not is_approved(e, ok):
            continue
        early = now_slug and e["slug"] == now_slug
        if datetime.fromisoformat(e["publish_at"]) > now and not early:
            continue
        if early:
            now_slug = ""
        if e["slug"] == "viksit-bharat":
            # Freshness rule: the source must still be live and inside the publish window.
            from sources.vb import still_fresh
            fresh, why = still_fresh(e.get("record_id", ""), e.get("posted"))
            if not fresh:
                print("held, not published:", e["slug"], e.get("video_id") or e["stem"], why)
                continue
        try:
            if e.get("platform") == "instagram":
                e["ig_media_id"] = post_instagram(e)
            else:
                srt = None
                if e.get("srt"):
                    srt = tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False)
                    srt.write(e["srt"])
                    srt.close()
                publish(e["slug"], e["video_id"], e["meta"], srt.name if srt else None)
        except Exception as ex:
            print("publish failed", e["slug"], e.get("video_id") or e["stem"], ex)
            continue
        e["status"] = "published"
        e["published_at"] = now.isoformat()
        changed = True
        print("published", e["slug"], e.get("video_id") or e.get("ig_media_id"), e["title"])
    if changed:
        QUEUE.write_text(json.dumps(queue, indent=1, ensure_ascii=False))
        update_issues(queue)


if __name__ == "__main__":
    main()
