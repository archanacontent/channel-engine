"""YouTube Data API calls for the five channels.

Upload (Sunday): the Short goes up private with its title, description, tags,
category, language and audience already set. 1 unit from the separate
100-a-day upload allowance.

Publish (at its slot, only if ticked): status to public (50 units), added to its
series playlist (50), exact caption file attached (400). About 500 units a
Short, 7,500 a day for 15 Shorts, inside the 10,000 free daily units.

Credentials: YT_CLIENT_ID and YT_CLIENT_SECRET for the one Google Cloud project,
and one YT_REFRESH_<SLUG> per channel (e.g. YT_REFRESH_BREACH_BRIEF), each
authorised for that channel's Brand Account with the youtube.force-ssl
scope, which covers uploads, playlists, status changes and captions.
"""
import json
import os
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def client(slug):
    key = "YT_REFRESH_" + slug.upper().replace("-", "_")
    creds = Credentials(None, refresh_token=os.environ[key], token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
                        scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def whoami(slug):
    """Name and handle of the channel a token belongs to, to catch a token made on the wrong channel."""
    ch = client(slug).channels().list(part="snippet", mine=True).execute()["items"][0]["snippet"]
    return ch["title"], ch.get("customUrl")


def upload_private(slug, mp4, meta):
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["youtube_description"],
            "tags": meta["tags"],
            "categoryId": meta["category_id"],
            "defaultLanguage": meta["language"],
            "defaultAudioLanguage": meta["language"],
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": meta["made_for_kids"],
            "containsSyntheticMedia": meta["altered_content"] == "Yes",
            "embeddable": True,
            "publicStatsViewable": True,
        },
    }
    req = client(slug).videos().insert(part="snippet,status", body=body,
                                       media_body=MediaFileUpload(mp4, chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def playlist_id(yt, title):
    """Find the series playlist by title, creating it once if it doesn't exist."""
    page = None
    while True:
        r = yt.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=page).execute()
        for p in r.get("items", []):
            if p["snippet"]["title"] == title:
                return p["id"]
        page = r.get("nextPageToken")
        if not page:
            break
    made = yt.playlists().insert(part="snippet,status", body={
        "snippet": {"title": title, "defaultLanguage": "en"}, "status": {"privacyStatus": "public"}}).execute()
    return made["id"]


def publish(slug, video_id, meta, srt_path=None):
    yt = client(slug)
    yt.videos().update(part="status", body={"id": video_id, "status": {
        "privacyStatus": "public", "selfDeclaredMadeForKids": meta["made_for_kids"],
        "containsSyntheticMedia": meta["altered_content"] == "Yes", "embeddable": True,
        "publicStatsViewable": True}}).execute()
    _extras(yt, video_id, meta)


def _extras(yt, video_id, meta):
    """Playlist is a nice-to-have; it must never block a release. (Captions are left to
    YouTube's automatic captions: uploading them costs 400 of the 10,000 daily quota units.)"""
    if meta.get("playlist"):
        try:
            yt.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": playlist_id(yt, meta["playlist"]),
                "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
        except Exception as e:
            print("  playlist skipped:", str(e)[:120])


def schedule(slug, video_id, meta, srt_path, when_utc):
    """Hands the release to YouTube itself: the video goes public at exactly when_utc."""
    yt = client(slug)
    yt.videos().update(part="status", body={"id": video_id, "status": {
        "privacyStatus": "private", "publishAt": when_utc, "selfDeclaredMadeForKids": meta["made_for_kids"],
        "containsSyntheticMedia": meta["altered_content"] == "Yes", "embeddable": True,
        "publicStatsViewable": True}}).execute()
    _extras(yt, video_id, meta)


if __name__ == "__main__":
    cmd, slug = sys.argv[1], sys.argv[2]
    if cmd == "whoami":
        print(whoami(slug))
    elif cmd == "upload":
        print(upload_private(slug, sys.argv[3], json.load(open(sys.argv[4]))))
    elif cmd == "publish":
        publish(slug, sys.argv[3], json.load(open(sys.argv[4])), sys.argv[5] if len(sys.argv) > 5 else None)
