"""YouTube uploads through the Data API, free within the default quota.

Uploads go up private (1 unit each from the 100-a-day upload allowance).
At a slot, an approved Short is switched to public (videos.update, 50 units).

Each channel has its own refresh token in an Actions secret named
YT_REFRESH_<SLUG>, e.g. YT_REFRESH_BREACH_BRIEF.
"""
import json
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def client(slug):
    key = "YT_REFRESH_" + slug.upper().replace("-", "_")
    creds = Credentials(None, refresh_token=os.environ[key], token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
                        scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_private(slug, mp4, meta):
    yt = client(slug)
    body = {
        "snippet": {"title": meta["title"][:100], "description": meta["youtube_description"][:5000],
                    "categoryId": "28" if slug != "deep-field" else "27"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": meta.get("altered_content") == "Yes"},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(mp4, chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def make_public(slug, video_id):
    yt = client(slug)
    yt.videos().update(part="status", body={"id": video_id, "status": {"privacyStatus": "public"}}).execute()


if __name__ == "__main__":
    cmd, slug = sys.argv[1], sys.argv[2]
    if cmd == "upload":
        meta = json.load(open(sys.argv[4]))
        print(upload_private(slug, sys.argv[3], meta))
    elif cmd == "publish":
        make_public(slug, sys.argv[3])
