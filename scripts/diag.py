import re, sys
sys.path.insert(0, ".")
from sources.fetch import get, rss_items, CATALOG
for u in ["https://consumer.ftc.gov/consumer-alerts"]:
    try:
        p = get(u); print(u, len(p)); print(re.findall(r'href="([^"]*consumer-alerts/20[^"]*)"', p)[:5]); print(p[:300])
    except Exception as e: print(u, "ERR", repr(e))
for f in CATALOG["ai_search_feeds"]:
    try:
        it = list(rss_items(f)); print(f, len(it))
        for x in it[:3]: print("  ", x["title"][:80], "|", len(x["content"] or ""), len(x["description"] or ""))
    except Exception as e: print(f, "ERR", repr(e))
