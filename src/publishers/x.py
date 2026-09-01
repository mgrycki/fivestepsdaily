"""X: OAuth 1.0a for the media upload, v2 client for the tweet itself."""
import tweepy

from .. import config

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
    resp = client.create_tweet(text=text, media_ids=[media_id])
    return str(resp.data["id"])
