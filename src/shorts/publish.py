"""Reel publishers. Each raises on failure; the orchestrator decides what that means."""
import time

import requests

from .. import config

# ---------- Instagram Reels ----------

def instagram(video_url: str, caption: str) -> str:
    ig = config.req("IG_USER_ID")
    token = config.req("PAGE_ACCESS_TOKEN")
    r = requests.post(f"{config.GRAPH_BASE}/{ig}/media", data={
        "media_type": "REELS", "video_url": video_url, "caption": caption,
        "share_to_feed": "true", "access_token": token}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"ig reels /media failed [{r.status_code}]: {r.text}")
    cid = r.json()["id"]
    # Reels transcode server-side; publishing before FINISHED fails with a generic error.
    for _ in range(60):
        s = requests.get(f"{config.GRAPH_BASE}/{cid}",
                         params={"fields": "status_code,status", "access_token": token}, timeout=30)
        code = s.json().get("status_code") if s.ok else None
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"ig reels container error: {s.text}")
        time.sleep(5)
    else:
        raise RuntimeError("ig reels container never reached FINISHED")
    r = requests.post(f"{config.GRAPH_BASE}/{ig}/media_publish",
                      data={"creation_id": cid, "access_token": token}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"ig reels /media_publish failed [{r.status_code}]: {r.text}")
    return r.json()["id"]


# ---------- Facebook Page video ----------

def facebook(video_url: str, description: str, title: str) -> str:
    r = requests.post(f"{config.GRAPH_BASE}/{config.req('PAGE_ID')}/videos", data={
        "file_url": video_url, "description": description, "title": title,
        "access_token": config.req("PAGE_ACCESS_TOKEN")}, timeout=120)
    if not r.ok:
        raise RuntimeError(f"fb /videos failed [{r.status_code}]: {r.text}")
    return r.json().get("id", "")


# ---------- YouTube Shorts ----------

def youtube(path: str, title: str, description: str, tags: list) -> str:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        None,
        refresh_token=config.req("YT_REFRESH_TOKEN"),
        client_id=config.req("YT_CLIENT_ID"),
        client_secret=config.req("YT_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    # A vertical video under 3 minutes is a Short; the tag just helps discovery.
    if "#shorts" not in title.lower():
        title = (title[:92] + " #Shorts") if len(title) > 92 else title + " #Shorts"
    body = {
        "snippet": {"title": title[:100], "description": description[:5000],
                    "tags": [t.lstrip("#") for t in tags][:20], "categoryId": "28"},
        "status": {"privacyStatus": config.opt("YT_PRIVACY", "public"),
                   "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(path, mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


# ---------- X ----------

def x(path: str, text: str) -> str:
    import tweepy

    ck, cs = config.req("X_CONSUMER_KEY"), config.req("X_CONSUMER_SECRET")
    at, ats = config.req("X_ACCESS_TOKEN"), config.req("X_ACCESS_TOKEN_SECRET")
    api = tweepy.API(tweepy.OAuth1UserHandler(ck, cs, at, ats))
    # Chunked upload + tweet_video category is mandatory for video; the helper waits for processing.
    media = api.media_upload(path, chunked=True, media_category="tweet_video")
    client = tweepy.Client(consumer_key=ck, consumer_secret=cs,
                           access_token=at, access_token_secret=ats)
    resp = client.create_tweet(text=text, media_ids=[media.media_id_string])
    return str(resp.data["id"])
