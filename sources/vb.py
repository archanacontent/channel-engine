"""Source records for Viksit Bharat On Record.

Every record is one Press Information Bureau release, read in full from its own
page. A release is only used when it was posted within the freshness window
(10 days by default), carries real figures, and is not a greeting, a meeting or
anything to do with elections or parties.

Sectors rotate on a fixed 21-day cycle, so each of the 20 sectors gets one day
per cycle and the 21st day goes to whatever is newest. When the day's sector
has nothing fresh, the next sector in the cycle with a fresh release takes the
slot. A slot is never filled with an old figure.
"""
import re
from datetime import date, datetime, timedelta

from sources.fetch import get, rss_items, text_of

FEED = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
           "Accept-Language": "en-IN,en;q=0.9"}

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


def read_release(link):
    """One PIB release: its posting date, ministry, title and body text."""
    page = get(link, BROWSER, timeout=30)
    text = text_of(page, 40000)
    m = re.search(r"Posted On:?\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})", text)
    if not m:
        return None
    posted = datetime.strptime(re.sub(r"\s+", " ", m.group(1)).title(), "%d %b %Y").date()
    body = text[m.end():]
    body = re.sub(r"^\s*\d{1,2}:\d{2}\s*[AP]M\s*by\s*PIB\s*\w+", "", body).strip()
    body = body.split("***")[0].strip()
    head = text[:m.start()]
    ministry = ""
    mm = re.search(r"(Ministry of [A-Z][A-Za-z ,&]+?|Prime Minister's Office|Cabinet|NITI Aayog|"
                   r"Department of [A-Z][A-Za-z ,&]+?)(?=\s{1,3}[A-Z])", head[-600:])
    if mm:
        ministry = mm.group(1).strip()
    prid = re.search(r"PRID=(\d+)", link)
    return {"posted": posted, "ministry": ministry, "body": body[:4500],
            "prid": prid.group(1) if prid else link}


def _releases(max_age):
    try:
        items = list(rss_items(FEED))
    except Exception as e:
        print(f"  PIB feed failed: {e}")
        return []
    out = []
    cutoff = date.today() - timedelta(days=max_age)
    for it in items[:60]:
        if not it["link"] or SKIP.search(it["title"]):
            continue
        try:
            r = read_release(it["link"])
        except Exception as e:
            print(f"  PIB release failed {it['link']}: {e}")
            continue
        if not r or r["posted"] < cutoff or len(r["body"]) < 600 or SKIP.search(r["body"][:400]):
            continue
        if len(FIGURE.findall(r["body"])) < 2:
            continue
        r.update(title=it["title"].strip(), link=it["link"])
        out.append(r)
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


def next_record(series, day, used, avoid=(), max_age=10):
    """The freshest unused release for this series, today's sector first."""
    rels = sorted(fresh_releases(max_age), key=lambda r: r["posted"], reverse=True)
    order = [series] + [s for s in ("Myth vs Record", "While the World", "Then vs Now") if s != series]
    for s in order:
        for name, pattern in sector_order(day):
            rx = re.compile(pattern, re.I)
            for r in rels:
                rid = f"pib:{r['prid']}"
                if rid in used or rid in avoid or not fits(s, r):
                    continue
                if not rx.search(r["ministry"] + " " + r["title"] + " " + r["body"][:1500]):
                    continue
                released = r["posted"].strftime("%d %b %Y").lstrip("0")
                return {
                    "id": rid, "series": s, "sector": name, "headline": r["title"],
                    "released": released, "posted": r["posted"].isoformat(),
                    "facts": (f"Press Information Bureau release, posted {released}. "
                              f"{r['ministry'] + '. ' if r['ministry'] else ''}Title: {r['title']}. {r['body']}"),
                    "sources": [f"PIB, {r['ministry'] or 'Government of India'}, {released}: {r['link']}"],
                    "source_label": f"PIB release, {released}",
                }
    return None


def still_fresh(record_id, posted_iso, max_age=21):
    """Checked again just before a Short goes public: the release must still be
    live on PIB and no older than the publish window. Returns (ok, reason)."""
    if not record_id.startswith("pib:"):
        return True, ""
    if posted_iso:
        age = (date.today() - date.fromisoformat(posted_iso)).days
        if age > max_age:
            return False, f"source is {age} days old"
    link = f"https://pib.gov.in/PressReleasePage.aspx?PRID={record_id[4:]}"
    try:
        r = read_release(link)
    except Exception as e:
        return False, f"source page unreachable ({e})"
    if not r:
        return False, "source page no longer shows a release"
    return True, ""
