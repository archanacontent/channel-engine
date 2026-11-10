"""Daily source fetchers, one per series.

Every fetcher returns records: real, dated material the script writer turns
into one Short. A record is never used twice (state/used.json keeps the ids).

record = {
  "id": unique id, "series": series name, "headline": short label,
  "facts": the text the script may use (and nothing else),
  "sources": ["Label: https://..."], "image_url": optional, "credit": optional,
}
"""
import html
import itertools
import json
import re
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = yaml.safe_load((ROOT / "sources" / "catalog.yaml").read_text())
UA = "ChannelEngine/1.0 (creativecontent707@gmail.com)"


def get(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def get_json(url, headers=None):
    return json.loads(get(url, headers))


def text_of(markup, limit=4000):
    markup = re.sub(r"(?is)<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>", " ", markup)
    t = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    return re.sub(r"\s+", " ", t).strip()[:limit]


def rss_items(url):
    root = ET.fromstring(get(url).encode("utf-8"))
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    for it in root.iter("item"):
        yield {
            "title": (it.findtext("title") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "date": (it.findtext("pubDate") or "").strip(),
            "description": it.findtext("description") or "",
            "content": it.findtext("content:encoded", namespaces=ns) or "",
        }


def autocomplete(q):
    try:
        data = json.loads(get("https://suggestqueries.google.com/complete/search?client=firefox&hl=en&q="
                              + urllib.parse.quote(q)))
        return [s for s in data[1] if isinstance(s, str)]
    except Exception:
        return []


# ---------------- AI Search Marketing ----------------

def buyers_asked(used):
    for k in CATALOG["b2b_keywords"]:
        rid = f"asked:{k}"
        if rid in used:
            continue
        found = {}
        for pattern in ("what is {k}", "how to choose {k}", "{k} vs", "is {k} worth it", "best {k} for",
                        "how much does {k} cost", "why {k}"):
            q = pattern.format(k=k)
            hits = [s for s in autocomplete(q) if s.lower() != q.lower()][:5]
            if hits:
                found[q] = hits
        if not found:
            continue
        lines = [f"Google autocomplete for '{q}' suggests: " + "; ".join(h) for q, h in found.items()]
        yield {"id": rid, "series": "Buyers Asked", "headline": k,
               "facts": f"Keyword: {k}. Collected {date.today().isoformat()} with the Asked method. " + " ".join(lines),
               "sources": ["Asked, free AEO and GEO question finder: https://archanacontent.github.io/asked/"]}


def the_fix(used):
    rules, kws = CATALOG["citable_rules"], CATALOG["b2b_keywords"]
    for i in range(len(rules) * len(kws)):
        rule, k = rules[i % len(rules)], kws[(i * 7) % len(kws)]
        rid = f"fix:{rule['id']}:{k}"
        if rid in used:
            continue
        yield {"id": rid, "series": "The Fix", "headline": f"{rule['name']} for {k}",
               "facts": (f"Rule from The Citable Passage Standard: {rule['name']}. {rule['rule']} "
                         f"Apply it to a page about {k}. The standard is part of the Asked Method by Archana Panda."),
               "sources": ["The Citable Passage Standard: https://archanacontent.github.io/asked/standard/"]}


def trend_check(used):
    terms = [t.lower() for t in CATALOG["ai_search_terms"]]
    for feed in CATALOG["ai_search_feeds"]:
        try:
            items = list(rss_items(feed))
        except Exception:
            continue
        for it in items[:30]:
            blob = (it["title"] + " " + text_of(it["description"])).lower()
            if not it["link"] or f"news:{it['link']}" in used or not any(t.lower() in blob for t in terms):
                continue
            body = text_of(it["content"] or it["description"], 3500)
            if len(body) < 1200:
                try:
                    page = text_of(get(it["link"]), 9000)
                    i = page.find(it["title"][:40])
                    page = page[i: i + 3500] if i >= 0 else page[:3500]
                    if len(page) > len(body):
                        body = page
                except Exception:
                    pass
            if len(body) < 250:
                continue
            yield {"id": f"news:{it['link']}", "series": "Trend Check", "headline": it["title"],
                   "facts": f"Published {it['date']}. Title: {it['title']}. {body}",
                   "sources": [f"{it['title']}: {it['link']}"]}


# ---------------- Marketing Automation Library ----------------

def n8n_templates(used, series):
    seen = 0
    for page in range(1, 6):
        try:
            data = get_json(f"https://api.n8n.io/api/templates/search?rows=50&page={page}&search=marketing")
        except Exception:
            return
        flows = data.get("workflows") or []
        if not flows:
            return
        for w in flows:
            rid = f"n8n:{w.get('id')}"
            if rid in used:
                continue
            try:
                full = get_json(f"https://api.n8n.io/api/templates/workflows/{w['id']}")
                wf = full.get("workflow", full)
            except Exception:
                continue
            nodes = wf.get("workflow", {}).get("nodes") or wf.get("nodes") or []
            names = [n.get("type", "").split(".")[-1] for n in nodes if not n.get("type", "").endswith("stickyNote")]
            desc = text_of(wf.get("description") or w.get("description") or "", 2500)
            if len(desc) < 120:
                continue
            seen += 1
            yield {"id": rid, "series": series, "headline": wf.get("name") or w.get("name"),
                   "facts": (f"n8n community template '{wf.get('name') or w.get('name')}'. Node types in order: "
                             f"{', '.join(names[:12])}. Template description: {desc}"),
                   "sources": [f"n8n template: https://n8n.io/workflows/{w['id']}"]}


# ---------------- Cybersecurity Daily ----------------

def exploited_today(used):
    data = None
    for url in ("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
                "https://raw.githubusercontent.com/cisagov/kev-data/main/known_exploited_vulnerabilities.json"):
        try:
            data = get_json(url)
            break
        except Exception:
            continue
    if not data:
        return
    for v in sorted(data["vulnerabilities"], key=lambda x: x["dateAdded"], reverse=True)[:60]:
        rid = f"kev:{v['cveID']}"
        if rid in used:
            continue
        nvd = ""
        try:
            n = get_json(f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={v['cveID']}")
            cve = n["vulnerabilities"][0]["cve"]
            nvd = next((x["value"] for x in cve.get("descriptions", []) if x["lang"] == "en"), "")
            m = cve.get("metrics", {})
            for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30"):
                if m.get(key):
                    c = m[key][0]["cvssData"]
                    nvd += f" CVSS base score {c.get('baseScore')} ({c.get('baseSeverity')})."
                    break
        except Exception:
            pass
        facts = (f"CISA Known Exploited Vulnerabilities entry. CVE ID: {v['cveID']}. Vendor: {v['vendorProject']}. "
                 f"Product: {v['product']}. Name: {v['vulnerabilityName']}. Added to KEV: {v['dateAdded']}. "
                 f"Federal remediation due date: {v['dueDate']}. CISA description: {v['shortDescription']} "
                 f"Required action: {v['requiredAction']} Known ransomware use: {v.get('knownRansomwareCampaignUse')}. "
                 f"NVD description: {nvd}")
        yield {"id": rid, "series": "Exploited Today", "headline": f"{v['vendorProject']} {v['product']} {v['cveID']}",
               "facts": facts,
               "sources": ["CISA KEV catalog: https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
                           f"NVD: https://nvd.nist.gov/vuln/detail/{v['cveID']}"]}


def breach_watch(used):
    start = (date.today() - timedelta(days=45)).isoformat()
    try:
        data = get_json("https://efts.sec.gov/LATEST/search-index?q=%22Item%201.05%22&forms=8-K"
                        f"&startdt={start}&enddt={date.today().isoformat()}")
    except Exception:
        return
    for h in data.get("hits", {}).get("hits", []):
        src = h["_source"]
        adsh = src.get("adsh")
        rid = f"sec:{adsh}"
        if rid in used or "1.05" not in (src.get("items") or []):
            continue
        acc, fname = h["_id"].split(":", 1)
        url = f"https://www.sec.gov/Archives/edgar/data/{int(src['ciks'][0])}/{acc.replace('-', '')}/{fname}"
        try:
            doc = text_of(get(url), 60000)
        except Exception:
            continue
        i = doc.find("Item 1.05")
        part = doc[i: i + 3500] if i >= 0 else ""
        if len(part) < 300:
            continue
        name = re.sub(r"\s*\(CIK.*", "", (src.get("display_names") or ["A company"])[0])
        yield {"id": rid, "series": "Breach Watch", "headline": name,
               "facts": f"SEC Form 8-K filed {src.get('file_date')} by {name}, Item 1.05 Material Cybersecurity Incidents. Filing text: {part}",
               "sources": [f"SEC filing: {url}"]}


def scam_alert(used):
    try:
        page = get("https://consumer.ftc.gov/consumer-alerts")
    except Exception:
        return
    links = []
    for href, title in re.findall(r'href="(?:https://consumer\.ftc\.gov)?(/consumer-alerts/20\d\d/\d\d/[^"#?]+)"[^>]*>(.*?)</a>', page, flags=re.S):
        t = text_of(title, 200)
        if t and href not in [l for l, _ in links]:
            links.append((href, t))
    for href, title in links[:25]:
        url = "https://consumer.ftc.gov" + href
        rid = f"ftc:{href}"
        if rid in used:
            continue
        try:
            body = text_of(get(url), 9000)
        except Exception:
            continue
        i = body.find(title[:40])
        body = body[i: i + 3500] if i >= 0 else body[:3500]
        m = re.search(r"/consumer-alerts/(20\d\d)/(\d\d)/", href)
        yield {"id": rid, "series": "Scam Alert", "headline": title,
               "facts": f"FTC consumer alert published {m.group(1)}-{m.group(2)}: {title}. {body}",
               "sources": [f"FTC consumer alert: {url}"]}


# ---------------- Space Science ----------------

PEOPLE = re.compile(r"astronaut|crew|portrait|headshot|administrator|ceremony|press conference|employee|students?\b",
                    re.I)


def look_closer(used):
    year = date.today().year - 1
    for q in CATALOG["nasa_queries"]:
        try:
            data = get_json("https://images-api.nasa.gov/search?media_type=image&year_start="
                            f"{year}&q={urllib.parse.quote(q)}")
        except Exception:
            continue
        for it in data.get("collection", {}).get("items", [])[:40]:
            meta = (it.get("data") or [{}])[0]
            nid = meta.get("nasa_id")
            rid = f"nasa:{nid}"
            desc = text_of(meta.get("description", ""), 3000)
            blob = meta.get("title", "") + " " + desc + " " + " ".join(meta.get("keywords") or [])
            if not nid or rid in used or PEOPLE.search(blob) or len(desc) < 200:
                continue
            m = re.search(r"(?:Image )?[Cc]redit[s]?:\s*([^.]{3,120})", desc)
            credit = (m.group(1).strip() if m else "NASA")
            if "NASA" not in credit or re.search(r"©|copyright|getty|reuters|AP Photo", credit, re.I):
                continue
            img = next((l["href"] for l in it.get("links", []) if "~large" in l.get("href", "")), None) \
                or next((l["href"] for l in it.get("links", []) if l.get("render") == "image"), None)
            if not img:
                continue
            yield {"id": rid, "series": "Look Closer", "headline": meta.get("title"),
                   "facts": f"NASA image '{meta.get('title')}', created {meta.get('date_created', '')[:10]}, NASA center {meta.get('center')}. Description: {desc}",
                   "sources": [f"NASA Image and Video Library: https://images.nasa.gov/details/{nid}"],
                   "image_url": img, "credit": credit}


SPANISH = re.compile(r"\b(la|el|los|las|del|busca|nueva|próxima)\b", re.I)


def mission_log(used):
    try:
        items = list(rss_items("https://www.nasa.gov/news-release/feed/"))
    except Exception:
        return
    for it in items[:30]:
        rid = f"nasanews:{it['link']}"
        if rid in used or SPANISH.search(it["title"]) or PEOPLE.search(it["title"]):
            continue
        body = text_of(it["content"] or it["description"], 3500)
        if len(body) < 400:
            continue
        yield {"id": rid, "series": "Mission Log", "headline": it["title"],
               "facts": f"NASA news release, {it['date']}: {it['title']}. {body}",
               "sources": [f"NASA: {it['link']}"]}


def scale_it(used):
    try:
        page = get("https://nssdc.gsfc.nasa.gov/planetary/factsheet/")
    except Exception:
        return
    rows = {}
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", page):
        cells = [text_of(c, 80) for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
        if cells:
            rows[cells[0].lower()] = cells[1:]
    header = next((v for k, v in rows.items() if "mercury" in " ".join(v).lower()), None)
    diam = next((v for k, v in rows.items() if k.startswith("diameter")), None)
    dist = next((v for k, v in rows.items() if k.startswith("distance from sun")), None)
    if not header or not diam:
        return
    names = [h.upper() for h in header]
    table = {n: diam[i].replace(",", "") for i, n in enumerate(names) if i < len(diam)}
    bodies = [b for b in CATALOG["scale_bodies"] if b in table]
    for a, b in itertools.permutations(bodies, 2):
        try:
            da, db = float(table[a]), float(table[b])
        except ValueError:
            continue
        if da <= db:
            continue
        rid = f"scale:{a}:{b}"
        if rid in used:
            continue
        extra = ""
        if dist:
            try:
                extra = (f" Distance from the Sun: {a.title()} {dist[names.index(a)]} million km, "
                         f"{b.title()} {dist[names.index(b)]} million km.")
            except (ValueError, IndexError):
                pass
        yield {"id": rid, "series": "Scale It", "headline": f"{a.title()} vs {b.title()}",
               "facts": (f"NASA Planetary Fact Sheet. Diameter of {a.title()}: {table[a]} km. Diameter of {b.title()}: "
                         f"{table[b]} km. Ratio: {da / db:.2f}.{extra}"),
               "sources": ["NASA Planetary Fact Sheet: https://nssdc.gsfc.nasa.gov/planetary/factsheet/"],
               "scale": {"a_label": a.title(), "a_value": da, "b_label": b.title(), "b_value": db}}


# ---------------- Technical Writing For Beginners ----------------

def rewrite_this(used):
    import os
    token = os.environ.get("GITHUB_TOKEN")
    since = (date.today() - timedelta(days=30)).isoformat()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for lic in ("mit", "apache-2.0", "bsd-3-clause"):
        try:
            data = get_json("https://api.github.com/search/repositories?per_page=40&sort=updated&q="
                            + urllib.parse.quote(f"stars:100..3000 pushed:>{since} license:{lic} fork:false"), headers)
        except Exception:
            continue
        for r in data.get("items", []):
            rid = f"repo:{r['full_name']}"
            if rid in used:
                continue
            try:
                readme = get(f"https://api.github.com/repos/{r['full_name']}/readme",
                             {**headers, "Accept": "application/vnd.github.raw+json"})
            except Exception:
                continue
            prose = "\n".join(l for l in readme.splitlines()
                              if l.strip() and not l.lstrip().startswith(("#", "!", "[", "<", "|", "```", "-", "*", ">")))
            prose = re.sub(r"\s+", " ", prose)
            if len(prose) < 400:
                continue
            yield {"id": rid, "series": "Rewrite This", "headline": r["full_name"],
                   "facts": (f"README of the open-source project {r['full_name']} ({r.get('license', {}).get('spdx_id')} license). "
                             f"README prose: {prose[:3000]}"),
                   "sources": [f"{r['full_name']} README ({r.get('license', {}).get('spdx_id')}): {r['html_url']}"],
                   "license": r.get("license", {}).get("spdx_id")}


def one_rule(used):
    for url in CATALOG["style_topics"]:
        rid = f"style:{url}"
        if rid in used:
            continue
        try:
            body = text_of(get(url), 9000)
        except Exception:
            continue
        i = max(0, body.find(" ", 300))
        yield {"id": rid, "series": "One Rule", "headline": url.rsplit("/", 1)[-1].replace("-", " "),
               "facts": f"Guidance from {url}: {body[i:i + 3500]}", "sources": [f"Google developer documentation: {url}"]}


def doc_types(used):
    for d in CATALOG["doc_types"]:
        rid = f"doctype:{d['name']}"
        if rid in used:
            continue
        try:
            body = text_of(get(d["url"]), 9000)
        except Exception:
            continue
        yield {"id": rid, "series": "Doc Types", "headline": d["name"],
               "facts": f"Doc type: {d['name']}. Guidance from {d['url']}: {body[:3500]}",
               "sources": [f"{d['name']} guidance: {d['url']}"]}


# ---------------- registry ----------------

SERIES = {
    "asked-and-answered": {"Buyers Asked": buyers_asked, "The Fix": the_fix, "Trend Check": trend_check},
    "automation-shelf": {"Stop Doing This": lambda u: n8n_templates(u, "Stop Doing This"),
                         "Library Pick": lambda u: n8n_templates(u, "Library Pick"),
                         "Can It Be Automated?": lambda u: n8n_templates(u, "Can It Be Automated?")},
    "breach-brief": {"Exploited Today": exploited_today, "Breach Watch": breach_watch, "Scam Alert": scam_alert},
    "plain-docs": {"Rewrite This": rewrite_this, "One Rule": one_rule, "Doc Types": doc_types},
    "deep-field": {"Look Closer": look_closer, "Mission Log": mission_log, "Scale It": scale_it},
}


def next_record(slug, series, used, avoid=()):
    """The next unused record for a series, falling back to the channel's other series."""
    order = [series] + [s for s in SERIES[slug] if s != series]
    for s in order:
        try:
            for rec in SERIES[slug][s](used):
                if rec["id"] not in used and rec["id"] not in avoid:
                    return rec
        except Exception as e:
            print(f"  source {slug}/{s} failed: {e}")
    return None
