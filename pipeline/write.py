"""Turns one source record into an episode script with Gemini (free tier).

The model may use only the facts in the record. Every script is checked before
it is accepted: length, beat count, scene shapes, no dashes, every number in the
captions present in the source, and quoted passages copied exactly. A script
that fails is sent back with the errors, twice at most, then the record is
skipped.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

MODELS = os.environ.get("GEMINI_MODELS",
                        "gemini-3.6-flash,gemini-2.5-flash,gemini-3.5-flash-lite,gemini-2.5-flash-lite").split(",")
API = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
SCENES = {"headline", "stat", "card", "list", "compare", "flow", "image", "sizes", "quote", "cta"}

VOICE = """Writing rules, all mandatory:
- Plain, confident, specific. Premium B2B tone for business channels, curious and clear for Space Science.
- Use only facts present in SOURCE. Never add a number, date, name, product, statistic or claim that SOURCE does not state.
- No em dashes or en dashes anywhere. No emojis. No hashtags in the script.
- No filler openers such as "In this video", "Did you know", "Let's dive in", "Here's the thing".
- Vary sentence length. No three-item rhythm in every sentence. No hedging.
- First beat is the hook: the single most useful or surprising fact, stated outright in under 15 words.
- Each "say" is what the voice reads; spell out anything a voice would misread (write "C V E 2026, 1 2 3 4" style IDs out, "S S H", "n eight n").
- "caption" is the same sentence as "say" in normal written form (IDs, numbers and symbols as written)."""

SERIES_GUIDE = {
    "Buyers Asked": "Pick ONE question from the autocomplete suggestions that a B2B buyer would really ask. Beat 1 states the question. Then explain what a page must say to be the answer AI search cites. Use a 'quote' or 'list' scene for the answer structure. Close: 'Find your buyers' questions with Asked, link on our channel page.'",
    "The Fix": "Teach the rule from SOURCE using a page about the named keyword. Show a short weak line and a rewritten line in a 'compare' scene (write both yourself; they illustrate the rule and contain no statistics). Close: 'The full standard is linked on our channel page.'",
    "Trend Check": "Report the AI search development in SOURCE: what changed, who it affects, what B2B marketers should do. Name the publication in one beat. Close: 'Source in the description.'",
    "Stop Doing This": "Frame the manual marketing task this template removes. Show the workflow as a 'flow' scene built from the node types in SOURCE (2 to 4 steps, plain names). Close: 'The free template is linked in the description.'",
    "Library Pick": "Present the template as a pick from n8n's public library: what it does, the steps, who it suits. Use a 'flow' scene. Close: 'Template link in the description.'",
    "Can It Be Automated?": "Open with the question 'Can you automate <task>?' and answer yes, then show how with a 'flow' scene. Close: 'Template link in the description.'",
    "Exploited Today": "Report the actively exploited vulnerability: product, what the flaw allows, KEV date, due date, required action. Use a 'card' scene with CVE ID, product, added date, due date, and a 'list' scene for actions. Close: 'Sources are in the description.'",
    "Breach Watch": "Report what the company disclosed in its SEC 8-K Item 1.05: when it found the incident, what was affected, what it did. Only what the filing says. Use a 'card' scene. Never name individuals. Close: 'The filing is linked in the description.'",
    "Scam Alert": "Explain the scam from the FTC alert: how it works, the warning signs, what to do. Use a 'list' scene for warning signs or steps. Close: 'More in the FTC alert linked in the description.'",
    "Rewrite This": "Choose one or two sentences from the README prose in SOURCE that are wordy, vague or confusing. Quote them EXACTLY, character for character, as compare.left_text. Write a clearer version as compare.right_text. Explain each edit in plain words. Do not mock the project. Close with the rule in one line using a 'quote' scene.",
    "One Rule": "Teach the single writing rule from SOURCE in your own words. Show a weak example and a better example you write yourself in a 'compare' scene. Credit Google's developer documentation in one beat. Close with the rule in a 'quote' scene.",
    "Doc Types": "Explain what this doc type is for and what it must contain, using SOURCE. Use a 'list' scene for its must-have parts. Close with one rule for writing it in a 'quote' scene.",
    "Look Closer": "Explain what the NASA image shows using SOURCE: what it is, where, how big or far, why it matters. Beat 1 or 2 uses an 'image' scene. Close: 'Image credit in the description.'",
    "Mission Log": "Report the NASA update from SOURCE: what happened, the mission, why it matters. Use 'card' or 'stat' scenes for key facts. Close: 'Source in the description.'",
    "Scale It": "Compare the two bodies' sizes from SOURCE. Use a 'sizes' scene with the two diameters, and a relatable comparison only if it follows from the ratio. Close: 'Figures from NASA's Planetary Fact Sheet.'",
}

SCHEMA = """Return JSON only, in this shape:
{"skip": false, "skip_reason": "",
 "title": "<= 90 characters, follows the series title pattern",
 "beats": [ {"say": "...", "caption": "...", "highlight": ["1 to 3 exact phrases from caption"], "scene": {...}} ],
 "description": { <fields listed below> },
 "seo": {"seeds": ["3 or 4 search phrases a viewer would type, specific to this video"], "hashtags": ["#Two", "#Specific"]}}
Rules for beats: 4 to 6 beats, 80 to 125 words of "say" in total, each beat 1 or 2 sentences.
Scene types and fields (use different types across beats, last beat is usually "cta" or "quote"):
 headline {kicker?, text} | stat {value, label, source?} | card {title, rows: [[label, value]] up to 5}
 list {title, items: up to 4 short items, style: check|number|bullet} | compare {left_label, left_text, right_label, right_text}
 flow {steps: [{title, note}] 2 to 4} | image {credit} | sizes {a_label, a_value, b_label, b_value, unit}
 quote {text, highlight: [phrases]} | cta {line, subline}
Scene text must be short: headline under 14 words, list items under 9 words, card values under 6 words.
If SOURCE does not contain enough real material for a strong Short, return {"skip": true, "skip_reason": "..."}."""


def _call(model, system, user, key):
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
    }).encode()
    req = urllib.request.Request(API.format(m=model), data=body, method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def generate(system, user):
    key = os.environ["GEMINI_API_KEY"]
    last = None
    for model in MODELS:
        for attempt in range(4):
            try:
                out = _call(model.strip(), system, user, key)
                time.sleep(4)
                return json.loads(out)
            except urllib.error.HTTPError as e:
                last = f"{model}: HTTP {e.code} {e.read()[:300]!r}"
                print("  gemini", last, flush=True)
                if e.code in (429, 500, 503):
                    time.sleep(15 * (attempt + 1))
                    continue
                break
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                last = f"{model}: bad response {e}"
                time.sleep(3)
                continue
    raise RuntimeError(f"Gemini unavailable: {last}")


def _norm_num(s):
    return s.replace(",", "").rstrip(".")


def check(ep, record, desc_fields):
    errs = []
    beats = ep.get("beats") or []
    if not 4 <= len(beats) <= 6:
        errs.append(f"Need 4 to 6 beats, got {len(beats)}.")
    words = sum(len(str(b.get("say", "")).split()) for b in beats)
    if not 70 <= words <= 135:
        errs.append(f"'say' totals {words} words; need 80 to 125.")
    facts = record["facts"]
    facts_nums = {_norm_num(n) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", facts)}
    flat_facts = re.sub(r"\s+", " ", facts)
    for i, b in enumerate(beats):
        for k in ("say", "caption"):
            if not str(b.get(k, "")).strip():
                errs.append(f"Beat {i + 1} is missing '{k}'.")
        sc = b.get("scene") or {}
        if sc.get("type") not in SCENES:
            errs.append(f"Beat {i + 1} has unknown scene type {sc.get('type')!r}.")
        text = json.dumps(b, ensure_ascii=False)
        if "—" in text or "–" in text:
            errs.append(f"Beat {i + 1} uses a dash character; rewrite without it.")
        for n in re.findall(r"\d[\d,]*(?:\.\d+)?", str(b.get("caption", "")) + " " + json.dumps(sc)):
            nn = _norm_num(n)
            if nn not in facts_nums and not (nn.isdigit() and int(nn) <= 12):
                errs.append(f"Beat {i + 1} uses the number {n}, which is not in SOURCE.")
        if sc.get("type") == "compare" and record["series"] == "Rewrite This":
            left = re.sub(r"\s+", " ", str(sc.get("left_text", ""))).strip()
            if not left or left not in flat_facts:
                errs.append("compare.left_text must be copied exactly from the README prose in SOURCE.")
    if len(str(ep.get("title", ""))) > 95 or not ep.get("title"):
        errs.append("Title missing or longer than 90 characters.")
    missing = [f for f in desc_fields if not (ep.get("description") or {}).get(f)]
    if missing:
        errs.append(f"description is missing fields: {missing}.")
    return errs


def write_episode(brand, record):
    desc_fields = [f for f in re.findall(r"{(\w+)}", brand["description_template"])
                   if f not in ("youtube_hashtags", "source_links", "template_link", "library_link",
                                "source_link", "license", "credit")]
    title_pattern = brand["titles"].get(record["series"], "{topic}")
    system = (f"You write YouTube Shorts scripts for the channel '{brand['name']}'. Channel promise: "
              f"{brand['positioning']} Audience and focus: {brand['description']}\n\n{VOICE}\n\n"
              f"Series '{record['series']}': {SERIES_GUIDE.get(record['series'], '')}\n"
              f"Title pattern for this series: {title_pattern}\n"
              f"Description fields to fill (one or two plain sentences each, first field answers the viewer's question "
              f"outright and names the subject): {desc_fields}\n\n{SCHEMA}")
    user = f"SOURCE (the only facts you may use):\n{record['facts']}\n\nSOURCE LINKS: {record['sources']}"
    errs = []
    for _ in range(3):
        prompt = user if not errs else user + "\n\nYour previous answer failed these checks, fix all of them:\n- " + "\n- ".join(errs)
        ep = generate(system, prompt)
        if ep.get("skip"):
            return None, ep.get("skip_reason", "model skipped")
        for b in ep.get("beats", []):
            for k in ("say", "caption"):
                b[k] = str(b.get(k, "")).replace(" — ", ", ").replace("—", ", ").replace("–", "-")
            b["highlight"] = [h for h in (b.get("highlight") or []) if str(h).lower() in b["caption"].lower()][:3]
            if (b.get("scene") or {}).get("type") == "sizes" and record.get("scale"):
                b["scene"].update(record["scale"], unit="km")
        errs = check(ep, record, desc_fields)
        if errs:
            print(f"  check failed ({record['id']}):", "; ".join(errs[:5]), flush=True)
        if not errs:
            ep["description"]["sources"] = record["sources"]
            if record.get("credit"):
                ep["description"]["credit"] = record["credit"]
            if record["series"] == "Rewrite This":
                ep["description"]["source_link"] = record["sources"][0].split(": ", 1)[-1]
                ep["description"]["license"] = record.get("license", "")
            if record["sources"] and "n8n.io/workflows" in record["sources"][0]:
                ep["description"]["template_link"] = record["sources"][0].split(": ", 1)[-1]
            return ep, None
    return None, "; ".join(errs[:4])
