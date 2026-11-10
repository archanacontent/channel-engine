import json, os, urllib.request, urllib.error
key = os.environ["GEMINI_API_KEY"]
H = {"x-goog-api-key": key, "Content-Type": "application/json"}
req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers=H)
models = [m["name"].split("/")[1] for m in json.loads(urllib.request.urlopen(req).read())["models"]
          if "generateContent" in m.get("supportedGenerationMethods", [])]
print("models:", ", ".join(models))
body = json.dumps({"contents": [{"role": "user", "parts": [{"text": "Reply with the word ready."}]}]}).encode()
for m in models:
    if not any(k in m for k in ("flash", "gemma", "pro")) or any(k in m for k in ("image", "tts", "audio", "live", "embedding")):
        continue
    r = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", data=body, headers=H, method="POST")
    try:
        out = json.loads(urllib.request.urlopen(r, timeout=60).read())
        print("OK  ", m, out["candidates"][0]["content"]["parts"][0]["text"][:20].strip())
    except urllib.error.HTTPError as e:
        msg = json.loads(e.read()).get("error", {})
        viol = [v.get("quotaId", "") + "=" + str(v.get("quotaValue", "")) for d in msg.get("details", []) for v in d.get("violations", [])]
        print("FAIL", m, e.code, msg.get("message", "")[:120].replace("\n", " "), viol)
    except Exception as e:
        print("FAIL", m, repr(e)[:150])
