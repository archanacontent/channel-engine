"""Which official India feeds answer the pipeline from a GitHub runner? Prints status and the first item.
Requests identify the pipeline by name; a source that refuses it is not used."""
import re
import urllib.request

UA = {"User-Agent": "ChannelEngine/1.0 (103558334+archanacontent@users.noreply.github.com)"}
URLS = [
    "https://newsonair.gov.in/feed/",
    "https://www.newsonair.gov.in/feed/",
    "https://ddnews.gov.in/en/feed/",
    "https://www.mygov.in/rss/feed/",
    "https://www.india.gov.in/rss.xml",
    "https://api.data.gov.in/lists?format=json&limit=1",
    "https://www.isro.gov.in/rss.xml",
    "https://www.rbi.org.in/pressreleases_rss.xml",
    "https://news.google.com/rss/search?q=PIB+India+ministry+crore&hl=en-IN&gl=IN&ceid=IN:en",
    "https://api.worldbank.org/v2/country/IND/indicator/EG.ELC.ACCS.ZS?format=json&per_page=3",
    "https://www.thehindubusinessline.com/economy/feeder/default.rss",
    "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    "https://www.livemint.com/rss/economy",
    "https://www.business-standard.com/rss/economy-102.rss",
]
for u in URLS:
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
            body = r.read().decode("utf-8", "replace")
            t = re.findall(r"<title>(.*?)</title>", body, re.S)
            print(r.status, len(body), u, "|", (t[1] if len(t) > 1 else t[0] if t else body[:80])[:90].strip())
    except Exception as e:
        print("FAIL", u, e)
