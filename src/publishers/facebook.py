"""Facebook Page photo post."""
import requests

from .. import config


def publish(image_url: str, caption: str) -> str:
    page_id = config.req("PAGE_ID")
    r = requests.post(
        f"{config.GRAPH_BASE}/{page_id}/photos",
        data={
            "url": image_url,
            "caption": caption,
            "access_token": config.req("PAGE_ACCESS_TOKEN"),
        },
        timeout=60,
    )
    if not r.ok:
        raise RuntimeError(f"facebook /photos failed [{r.status_code}]: {r.text}")
    return r.json().get("post_id") or r.json().get("id", "")
