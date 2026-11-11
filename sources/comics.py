"""Public domain comic pages from Wikimedia Commons.

Everything here was first published in the US before 1931, so it is in the US
public domain, and its creators died more than 70 years ago (Winsor McCay, 1934),
so it is public domain in most other countries too. Pages run in date order so
continuing stories stay in sequence.
"""
import json
import re
import urllib.parse
import urllib.request

UA = "ChannelEngine/1.0 (creativecontent707@gmail.com)"
API = "https://commons.wikimedia.org/w/api.php?"
DATE = re.compile(r"(1[89]\d\d)[-_ .](\d\d)[-_ .](\d\d)")

COMICS = {
    "nemo": {
        "name": "Little Nemo in Slumberland",
        "categories": ["Category:Little Nemo in Slumberland", "Category:In the Land of Wonderful Dreams"],
        "creator": "Winsor McCay",
    },
    "sammy": {
        "name": "Little Sammy Sneeze",
        "categories": ["Category:Little Sammy Sneeze"],
        "creator": "Winsor McCay",
    },
    "rarebit": {
        "name": "Dream of the Rarebit Fiend",
        "categories": ["Category:Dream of the Rarebit Fiend"],
        "creator": "Winsor McCay (as Silas)",
    },
}
# Some strips of the era contain racist caricatures; pages naming these are skipped
# before the vision check even runs.
BLOCK = re.compile(r"impie|imp\b|jungle imp|cannibal|savage", re.I)
_cache = {}


def _q(**p):
    p.update(format="json", action="query")
    req = urllib.request.Request(API + urllib.parse.urlencode(p), headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def _members(cat, kind):
    out, cont = [], {}
    while True:
        d = _q(list="categorymembers", cmtitle=cat, cmlimit=500, cmtype=kind, **cont)
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" not in d:
            return out
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}


def _tree(cat, depth=2):
    files = _members(cat, "file")
    if depth:
        for s in _members(cat, "subcat"):
            files += _tree(s, depth - 1)
    return files


def pages(key):
    """[(date, title)] for one comic, one file per date (the largest), oldest first."""
    if key in _cache:
        return _cache[key]
    c = COMICS[key]
    titles = sorted({t for cat in c["categories"] for t in _tree(cat)})
    titles = [t for t in titles if re.search(r"\.(jpe?g|png|gif|tiff?)$", t, re.I) and DATE.search(t)
              and not BLOCK.search(t) and "cover" not in t.lower()]
    by_date = {}
    for i in range(0, len(titles), 40):
        info = _q(titles="|".join(titles[i:i + 40]), prop="imageinfo", iiprop="size|url", iiurlwidth=4000)
        for p in info["query"]["pages"].values():
            ii = (p.get("imageinfo") or [{}])[0]
            if not ii or max(ii.get("width", 0), ii.get("height", 0)) < 2200:
                continue  # small scans blur when a panel fills the screen
            m = DATE.search(p["title"])
            d = f"{m[1]}-{m[2]}-{m[3]}"
            if int(m[1]) > 1930:
                continue
            area = ii["width"] * ii["height"]
            if d not in by_date or area > by_date[d][0]:
                by_date[d] = (area, p["title"], ii["url"] if max(ii["width"], ii["height"]) <= 5000 else ii["thumburl"],
                              ii["descriptionurl"],
                              ii["width"], ii["height"])
    _cache[key] = sorted((d, *v[1:]) for d, v in by_date.items())
    return _cache[key]


def comic_records(keys, series, used):
    """Next unused pages, cycling through the given comics in turn."""
    lists = {k: pages(k) for k in keys}
    i = 0
    while any(lists.values()):
        k = keys[i % len(keys)]
        i += 1
        while lists[k]:
            d, title, url, page, w, h = lists[k].pop(0)
            rid = f"commons:{title}"
            if rid in used:
                continue
            c = COMICS[k]
            yield {
                "id": rid, "series": series, "comic": k, "comic_name": c["name"], "creator": c["creator"],
                "date": d, "headline": f"{c['name']}, {d}", "image_url": url, "width": w, "height": h,
                "credit": f"{c['name']} by {c['creator']}, first published {d}. Public domain. "
                          f"Scan: Wikimedia Commons",
                "sources": [f"Original page (Wikimedia Commons): {page}"], "facts": "",
            }
            break
