"""Tags and hashtags for every upload.

Tags come from three places, most specific first:
1. the episode's own seed terms (product, CVE, object, task),
2. what people type into YouTube search for those seeds, read from YouTube's
   public autocomplete, so each tag is a phrase people actually search,
3. the channel's evergreen topic pool.

Limits kept on purpose: YouTube asks for tags that relate directly to the video
and warns that excessive tags break its spam policy, so a video gets at most
20 tags inside 480 characters, 6 hashtags in the description (YouTube shows
3 above the title) and 5 on Instagram, its hard cap.
"""
import json
import re
import urllib.parse
import urllib.request

MAX_TAGS, MAX_TAG_CHARS = 20, 480
MAX_YT_HASHTAGS, MAX_IG_HASHTAGS = 6, 5


def autocomplete(term, timeout=6):
    """YouTube search suggestions for a term; empty when the network blocks it."""
    url = ("https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&hl=en&q="
           + urllib.parse.quote(term))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        return [s for s in data[1] if isinstance(s, str)]
    except Exception:
        return []


def _clean(tag):
    tag = re.sub(r"[<>\"]", "", tag).strip()
    return tag if 1 < len(tag) <= 60 else ""


def build_tags(brand, ep, use_autocomplete=True):
    seeds = ep.get("seo", {}).get("seeds", [])
    candidates = list(seeds)
    if use_autocomplete:
        for s in seeds[:4]:
            words = set(s.lower().split())
            hits = [x for x in autocomplete(s) if words & set(x.lower().split())]
            candidates += hits[:3]
    sp = brand["seo"].get("series_pools", {}).get(ep["series"], {})
    candidates += brand["seo"]["tag_pool"][:3] + sp.get("tags", []) + brand["seo"]["tag_pool"][3:]
    out, seen, used = [], set(), 0
    for c in candidates:
        c = _clean(c)
        key = c.lower()
        if not c or key in seen:
            continue
        cost = len(c) + (2 if " " in c else 0) + 1  # quotes for multi-word tags, plus the comma
        if used + cost > MAX_TAG_CHARS or len(out) >= MAX_TAGS:
            break
        out.append(c)
        seen.add(key)
        used += cost
    return out


def _hashtag(h):
    h = "#" + re.sub(r"[^0-9A-Za-z]", "", h.lstrip("#"))
    return h if len(h) > 2 else ""


def build_hashtags(brand, ep, limit):
    anchor = brand["seo"]["hashtag_pool"][0]
    sp = brand["seo"].get("series_pools", {}).get(ep["series"], {})
    pool = [anchor] + ep.get("seo", {}).get("hashtags", []) + brand["seo"]["hashtag_pool"][1:2] + sp.get("hashtags", []) + brand["seo"]["hashtag_pool"][2:]
    out, seen = [], set()
    for h in pool:
        h = _hashtag(h)
        if h and h.lower() not in seen:
            out.append(h)
            seen.add(h.lower())
        if len(out) >= limit:
            break
    return out
