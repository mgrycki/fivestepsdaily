"""Per-platform text limits. Every caption is clamped here, never sent raw."""

FB_LIMIT = 63206          # Facebook post body
IG_LIMIT = 2200           # Instagram caption
IG_HASHTAG_MAX = 30       # Instagram rejects the post above this
X_LIMIT = 280             # free tier; X Premium raises it to 25000

# X counts most Latin text as 1 per char and everything else as 2, capped at 280.
_X_SINGLE_RANGES = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))


def x_weight(text: str) -> int:
    total = 0
    for ch in text:
        cp = ord(ch)
        total += 1 if any(lo <= cp <= hi for lo, hi in _X_SINGLE_RANGES) else 2
    return total


def _trim_to(text: str, budget: int, weighted: bool = False) -> str:
    """Cut on a word boundary and mark the cut, so captions never end mid-word."""
    measure = x_weight if weighted else len
    if measure(text) <= budget:
        return text
    out = text
    while out and measure(out + "…") > budget:
        cut = out.rstrip()
        out = cut[: cut.rfind(" ")] if " " in cut else cut[:-1]
    return (out.rstrip(" ,;:-") + "…") if out else ""


def compose(body: str, hashtags: list, limit: int, max_tags: int = 30) -> str:
    """Fill the platform limit: hashtags are reserved first, the body absorbs the trim."""
    tags = [t for t in hashtags][:max_tags]
    tail = ("\n\n" + " ".join(tags)) if tags else ""
    # Drop tags one at a time if even a minimal body cannot fit alongside them.
    while tags and len(tail) > limit // 2:
        tags.pop()
        tail = ("\n\n" + " ".join(tags)) if tags else ""
    return _trim_to(body, limit - len(tail)) + tail


def for_facebook(body: str, hashtags: list) -> str:
    return compose(body, hashtags, FB_LIMIT)


def for_instagram(body: str, hashtags: list) -> str:
    return compose(body, hashtags, IG_LIMIT, max_tags=IG_HASHTAG_MAX)


def for_x(text: str, limit: int = X_LIMIT) -> str:
    return _trim_to(text, limit, weighted=True)
