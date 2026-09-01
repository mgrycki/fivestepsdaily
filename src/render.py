"""Step 2b: HTML template -> 1080x1350 JPEG via Playwright."""
import base64
import json
import os
import zlib

from playwright.sync_api import sync_playwright

from . import config

LAYOUTS = ["cards", "flow"]

# Must stay in step with the body[data-theme="N"] blocks in template.html.
# The illustration prompt is built from these, so the art lands in the same palette.
ACCENTS = [
    ("sky blue", "warm orange"),
    ("vivid coral orange", "golden yellow"),
    ("emerald green", "cyan"),
    ("amber orange", "raspberry red"),
    ("violet purple", "sky blue"),
    ("magenta pink", "violet purple"),
]
THEMES = len(ACCENTS)


def rotation(seed: str) -> tuple:
    """Deterministic but varied theme/layout per topic, so IG never sees the same frame twice."""
    h = zlib.crc32(seed.encode())
    return h % THEMES, LAYOUTS[(h >> 8) % len(LAYOUTS)]


def render(data: dict, out_path: str, handle: str = "", art: bytes = None,
           theme: int = None, layout: str = None) -> str:
    auto_theme, auto_layout = rotation(data["title"])
    theme = auto_theme if theme is None else theme
    layout = auto_layout if layout is None else layout

    # The page is loaded via set_content, so it has no origin and file:// images are blocked.
    # Everything has to travel inline.
    art_uri = ""
    if art:
        art_uri = "data:image/png;base64," + base64.b64encode(art).decode()

    html = open(config.TEMPLATE, encoding="utf-8").read()
    icons = open(config.ICONS, encoding="utf-8").read()
    html = (
        html.replace("{{DATA}}", json.dumps(data, ensure_ascii=False))
        .replace("{{ICONS}}", icons)
        .replace("{{THEME}}", str(theme))
        .replace("{{LAYOUT}}", json.dumps(layout))
        .replace("{{HANDLE}}", json.dumps(handle))
        .replace("{{ART}}", json.dumps(art_uri))
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1080, "height": 1350}, device_scale_factor=2
        )
        page.set_content(html, wait_until="load")
        # Google Fonts must be in before we shoot, otherwise fit() sizes against the wrong metrics.
        try:
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=8000)
        except Exception:
            pass  # fall back to the system stack rather than failing the run
        page.evaluate("() => window.scrollTo(0,0)")
        # JPEG only: Instagram rejects PNG uploads via /media.
        page.screenshot(path=out_path, type="jpeg", quality=88,
                        clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
        browser.close()
    return out_path
