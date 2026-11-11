"""Runs the moment the review issue is edited: turns a ticked bulk box into
individual ticks and clears the bulk box, so the checklist shows exactly what
will post.

    python -m review.expand 7
"""
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from review.approvals import review_body, ticked

QUEUE = Path(__file__).resolve().parent.parent / "queue" / "current.json"


def week_of(e):
    d = date.fromisoformat(e["publish_at"][:10])
    return (d - timedelta(days=d.weekday())).isoformat()


def main(number):
    issue = json.loads(subprocess.run(["gh", "issue", "view", number, "--json", "title,body,labels"],
                                      capture_output=True, text=True, check=True).stdout)
    if "review" not in [l["name"] for l in issue["labels"]] or not issue["title"].startswith("Review: week of"):
        return
    week = issue["title"].rsplit(" ", 1)[-1]
    queue = json.loads(QUEUE.read_text()) if QUEUE.exists() else []
    entries = [e for e in queue if week_of(e) == week]
    body = review_body(entries, ticked(issue["body"], entries))
    if body.strip() != issue["body"].strip():
        subprocess.run(["gh", "issue", "edit", number, "--body", body], check=True)
        print("checklist updated")


if __name__ == "__main__":
    main(sys.argv[1])
