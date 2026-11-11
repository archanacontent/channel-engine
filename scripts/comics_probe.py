import json, urllib.request, urllib.parse
UA = {"User-Agent": "ChannelEngine/1.0 (creativecontent707@gmail.com)"}
API = "https://commons.wikimedia.org/w/api.php?"
def q(**p):
    p.update(format="json", action="query")
    return json.loads(urllib.request.urlopen(urllib.request.Request(API + urllib.parse.urlencode(p), headers=UA), timeout=60).read())
def members(cat, kind):
    out, cont = [], {}
    while True:
        d = q(list="categorymembers", cmtitle=cat, cmlimit=500, cmtype=kind, **cont)
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" not in d: return out
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}
def tree(cat, depth=2):
    f = members(cat, "file")
    if depth:
        for s in members(cat, "subcat"):
            f += tree(s, depth - 1)
    return f
for name in ["Krazy Kat comics", "Little Nemo in Slumberland, 1906", "Dream of the Rarebit Fiend", "Little Sammy Sneeze"]:
    files = sorted(set(tree("Category:" + name)))
    print(f"{name}: {len(files)}")
    for t in files[:6]: print("   ", t)
    info = q(titles="|".join(files[:5]), prop="imageinfo", iiprop="size|url|extmetadata")
    for p in info["query"]["pages"].values():
        ii = p["imageinfo"][0]; md = ii.get("extmetadata", {})
        print("   size", ii["width"], ii["height"], md.get("LicenseShortName", {}).get("value"), md.get("DateTimeOriginal", {}).get("value", "")[:40])
