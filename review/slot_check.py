"""Runs after each posting slot. Publishes every Short that is ticked in an open
review issue and whose slot time has passed, then marks it published.

A Short that is never ticked stays private.
"""
import json
import subprocess
import tempfile
from datetime import datetime, timezone

from pipeline.upload import QUEUE, TICK, load, update_issues
from publish.youtube import publish


def ticked_ids():
    raw = subprocess.run(["gh", "issue", "list", "--label", "review", "--state", "open", "--json", "body",
                          "--limit", "20"], capture_output=True, text=True, check=True).stdout
    ids = set()
    for issue in json.loads(raw or "[]"):
        ids |= set(TICK.findall(issue["body"]))
    return ids


def main():
    queue = load(QUEUE, [])
    now = datetime.now(timezone.utc)
    ok = ticked_ids()
    changed = False
    for e in sorted(queue, key=lambda x: x["publish_at"]):
        if e.get("status") != "uploaded" or e.get("video_id") not in ok:
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
