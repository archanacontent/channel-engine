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
for name in ["Little Nemo in Slumberland", "Little Nemo", "In the Land of Wonderful Dreams", "Krazy Kat", "Dream of the Rarebit Fiend",
             "Little Sammy Sneeze", "The Katzenjammer Kids", "Mutt and Jeff", "Buster Brown", "Happy Hooligan", "Bringing Up Father",
             "Polly and Her Pals", "Thimble Theatre", "Hairbreadth Harry", "Winsor McCay comics"]:
    cat = "Category:" + name
    try:
        files = members(cat, "file"); subs = members(cat, "subcat")
        deep = sum(len(members(s, "file")) for s in subs[:40])
        print(f"{name}: {len(files)} files, {len(subs)} subcats, {deep} files in subcats | e.g. {files[:2]} {subs[:4]}")
    except Exception as e:
        print(name, "ERR", e)
