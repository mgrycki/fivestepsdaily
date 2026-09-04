"""One call to HeyGen Video Agent: the day's brief in, a finished vertical reel out."""
import json
import sys
import time

import requests

from .. import config

API = "https://api.heygen.com/v3"

LANG_NAMES = {"en": "English", "pl": "Polish", "de": "German", "es": "Spanish", "fr": "French"}

PROMPT = """Create a {seconds}-second vertical short-form video (Instagram Reel / YouTube Short) that
explains the process below. Spoken narration and all on-screen text in {lang}.

FORMAT
- Portrait 9:16. Fast-paced, one idea per scene, big readable captions synced to the voice.
- Open with the single most surprising fact in the first sentence. Viewers decide in 2 seconds.
- Walk through the five stages in order. Say the hard numbers out loud and show them on screen.
- Close with one concrete takeaway. No call to action, no "subscribe".
{presenter}
- Music: subtle, modern, under the voice. No sound effects gimmicks.

CONTENT (use only what is here, do not invent facts, numbers or quotes)
Title: {title}
Hook: {hook}
Stages:
{stages}
Key figures:
{stats}
{quote}
"""


def build_prompt(source: dict) -> str:
    lang = LANG_NAMES.get(config.opt("REEL_LANGUAGE", "en"), config.opt("REEL_LANGUAGE", "en"))
    seconds = config.opt("REEL_SECONDS", "50")
    faceless = config.opt("REEL_FACELESS", "1") == "1"
    presenter = (
        "- No on-screen presenter or avatar. Voice-over with b-roll, motion graphics and captions only."
        if faceless else
        "- One presenter, framed waist-up, speaking to camera, with b-roll cutaways for each stage."
    )
    stages = "\n".join(f"  {s['n']}. {s['label']} -- {s['text']}" for s in source["steps"])
    stats = "\n".join(f"  - {st['value']}: {st['label']}" for st in source.get("stats", [])) or "  (none)"
    q = source.get("quote")
    quote = f'Quote (verbatim, attribute on screen): "{q["text"]}" -- {q["who"]}' if q else ""
    return PROMPT.format(seconds=seconds, lang=lang, presenter=presenter, title=source["title"],
                         hook=source["hook"], stages=stages, stats=stats, quote=quote)


def _get(path: str, key: str) -> dict:
    r = requests.get(f"{API}{path}", headers={"X-Api-Key": key}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"heygen GET {path} failed [{r.status_code}]: {r.text[:400]}")
    return r.json().get("data", r.json())


def generate(source: dict, out_path: str) -> dict:
    """Block until HeyGen has rendered the reel; write it to out_path.
    Returns {"video_id", "session_id", "duration", "prompt"}."""
    key = config.req("HEYGEN_API_KEY")
    prompt = build_prompt(source)
    body = {"prompt": prompt, "mode": "generate", "orientation": "portrait", "incognito_mode": True}
    for opt, field in (("HEYGEN_AVATAR_ID", "avatar_id"), ("HEYGEN_VOICE_ID", "voice_id"),
                       ("HEYGEN_STYLE_ID", "style_id"), ("HEYGEN_BRAND_KIT_ID", "brand_kit_id")):
        if config.opt(opt):
            body[field] = config.opt(opt)

    r = requests.post(f"{API}/video-agents", json=body,
                      headers={"X-Api-Key": key, "Content-Type": "application/json"}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"heygen create failed [{r.status_code}]: {r.text[:400]}")
    session_id = r.json()["data"]["session_id"]
    print(f"[heygen] session {session_id}")

    # Two-stage wait: the agent first plans (no video_id yet), then renders.
    # HeyGen quotes 5-10x the final length, so a 50 s reel can take ~8 minutes.
    deadline = time.time() + int(config.opt("HEYGEN_TIMEOUT", "1800"))
    video_id = None
    while time.time() < deadline and not video_id:
        s = _get(f"/video-agents/{session_id}", key)
        if s.get("status") == "failed":
            raise RuntimeError(f"heygen session failed: {json.dumps(s)[:400]}")
        if s.get("status") == "waiting_for_input":
            raise RuntimeError("heygen session is waiting for input; prompt was ambiguous")
        video_id = s.get("video_id")
        if not video_id:
            time.sleep(10)
    if not video_id:
        raise RuntimeError("heygen never started rendering before timeout")
    print(f"[heygen] rendering {video_id}")

    while time.time() < deadline:
        v = _get(f"/videos/{video_id}", key)
        st = v.get("status")
        if st == "completed" and v.get("video_url"):
            dl = requests.get(v["video_url"], timeout=600)
            dl.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(dl.content)
            return {"video_id": video_id, "session_id": session_id,
                    "duration": v.get("duration"), "prompt": prompt}
        if st == "failed":
            raise RuntimeError(f"heygen render failed: {v.get('failure_code')} {v.get('failure_message')}")
        time.sleep(15)
    raise RuntimeError("heygen render timed out")
