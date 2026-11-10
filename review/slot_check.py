"""Runs at each slot. Publishes only the Shorts ticked in the open review issue."""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from publish.youtube import make_public

TICKED = re.compile(r"- \[x\] `([A-Za-z0-9_-]{11})`", re.I)


def ticked_ids():
    raw = subprocess.run(["gh", "issue", "list", "--label", "review", "--state", "open", "--json", "body",
                          "--limit", "1"], capture_output=True, text=True, check=True).stdout
    issues = json.loads(raw)
    return set(TICKED.findall(issues[0]["body"])) if issues else set()


if __name__ == "__main__":
    queue = json.load(open(sys.argv[1]))
    now = datetime.now(timezone.utc)
    ok = ticked_ids()
    for q in queue:
        due = datetime.fromisoformat(q["publish_at"])
        if now - timedelta(minutes=30) <= due <= now + timedelta(minutes=5) and q["video_id"] in ok:
            make_public(q["slug"], q["video_id"])
            print("published", q["slug"], q["video_id"])
