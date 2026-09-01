"""Instagram Graph API: container -> publish. Always two calls."""
import time

import requests

from .. import config


def _poll_ready(creation_id: str, token: str, tries: int = 12, delay: float = 5.0) -> None:
    """Large images are fetched async; publishing a container before it is FINISHED 500s."""
    for _ in range(tries):
        r = requests.get(
            f"{config.GRAPH_BASE}/{creation_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        )
        status = r.json().get("status_code") if r.ok else None
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"instagram container error: {r.text}")
        time.sleep(delay)
    raise RuntimeError(f"instagram container {creation_id} never reached FINISHED")


def publish(image_url: str, caption: str) -> str:
    ig_user = config.req("IG_USER_ID")
    token = config.req("PAGE_ACCESS_TOKEN")

    r = requests.post(
        f"{config.GRAPH_BASE}/{ig_user}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=60,
    )
    if not r.ok:
        raise RuntimeError(f"instagram /media failed [{r.status_code}]: {r.text}")
    creation_id = r.json()["id"]

    _poll_ready(creation_id, token)

    r = requests.post(
        f"{config.GRAPH_BASE}/{ig_user}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    if not r.ok:
        raise RuntimeError(f"instagram /media_publish failed [{r.status_code}]: {r.text}")
    return r.json()["id"]
