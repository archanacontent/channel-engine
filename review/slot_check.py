"""Runs after each posting slot. Publishes every Short that is ticked in an open
review issue and whose slot time has passed, then marks it published.

A Short that is never ticked stays private.
"""
import json
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


def main():
    queue = load(QUEUE, [])
    now = datetime.now(timezone.utc)
    ok = approved_keys(queue)
    changed = False
    for e in sorted(queue, key=lambda x: x["publish_at"]):
        if e.get("status") != "uploaded" or not is_approved(e, ok):
            continue
        if datetime.fromisoformat(e["publish_at"]) > now:
            continue
        srt = None
        if e.get("srt"):
            srt = tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False)
            srt.write(e["srt"])
            srt.close()
        try:
            publish(e["slug"], e["video_id"], e["meta"], srt.name if srt else None)
        except Exception as ex:
            print("publish failed", e["slug"], e["video_id"], ex)
            continue
        e["status"] = "published"
        e["published_at"] = now.isoformat()
        changed = True
        print("published", e["slug"], e["video_id"], e["title"])
    if changed:
        QUEUE.write_text(json.dumps(queue, indent=1, ensure_ascii=False))
        update_issues(queue)


if __name__ == "__main__":
    main()
