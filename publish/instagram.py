"""Posts to Instagram through the Instagram API with Facebook Login (free).

Needs three GitHub secrets for the account: IG_USER_ID, IG_PAGE_ID and IG_PAGE_TOKEN
(a Page access token from a long-lived user token, which does not expire).

    python -m publish.instagram whoami
    python -m publish.instagram delete MEDIA_ID [MEDIA_ID ...]

Images: Instagram fetches images from a URL, so the image is first stored as an
unpublished photo on the linked Facebook Page and Instagram is given its CDN URL.
Reels: uploaded directly with Instagram's resumable upload.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

V = os.environ.get("GRAPH_VERSION", "v27.0")
G = f"https://graph.facebook.com/{V}"


def env():
    return os.environ["IG_USER_ID"], os.environ["IG_PAGE_ID"], os.environ["IG_PAGE_TOKEN"]


def call(method, path, params=None, data=None, headers=None, base=G):
    url = f"{base}/{path}"
    if params and method == "GET":
        url += "?" + urllib.parse.urlencode(params)
        params = None
    body = data if data is not None else (urllib.parse.urlencode(params).encode() if params else None)
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: HTTP {e.code} {e.read()[:400]!r}") from None


def multipart(fields, file_field, file_path):
    b = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    data = Path(file_path).read_bytes()
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{Path(file_path).name}"\r\n'
                 f'Content-Type: image/jpeg\r\n\r\n'.encode() + data + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    return b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={b}"}


def wait_ready(container, token, tries=60):
    for _ in range(tries):
        st = call("GET", container, {"fields": "status_code,status", "access_token": token})
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram could not process the media: {st}")
        time.sleep(10)
    raise RuntimeError("Instagram took too long to process the media")


def post_image(path, caption, dry=False):
    ig, page, token = env()
    body, hdr = multipart({"published": "false", "temporary": "true", "access_token": token}, "source", path)
    photo = call("POST", f"{page}/photos", data=body, headers=hdr)["id"]
    src = max(call("GET", photo, {"fields": "images", "access_token": token})["images"], key=lambda i: i["width"])["source"]
    c = call("POST", f"{ig}/media", {"image_url": src, "caption": caption, "access_token": token})["id"]
    wait_ready(c, token)
    if dry:
        call("DELETE", photo, {"access_token": token})
        return f"dry run ok, container {c} (not published)"
    media = call("POST", f"{ig}/media_publish", {"creation_id": c, "access_token": token})["id"]
    try:
        call("DELETE", photo, {"access_token": token})   # the stand-in Page photo is no longer needed
    except Exception:
        pass
    return media


def post_reel(path, caption, dry=False):
    ig, page, token = env()
    c = call("POST", f"{ig}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": caption,
                                     "share_to_feed": "true", "access_token": token})["id"]
    data = Path(path).read_bytes()
    call("POST", f"ig-api-upload/{V}/{c}", data=data, base="https://rupload.facebook.com",
         headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(data))})
    wait_ready(c, token)
    if dry:
        return f"dry run ok, container {c} (not published)"
    return call("POST", f"{ig}/media_publish", {"creation_id": c, "access_token": token})["id"]


LEDGER = Path(__file__).resolve().parent.parent / "state" / "instagram_posted.json"


def fingerprint(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def already_posted(path, caption):
    """True if this exact file, or a post with the same opening caption line, is already up.
    Checks our ledger and the account's 25 most recent posts, so a second run or a second
    tool can never post the same thing twice."""
    fp = fingerprint(path)
    led = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    if fp in led:
        return led[fp]
    ig, _, token = env()
    first = caption.strip().splitlines()[0].strip().lower() if caption.strip() else ""
    recent = call("GET", f"{ig}/media", {"fields": "id,caption,timestamp", "limit": 25, "access_token": token})
    for m in recent.get("data", []):
        c = (m.get("caption") or "").strip().splitlines()
        if first and c and c[0].strip().lower() == first:
            return m["id"]
    return None


def publish(path, caption):
    dup = already_posted(path, caption)
    if dup:
        print(f"skipped: already on Instagram as {dup}")
        return dup
    mid = post_reel(path, caption) if str(path).endswith(".mp4") else post_image(path, caption)
    led = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    led[fingerprint(path)] = mid
    LEDGER.parent.mkdir(exist_ok=True)
    LEDGER.write_text(json.dumps(led, indent=1))
    return mid


def delete(media_id):
    _, _, token = env()
    return call("DELETE", media_id, {"access_token": token})


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "whoami":
        ig, _, token = env()
        print(call("GET", ig, {"fields": "username,media_count", "access_token": token}))
    elif cmd == "dryrun":   # checks Instagram accepts the files without posting anything
        for f in sys.argv[2:]:
            fn = post_reel if f.endswith(".mp4") else post_image
            print(f, fn(f, "test", dry=True))
    elif cmd == "post":    # python -m publish.instagram post FILE CAPTION_FILE
        print("posted", publish(sys.argv[2], Path(sys.argv[3]).read_text()))
    elif cmd == "delete":
        for m in sys.argv[2:]:
            print(m, delete(m))
