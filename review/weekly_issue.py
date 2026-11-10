"""Opens the Sunday review issue: one checkbox per Short, grouped by day and slot.

Input: queue.json written by the Sunday render, a list of
{"slug", "channel", "series", "title", "video_id", "publish_at"}.
Ticked boxes are read back at each slot by review/slot_check.py.
"""
import json
import os
import subprocess
import sys
from collections import defaultdict


def body(queue):
    by_day = defaultdict(list)
    for q in sorted(queue, key=lambda x: x["publish_at"]):
        by_day[q["publish_at"][:10]].append(q)
    out = ["Tick each Short you approve. Unticked Shorts stay private and never post.",
           "Watch them in the YouTube Studio app under Content > Private.", ""]
    for day, items in by_day.items():
        out.append(f"### {day}")
        for q in items:
            link = f"https://studio.youtube.com/video/{q['video_id']}/edit"
            out.append(f"- [ ] `{q['video_id']}` {q['publish_at'][11:16]} · **{q['channel']}** · {q['series']}: "
                       f"[{q['title']}]({link})")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    queue = json.load(open(sys.argv[1]))
    week = queue[0]["publish_at"][:10]
    subprocess.run(["gh", "issue", "create", "--title", f"Review: week of {week}", "--label", "review",
                    "--body", body(queue)], check=True, env=os.environ)
