"""Step 2a: one flat-vector illustration per post, generated fresh.

Any OpenAI-compatible /images/generations endpoint works -- point IMAGE_API_BASE at
OpenAI directly or at a gateway that speaks the same shape. Failure is never fatal:
the post still goes out with the icon-only frame.
"""
import base64
import sys
import time

import requests

from . import config

# Locked style, so a month of posts still reads as one account rather than a stock bin.
STYLE = (
    "Flat vector editorial illustration, modern infographic style. "
    "Bold simple geometric shapes, clean thick outlines, confident flat colour fills, "
    "soft depth through overlapping shapes only -- no photorealism, no 3D render, "
    "no gradients meshes, no drop shadows. "
    "Palette: {accent} and {accent2} as the leads over light neutrals. "
    "Centred single subject, generous margin, nothing cropped at the edges. "
    "Fully transparent background. "
    "ABSOLUTELY NO text, letters, numbers, labels, captions, watermarks or UI chrome "
    "anywhere in the image."
)


def prompt_for(data: dict, accent: str, accent2: str) -> str:
    subject = data.get("art") or f"an abstract depiction of {data['title']}"
    return f"{STYLE.format(accent=accent, accent2=accent2)}\n\nSubject: {subject}"


def generate(data: dict, accent: str, accent2: str, retries: int = 2) -> bytes:
    """Return PNG bytes, or None if the provider is unreachable or unconfigured."""
    key = config.opt("IMAGE_API_KEY")
    if not key:
        print("[art] IMAGE_API_KEY not set, skipping illustration", file=sys.stderr)
        return None

    payload = {
        "model": config.opt("IMAGE_MODEL", "gpt-image-1"),
        "prompt": prompt_for(data, accent, accent2),
        "size": config.opt("IMAGE_SIZE", "1024x1024"),
        "n": 1,
    }
    # Transparency is what lets the illustration sit inside our own palette instead of
    # dragging its own white box along. Providers that ignore these keys still work.
    if config.opt("IMAGE_TRANSPARENT", "1") == "1":
        payload["background"] = "transparent"
        payload["output_format"] = "png"

    url = config.opt("IMAGE_API_BASE", "https://api.openai.com/v1").rstrip("/") + "/images/generations"
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {key}"},
                timeout=int(config.opt("IMAGE_TIMEOUT", "240")),
            )
            if r.ok:
                item = r.json()["data"][0]
                if item.get("b64_json"):
                    return base64.b64decode(item["b64_json"])
                if item.get("url"):  # some providers hand back a link instead
                    img = requests.get(item["url"], timeout=120)
                    img.raise_for_status()
                    return img.content
                raise RuntimeError(f"no image payload in response: {list(item)}")
            last = f"[{r.status_code}] {r.text[:400]}"
        except Exception as e:
            last = str(e)
        if attempt < retries:
            time.sleep(4 * (attempt + 1))
    print(f"[art] generation failed, falling back to icon-only frame: {last}", file=sys.stderr)
    return None
