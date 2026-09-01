"""X: OAuth 1.0a for the media upload, v2 client for the tweet itself."""
import tweepy

from .. import config

LIMIT = 280


def _fit(text: str) -> str:
    # A tweet with media still costs the full text length; the media itself is free.
    if len(text) <= LIMIT:
        return text
    return text[: LIMIT - 1].rsplit(" ", 1)[0] + "…"


def publish(image_path: str, text: str) -> str:
    ck = config.req("X_CONSUMER_KEY")
    cs = config.req("X_CONSUMER_SECRET")
    at = config.req("X_ACCESS_TOKEN")
    ats = config.req("X_ACCESS_TOKEN_SECRET")

    auth = tweepy.OAuth1UserHandler(ck, cs, at, ats)
    media_id = tweepy.API(auth).media_upload(image_path).media_id_string

    client = tweepy.Client(
        consumer_key=ck, consumer_secret=cs,
        access_token=at, access_token_secret=ats,
    )
    resp = client.create_tweet(text=_fit(text), media_ids=[media_id])
    return str(resp.data["id"])
