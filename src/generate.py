"""Step 1: pick an interesting process via web search, return validated JSON."""
import json
import os
import re
import unicodedata

import anthropic

from . import config

RESEARCH_PROMPT = """Find ONE genuinely interesting *process* worth explaining in 5 steps.
Any field: AI, medicine, IT, biology, logistics, materials, energy, space.

Hard requirements:
- Prefer something that appeared in the news or in research within the last 12 months.
- It must be a PROCESS (a sequence of stages), not a product announcement or an opinion.
- Do NOT pick any of these already-used topics: {used}

Use web search to verify the process is real and get the stages right.
Then write a short factual brief: the title, what it is, and the 5 stages in order.
Cite the sources you used.
"""

FORMAT_PROMPT = """Turn this brief into a social-media post payload.

BRIEF:
{brief}

Return ONLY a JSON object, no prose, no markdown fences, with exactly this shape:
{{
  "title": "max 45 chars, no trailing period",
  "hook": "one sentence, max 90 chars",
  "steps": [{{"n": 1, "label": "3-5 words", "text": "max 12 words"}}],
  "caption": "120-180 chars, plain text, no hashtags inside",
  "hashtags": ["#one", "#two", "#three", "#four", "#five"],
  "field": "one word domain, e.g. biology",
  "sources": ["https://..."]
}}
Exactly 5 steps, numbered 1..5. Hashtags: 3-6 items, each starts with #.
"""


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def load_used() -> list:
    if not os.path.exists(config.USED_TOPICS):
        return []
    with open(config.USED_TOPICS) as f:
        return json.load(f)


def save_used(used: list, data: dict) -> None:
    used.append({"slug": slug(data["title"]), "title": data["title"], "field": data.get("field", "")})
    os.makedirs(os.path.dirname(config.USED_TOPICS), exist_ok=True)
    with open(config.USED_TOPICS, "w") as f:
        json.dump(used[-500:], f, indent=2, ensure_ascii=False)


def _text(msg) -> str:
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def validate(d: dict) -> dict:
    for k in ("title", "hook", "steps", "caption", "hashtags"):
        if k not in d:
            raise ValueError(f"missing key: {k}")
    if len(d["steps"]) != 5:
        raise ValueError(f"expected 5 steps, got {len(d['steps'])}")
    for i, s in enumerate(d["steps"], 1):
        s["n"] = i
        s["label"] = str(s["label"]).strip()
        s["text"] = str(s["text"]).strip()
    d["hashtags"] = [h if h.startswith("#") else "#" + h for h in d["hashtags"]][:6]
    return d


def generate(retries: int = 3) -> dict:
    client = anthropic.Anthropic(api_key=config.req("ANTHROPIC_API_KEY"))
    used = load_used()
    used_titles = [u["title"] for u in used][-80:]

    research = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=2000,
        tools=[{"type": config.WEB_SEARCH_TOOL, "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": RESEARCH_PROMPT.format(used=json.dumps(used_titles))}],
    )
    brief = _text(research)
    if not brief:
        raise RuntimeError("research call returned no text")

    last_err = None
    for _ in range(retries):
        # Prefill "{" forces raw JSON. No tools on this call, so prefill is allowed.
        msg = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1200,
            messages=[
                {"role": "user", "content": FORMAT_PROMPT.format(brief=brief)},
                {"role": "assistant", "content": "{"},
            ],
        )
        raw = "{" + _text(msg)
        try:
            return validate(json.loads(raw))
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
    raise RuntimeError(f"could not get valid JSON after {retries} tries: {last_err}")


def is_duplicate(data: dict, used: list) -> bool:
    return slug(data["title"]) in {u["slug"] for u in used}
