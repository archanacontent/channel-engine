"""Gives every approved, uploaded YouTube Short to YouTube's own scheduler so it
goes public at its exact slot. Runs the moment the checklist is edited, after
every upload, and at each slot check. Anything whose slot has already passed
goes public right away.
"""
import json
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone

from pipeline.upload import QUEUE, load, update_issues, week_of
from publish.youtube import publish, schedule
from review.approvals import is_approved, ticked


def approved_keys(queue):
    raw = subprocess.run(["gh", "issue", "list", "--label", "review", "--state", "open", "--json", "title,body",
                          "--limit", "20"], capture_output=True, text=True, check=True).stdout
    keys = set()
    for issue in json.loads(raw or "[]"):
        week = issue["title"].rsplit(" ", 1)[-1]
        keys |= ticked(issue["body"], [e for e in queue if week_of(e) == week])
    return keys


def main():
    queue = load(QUEUE, [])
    ok = approved_keys(queue)
    now = datetime.now(timezone.utc)
    changed = False
    for e in sorted(queue, key=lambda x: x["publish_at"]):
        if e.get("platform") == "instagram" or e.get("status") != "uploaded" or not is_approved(e, ok):
            continue
        srt = None
        if e.get("srt"):
            srt = tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False)
            srt.write(e["srt"])
            srt.close()
        when = datetime.fromisoformat(e["publish_at"]).astimezone(timezone.utc)
        try:
            if when > now + timedelta(minutes=10):
                schedule(e["slug"], e["video_id"], e["meta"], srt.name if srt else None,
                         when.strftime("%Y-%m-%dT%H:%M:%SZ"))
                e["status"] = "scheduled"
                print("scheduled", e["slug"], e["video_id"], when.isoformat(), e["title"])
            else:
                publish(e["slug"], e["video_id"], e["meta"], srt.name if srt else None)
                e["status"] = "published"
                print("published now", e["slug"], e["video_id"], e["title"])
            e["published_at"] = when.isoformat()
            changed = True
        except Exception as ex:
            print("could not schedule", e["slug"], e["video_id"], ex)
    if changed:
        QUEUE.write_text(json.dumps(queue, indent=1, ensure_ascii=False))
        update_issues(queue)


if __name__ == "__main__":
    main()
