"""Step 1: pick an interesting process via web search, return validated JSON."""
import json
import os
import re
import unicodedata

import anthropic

from . import config

ICON_NAMES = sorted(json.load(open(os.path.join(config.ROOT, "templates", "icons.json"))).keys())

RESEARCH_PROMPT = """Find ONE genuinely interesting *process* worth explaining in 5 steps.
Any field: AI, medicine, IT, biology, logistics, materials, energy, space.

Hard requirements:
- Prefer something that appeared in the news or in research within the last 12 months.
- It must be a PROCESS (a sequence of stages), not a product announcement or an opinion.
- Do NOT pick any of these already-used topics: {used}

Use web search to verify the process is real and get the stages right.
Then write a detailed factual brief containing:
- the title and why it matters
- the 5 stages in order, with what physically happens at each one
- HARD NUMBERS: at least three concrete, verifiable figures (percentages, counts, durations,
  temperatures, costs). These are the headline statistics of the post, so they must be real
  and traceable to a source, never estimated or rounded from nothing.
- one short direct quote from a named researcher, engineer or institution, if the sources
  contain one. If none of your sources has a usable quote, say so explicitly instead of
  inventing one.
- the current open problem or limitation
Cite the sources you used.
"""

FORMAT_PROMPT = """Turn this brief into a social-media post payload.

BRIEF:
{brief}

Return ONLY a JSON object, no prose, no markdown fences, with exactly this shape:
{{
  "title": "max 45 chars, no trailing period",
  "hook": "one sentence, max 95 chars",
  "field": "one lowercase word, e.g. biology",
  "steps": [
    {{"n": 1, "label": "3-5 words", "text": "max 80 chars, what physically happens",
      "icon": "one name from the icon list"}}
  ],
  "stats": [{{"value": "98.5%", "label": "max 45 chars, what the number measures"}}],
  "quote": {{"text": "max 110 chars, verbatim from a source", "who": "name, role or institution"}},
  "art": "one sentence describing a single illustration subject for this process. Concrete and "
         "visual, e.g. 'a laboratory bioreactor vessel with coiled tubing and floating molecule "
         "shapes around it'. No text or labels in the scene.",
  "body": "{body_min}-{body_max} characters. This is the post text itself, so write it in full: "
          "open with the hook, walk through all 5 stages in prose with the concrete numbers, "
          "close with the open problem and why it matters. Plain text. Blank lines between "
          "paragraphs are fine. No hashtags, no markdown, no links.",
  "x_text": "max 230 characters, standalone, must make sense with no image and no thread",
  "hashtags": ["#one", "..."],
  "sources": ["https://..."]
}}

Rules:
- Exactly 5 steps, numbered 1..5.
- 3 stats. "value" is short and punchy (max 7 chars, e.g. "98.5%", "30 L", "-70C"). Every one
  must come from the brief -- do not invent or re-round figures.
- "quote" must be verbatim from the brief. If the brief has no usable quote, set it to null.
  Never fabricate a quote or an attribution.
- "body" MUST be at least {body_min} characters. Use the full length; do not summarise.
- 6-12 hashtags, each starting with #, lowercase, no spaces inside.
- "icon" MUST be chosen from this list, pick the closest match for that stage:
{icons}
"""

BODY_MIN = 900
BODY_MAX = 2000


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
    for k in ("title", "hook", "steps", "body", "x_text", "hashtags", "stats"):
        if k not in d:
            raise ValueError(f"missing key: {k}")
    if len(d["steps"]) != 5:
        raise ValueError(f"expected 5 steps, got {len(d['steps'])}")
    if len(d["body"]) < BODY_MIN:
        # Retrying is cheaper than publishing a thin post into a 2200-char slot.
        raise ValueError(f"body too short: {len(d['body'])} < {BODY_MIN}")
    for i, s in enumerate(d["steps"], 1):
        s["n"] = i
        s["label"] = str(s["label"]).strip()
        s["text"] = str(s["text"]).strip()
        icon = str(s.get("icon", "")).strip().lower()
        s["icon"] = icon if icon in ICON_NAMES else "gear"  # render falls back anyway
    stats = []
    for st in d.get("stats", []):
        value, label = str(st.get("value", "")).strip(), str(st.get("label", "")).strip()
        if value and label:
            stats.append({"value": value[:8], "label": label})
    if len(stats) < 2:
        raise ValueError(f"need at least 2 usable stats, got {len(stats)}")
    d["stats"] = stats[:3]

    q = d.get("quote")
    # A fabricated quote is worse than no quote, so anything malformed is dropped outright.
    if isinstance(q, dict) and str(q.get("text", "")).strip() and str(q.get("who", "")).strip():
        d["quote"] = {"text": str(q["text"]).strip().strip('"“”'), "who": str(q["who"]).strip()}
    else:
        d["quote"] = None

    d["art"] = str(d.get("art", "")).strip()
    d["hashtags"] = [
        re.sub(r"\s+", "", h if h.startswith("#") else "#" + h) for h in d["hashtags"]
    ][:12]
    d["sources"] = d.get("sources", [])
    return d


def generate(retries: int = 3) -> dict:
    client = anthropic.Anthropic(api_key=config.req("ANTHROPIC_API_KEY"))
    used = load_used()
    used_titles = [u["title"] for u in used][-80:]

    research = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=3000,
        tools=[{"type": config.WEB_SEARCH_TOOL, "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": RESEARCH_PROMPT.format(used=json.dumps(used_titles))}],
    )
    brief = _text(research)
    if not brief:
        raise RuntimeError("research call returned no text")

    prompt = FORMAT_PROMPT.format(
        brief=brief, icons=", ".join(ICON_NAMES), body_min=BODY_MIN, body_max=BODY_MAX
    )
    last_err = None
    for _ in range(retries):
        # Prefill "{" forces raw JSON. No tools on this call, so prefill is allowed.
        msg = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=3000,
            messages=[
                {"role": "user", "content": prompt},
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
