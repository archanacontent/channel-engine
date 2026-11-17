"""A second, independent read of every script before it reaches review.

The writer's own checks confirm that every number appears in the source. This
pass reads the finished script against the source the way an editor would and
rejects it if any sentence says more than the source supports, presents an
older figure as current, credits the wrong body, or claims for today's
government something the source says began earlier.
"""
import json

from pipeline.write import generate

SYSTEM = """You are a strict fact-checker for a news Shorts channel. You get SOURCE (an official release, or a news report of official figures)
and SCRIPT (what the video will say and show). Check every sentence, caption and on-screen text in SCRIPT.
Report a problem when:
- a claim, figure, date, rank or comparison is not directly stated in SOURCE, or is stated more strongly than SOURCE does;
- a figure is presented as current or new while SOURCE dates it to an earlier period;
- a figure is credited to the wrong ministry or body;
- the script credits the current government with something SOURCE says began before 2014;
- the script names a party, an election, or praises a politician.
The opening myth line in a 'Myth vs Record' Short is framing, not a claim, and is fine as long as it is not
attributed to anyone. Questions to the viewer are fine.
Return JSON only: {"ok": true|false, "problems": ["one line each, quoting the exact words at fault"]}"""


def verify(record, ep):
    script = {
        "title": ep.get("title"),
        "beats": [{"say": b.get("say"), "on_screen": b.get("scene")} for b in ep.get("beats", [])],
        "description": {k: v for k, v in (ep.get("description") or {}).items() if k != "sources"},
    }
    user = f"SOURCE:\n{record['facts']}\n\nSCRIPT:\n{json.dumps(script, ensure_ascii=False, indent=1)}"
    out = generate(SYSTEM, user, {"type": "OBJECT", "properties": {
        "ok": {"type": "BOOLEAN"}, "problems": {"type": "ARRAY", "items": {"type": "STRING"}}},
        "required": ["ok", "problems"]})
    problems = [str(p) for p in out.get("problems") or []]
    return bool(out.get("ok")) and not problems, problems
