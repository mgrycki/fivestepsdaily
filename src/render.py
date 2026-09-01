"""Step 2: HTML template -> 1080x1350 JPEG via Playwright."""
import json
import os
import zlib

from playwright.sync_api import sync_playwright

from . import config

LAYOUTS = ["cards", "timeline"]
THEMES = 5


def rotation(seed: str) -> tuple:
    """Deterministic but varied theme/layout per topic, so IG never sees the same frame twice."""
    h = zlib.crc32(seed.encode())
    return h % THEMES, LAYOUTS[(h >> 8) % len(LAYOUTS)]


def render(data: dict, out_path: str, handle: str = "") -> str:
    theme, layout = rotation(data["title"])
    html = open(config.TEMPLATE, encoding="utf-8").read()
    html = (
        html.replace("{{DATA}}", json.dumps(data, ensure_ascii=False))
        .replace("{{THEME}}", str(theme))
        .replace("{{LAYOUT}}", json.dumps(layout))
        .replace("{{HANDLE}}", json.dumps(handle))
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1080, "height": 1350}, device_scale_factor=2
        )
        page.set_content(html, wait_until="load")
        # Google Fonts must be in before we shoot, otherwise the fit() sizing is wrong.
        try:
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=8000)
        except Exception:
            pass  # fall back to the system stack rather than failing the run
        page.evaluate("() => window.scrollTo(0,0)")
        # JPEG only: Instagram rejects PNG uploads via /media.
        page.screenshot(path=out_path, type="jpeg", quality=88, clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
        browser.close()
    return out_path
