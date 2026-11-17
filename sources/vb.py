"""Source records for Viksit Bharat On Record.

PIB refuses cloud servers, so the daily run reads official figures as reported
by business papers whose feeds answer it (BusinessLine, Economic Times, Mint)
and RBI's own press releases. A story is used only when it quotes an official
body, carries real figures, was published within the freshness window (10 days
by default) and has nothing to do with elections or parties. Each record keeps
the official body and the paper, so the Short credits both.

Sectors rotate on a fixed 21-day cycle, so each of the 20 sectors gets one day
per cycle and the 21st day goes to whatever is newest. When the day's sector
has nothing fresh, the next sector in the cycle with a fresh release takes the
slot. A slot is never filled with an old figure.
"""
import json
import re
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from sources.fetch import get, rss_items, text_of

NEWS_FEEDS = [
    ("BusinessLine", "https://www.thehindubusinessline.com/economy/feeder/default.rss"),
    ("Economic Times", "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms"),
    ("Mint", "https://www.livemint.com/rss/economy"),
]
OFFICIAL = re.compile(r"\b(?:PIB|Ministry|Minister|NPCI|RBI|Reserve Bank|NSO|MoSPI|EPFO|ISRO|DPIIT|NITI Aayog|"
                      r"GST Council|CBIC|government data|official data|the Centre|Union government|"
                      r"government said|Department of|Statistics|Railways|NHAI|SEBI|data released)\b")
POSITIVE = re.compile(r"\b(?:record|highest|all-time|rise[sn]?|rose|grow(?:s|th|n)?|grew|surge[sd]?|jump(?:s|ed)?|"
                      r"cross(?:es|ed)|milestone|first|largest|biggest|top|up \d|doubl\w*|expan\w*|boost\w*|"
                      r"increase[sd]?|beat|overtak\w*|fastest|launch(?:es|ed)?|inaugurat\w*|complet\w*)\b", re.I)
NEGATIVE = re.compile(r"\b(?:slump|plunge|contract(?:s|ed|ion)|decline[sd]?|falls?|fell|drop(?:s|ped)?|"
                      r"slow(?:s|ed|down)|deficit widens|lowest|worst|crisis|shortfall|price rise|stock limits?|curbs?|ban(?:s|ned)?|"
                      r"inflation|probe|penalty|fine[sd]?)\b", re.I)

# 21-day cycle: three weeks of seven, the last day open for the newest release.
SECTORS = [
    ("Roads, Rail and Metro", r"Railways|Road Transport|Highways|metro|rail|expressway|Vande Bharat|freight corridor"),
    ("Health and Medicine", r"Health|AYUSH|hospital|medical|vaccin|Ayushman|AIIMS|doctor"),
    ("Digital Payments and IT", r"Electronics and Information Technology|UPI|digital|Aadhaar|DigiLocker|NPCI|broadband|5G|data centre"),
    ("Space", r"Space|ISRO|satellite|launch vehicle|Gaganyaan|Chandrayaan|IN-SPACe"),
    ("Farming and Food", r"Agriculture|Farmers|Food Processing|Fisheries|Animal Husbandry|crop|kharif|rabi|procurement|PM-KISAN"),
    ("Energy", r"New and Renewable Energy|Power|Petroleum|Coal|solar|wind|nuclear|green hydrogen|renewable|gigawatt|\bGW\b"),
    ("Sports", r"Youth Affairs and Sports|medal|Khelo India|championship|Olympic|Paralympic|athlete"),
    ("Defence and Defence Exports", r"Defence|DRDO|Indian Navy|Indian Army|Indian Air Force|defence export|indigenous"),
    ("Electronics and Manufacturing", r"Heavy Industries|Commerce and Industry|Steel|Textiles|PLI|manufactur|semiconductor|Make in India"),
    ("Startups and Markets", r"startup|DPIIT|SEBI|stock market|investment|\bFDI\b|MSME|Micro, Small"),
    ("Education and Skills", r"Education|Skill Development|university|IIT|school|scholarship|apprentice"),
    ("Housing, Water and Sanitation", r"Housing and Urban Affairs|Jal Shakti|Drinking Water|Swachh|PMAY|tap water|sanitation"),
    ("Aviation and Ports", r"Civil Aviation|Ports, Shipping|airport|UDAN|\bports?\b|shipping|cargo|maritime"),
    ("Tourism, Culture and Heritage", r"Tourism|Culture|heritage|UNESCO|museum|tourist"),
    ("Jobs and the Economy", r"Finance|Labour and Employment|Statistics|GDP|EPFO|employment|GST|inflation|exports|revenue"),
    ("Women-led Development", r"Women and Child Development|women|Lakhpati Didi|self help group|SHG|girl"),
    ("Environment and Wildlife", r"Environment, Forest|tiger|forest|wildlife|Ramsar|wetland|emission|climate"),
    ("Science and Research", r"Science & Technology|Science and Technology|Earth Sciences|CSIR|research and development|patent|quantum"),
    ("Trade and Diplomacy", r"External Affairs|Commerce|trade agreement|FTA|bilateral|export"),
    ("EVs and Auto", r"electric vehicle|\bEVs?\b|e-bus|automobile|PM E-DRIVE|charging station"),
    ("Newest Release", r"."),
]

SKIP = re.compile(r"condolence|greets|greetings|pays tribute|tributes|wishes|calls on|meets |meeting with|"
                  r"election|BJP|Congress|political party|Rajya Sabha question|Lok Sabha question|"
                  r"birth anniversary|death anniversary|obituary|curtain raiser|swearing", re.I)
FIGURE = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:%|per cent|percent|crore|lakh|million|billion|trillion|km|GW|MW|"
                    r"tonnes|times|fold|x\b)", re.I)
SINCE_2014 = re.compile(r"\b(?:2014|2013-14|2014-15)\b")
GLOBAL = re.compile(r"\b(?:world|global|globally|largest|fastest|first country|top \d+|rank(?:ed|s)?|"
                    r"second[- ]largest|third[- ]largest|among the)\b", re.I)


def sector_order(d):
    """Today's sector first, then the rest of the cycle in order."""
    i = d.toordinal() % len(SECTORS)
    return SECTORS[i:] + SECTORS[:i]


def _date(it):
    try:
        return parsedate_to_datetime(it["date"]).date()
    except Exception:
        return None


def read_story(outlet, it):
    """One story: the feed text, extended with the article page when it answers."""
    body = text_of(it.get("content") or it.get("description") or "", 4000)
    if len(body) < 900 and it["link"]:
        try:
            page = text_of(get(it["link"], timeout=30), 30000)
            i = page.find(it["title"][:40])
            page = page[i:i + 4500] if i >= 0 else page[:4500]
            if len(page) > len(body):
                body = page
        except Exception:
            pass
    return body


def _releases(max_age):
    out = []
    cutoff = date.today() - timedelta(days=max_age)
    for outlet, feed in NEWS_FEEDS:
        try:
            items = list(rss_items(feed))
        except Exception as e:
            print(f"  {outlet} feed failed: {e}")
            continue
        for it in items[:40]:
            posted = _date(it)
            title = re.sub(r"<!\[CDATA\[|\]\]>", "", it["title"]).strip()
            if not it["link"] or not posted or posted < cutoff or SKIP.search(title):
                continue
            if NEGATIVE.search(title) or not POSITIVE.search(title):
                continue
            body = read_story(outlet, dict(it, title=title))
            blob = title + " " + body
            if len(body) < 300 or len(FIGURE.findall(blob)) < 2 or SKIP.search(body[:600]):
                continue
            if not OFFICIAL.search(blob):
                continue
            out.append({"posted": posted, "outlet": outlet, "title": title, "body": body[:4500],
                        "link": it["link"], "ministry": outlet if outlet == "RBI" else ""})
    print(f"  fresh official-figure stories: {len(out)}")
    return out


_CACHE = {}


def fresh_releases(max_age=10):
    if max_age not in _CACHE:
        _CACHE[max_age] = _releases(max_age)
    return _CACHE[max_age]


def fits(series, r):
    blob = r["title"] + " " + r["body"]
    if series == "Then vs Now":
        return bool(SINCE_2014.search(blob))
    if series == "While the World":
        return bool(GLOBAL.search(blob))
    return True


FAILED = Path(__file__).resolve().parent.parent / "state" / "vb_failed.json"


def remember_failed(rid):
    """A story whose script failed the checks is not tried again on later runs."""
    ids = set(json.loads(FAILED.read_text())) if FAILED.exists() else set()
    ids.add(rid)
    FAILED.write_text(json.dumps(sorted(ids)[-500:], indent=0))


def next_record(series, day, used, avoid=(), max_age=10):
    """The freshest unused story for this series, today's sector first."""
    if FAILED.exists():
        used = set(used) | set(json.loads(FAILED.read_text()))
    rels = sorted(fresh_releases(max_age), key=lambda r: r["posted"], reverse=True)
    order = [series] + [s for s in ("Myth vs Record", "While the World", "Then vs Now") if s != series]
    for s in order:
        for name, pattern in sector_order(day):
            rx = re.compile(pattern, re.I)
            for r in rels:
                rid = f"vbnews:{r['link']}"
                if rid in used or rid in avoid or not fits(s, r):
                    continue
                if not rx.search(r["title"] + " " + r["body"][:1500]):
                    continue
                released = r["posted"].strftime("%d %b %Y").lstrip("0")
                return {
                    "id": rid, "series": s, "sector": name, "headline": r["title"],
                    "released": released, "posted": r["posted"].isoformat(),
                    "facts": (f"{r['outlet']}, published {released}. Title: {r['title']}. {r['body']}"),
                    "sources": [f"{r['outlet']}, {released}: {r['link']}"],
                    "source_label": f"{r['outlet']}, {released}",
                }
    return None


def still_fresh(record_id, posted_iso, max_age=21):
    """Checked again before a Short is released: the story must be inside the publish window."""
    if posted_iso:
        age = (date.today() - date.fromisoformat(posted_iso)).days
        if age > max_age:
            return False, f"source is {age} days old"
    return True, ""
