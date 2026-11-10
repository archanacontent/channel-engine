import json, os, urllib.request, urllib.error
key = os.environ["GEMINI_API_KEY"]
H = {"x-goog-api-key": key, "Content-Type": "application/json"}
prompt = 'Return JSON only: {"title": "...", "beats": [{"say": "..."}]} about why a README needs a quickstart. Two beats.'
for m in ["gemma-4-31b-it", "gemma-4-26b-a4b-it"]:
    for cfg in ({}, {"responseMimeType": "application/json"}):
        body = json.dumps({"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": cfg}).encode()
        r = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", data=body, headers=H, method="POST")
        try:
            out = json.loads(urllib.request.urlopen(r, timeout=120).read())
            parts = out["candidates"][0]["content"]["parts"]
            print("OK  ", m, cfg, [p.get("text", "")[:300] for p in parts], [bool(p.get("thought")) for p in parts])
        except urllib.error.HTTPError as e:
            print("FAIL", m, cfg, e.code, e.read()[:300])
        except Exception as e:
            print("FAIL", m, cfg, repr(e)[:200])
