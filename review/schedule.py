"""Keeps YouTube in line with the plan. Everything posts automatically:

1. Releases: every uploaded Short that is not stopped gets its exact slot in YouTube's
   own scheduler (or goes public now if its slot has passed). A Short ticked in the
   checklist is stopped (private, no release time); unticking it schedules it again.
2. Extras: series playlist and the exact caption file, retried on every run until done,
   since they share the 10,000-unit daily API quota.

Runs after every upload, whenever the checklist is edited, and at each slot check.
"""
import json
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone

from pipeline.upload import QUEUE, load, update_issues, week_of
from publish.youtube import add_captions, add_playlist, hold, publish, schedule, set_description
from render.seo import with_keywords
from review.approvals import is_held, ticked


def stopped_keys(queue):
    raw = subprocess.run(["gh", "issue", "list", "--label", "review", "--state", "open", "--json", "title,body",
                          "--limit", "20"], capture_output=True, text=True, check=True).stdout
    keys = set()
    for issue in json.loads(raw or "[]"):
        week = issue["title"].rsplit(" ", 1)[-1]
        keys |= ticked(issue["body"], [e for e in queue if week_of(e) == week])
    return keys


def quota(ex):
    return "quota" in str(ex).lower()


def main():
    queue = load(QUEUE, [])
    stop = stopped_keys(queue)
    now = datetime.now(timezone.utc)
    yt = [e for e in sorted(queue, key=lambda x: x["publish_at"])
          if e.get("platform", "youtube") != "instagram" and e.get("video_id")]
    changed = False
    # 1. releases
    for e in yt:
        held = is_held(e, stop)
        when = datetime.fromisoformat(e["publish_at"]).astimezone(timezone.utc)
        try:
            if held and e["status"] in ("uploaded", "scheduled", "published"):
                hold(e["slug"], e["video_id"], e["meta"])
                e["status"] = "held"
                print("stopped", e["slug"], e["video_id"], e["title"])
            elif not held and e["status"] in ("uploaded", "held"):
                if when > now + timedelta(minutes=10):
                    schedule(e["slug"], e["video_id"], e["meta"], None, when.strftime("%Y-%m-%dT%H:%M:%SZ"))
                    e["status"] = "scheduled"
                    print("scheduled", e["slug"], e["video_id"], when.isoformat(), e["title"])
                else:
                    publish(e["slug"], e["video_id"], e["meta"])
                    e["status"] = "published"
                    print("released now", e["slug"], e["video_id"], e["title"])
                e["published_at"] = when.isoformat()
            else:
                continue
            changed = True
        except Exception as ex:
            print("release step failed", e["slug"], e["video_id"], str(ex)[:160])
            if quota(ex):
                break
    # 2. extras, nearest release first
    for e in yt:
        if e["status"] not in ("scheduled", "published"):
            continue
        try:
            if e["meta"].get("playlist") and not e.get("playlist_done"):
                add_playlist(e["slug"], e["video_id"], e["meta"])
                e["playlist_done"] = True
                changed = True
            if not e.get("keywords_done"):
                desc = with_keywords(e["slug"], e["meta"])
                set_description(e["slug"], e["video_id"], e["meta"], desc)
                e["meta"]["youtube_description"] = desc
                e["keywords_done"] = True
                changed = True
            if e.get("srt") and not e.get("captions_done"):
                with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False) as f:
                    f.write(e["srt"])
                add_captions(e["slug"], e["video_id"], e["meta"], f.name)
                e["captions_done"] = True
                changed = True
        except Exception as ex:
            print("extras pending", e["slug"], e["video_id"], str(ex)[:120])
            if quota(ex):
                print("daily API quota reached; playlist and captions continue on the next run")
                break
    if changed:
        QUEUE.write_text(json.dumps(queue, indent=1, ensure_ascii=False))
        update_issues(queue)


if __name__ == "__main__":
    main()
