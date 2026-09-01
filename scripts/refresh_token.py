"""Refresh the long-lived Page token (~60 day life) and print the new one.

Run monthly. The output has to be written back into the GitHub secret
PAGE_ACCESS_TOKEN -- this script does not do that for you.
"""
import sys

import requests

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from src import config  # noqa: E402


def main() -> int:
    r = requests.get(
        f"{config.GRAPH_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": config.req("META_APP_ID"),
            "client_secret": config.req("META_APP_SECRET"),
            "fb_exchange_token": config.req("PAGE_ACCESS_TOKEN"),
        },
        timeout=30,
    )
    if not r.ok:
        print(f"refresh failed [{r.status_code}]: {r.text}", file=sys.stderr)
        return 1
    body = r.json()
    print(body["access_token"])
    print(f"expires_in={body.get('expires_in', 'never')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
