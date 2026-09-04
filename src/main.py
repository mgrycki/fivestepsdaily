"""Daily run: research -> dedupe -> render -> upload -> publish -> record."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

from . import config, generate, illustrate, limits, render, storage
from .publishers import facebook, instagram
from .publishers import x as xpub


def build_captions(data: dict) -> dict:
    """One body, three clamps. Each network gets as much text as it actually allows."""
    body = f"{data['title']}\n\n{data['body']}"
    x_limit = int(config.opt("X_CHAR_LIMIT", str(limits.X_LIMIT)))
    return {
        "facebook": limits.for_facebook(body, data["hashtags"]),
        "instagram": limits.for_instagram(body, data["hashtags"]),
        "x": limits.for_x(data["x_text"], x_limit),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="generate + render, print everything, publish nothing")
    ap.add_argument("--targets", default=",".join(config.TARGETS),
                    help="comma list: facebook,instagram,x")
    ap.add_argument("--attempts", type=int, default=3,
                    help="how many topics to try before giving up on dedupe")
    ap.add_argument("--no-art", action="store_true",
                    help="skip illustration generation (no image-provider spend)")
    ap.add_argument("--from-payload", default="",
                    help="path to a ready payload JSON (written by the Claude routine); "
                         "skips research and needs no ANTHROPIC_API_KEY")
    args = ap.parse_args()
    targets = [t.strip().lower() for t in args.targets.split(",") if t.strip()]

    used = generate.load_used()
    data = None
    if args.from_payload:
        with open(args.from_payload, encoding="utf-8") as f:
            raw = json.load(f)
        # Same validator the API path uses, so a hand-written payload gets the same guarantees.
        data = generate.validate(raw.get("data", raw))
        if generate.is_duplicate(data, used):
            print(f"[fatal] payload topic '{data['title']}' already used", file=sys.stderr)
            return 2
        print(f"[topic] from payload: '{data['title']}'")
    else:
        for attempt in range(1, args.attempts + 1):
            candidate = generate.generate()
            if generate.is_duplicate(candidate, used):
                print(f"[dedupe] '{candidate['title']}' already used (attempt {attempt})", file=sys.stderr)
                continue
            data = candidate
            break
    if data is None:
        print("[fatal] only duplicates after all attempts", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    slug = generate.slug(data["title"])[:60]
    local = os.path.join(config.OUT_DIR, f"{stamp}-{slug}.jpg")

    theme, _ = render.rotation(data["title"])
    art = None
    if not args.no_art:
        # Palette-matched so the illustration belongs to today's frame, not to a stock set.
        art = illustrate.generate(data, *render.ACCENTS[theme])
        if art:
            with open(os.path.join(config.OUT_DIR, f"{stamp}-{slug}-art.png"), "wb") as f:
                f.write(art)
    print(f"[art] {'generated' if art else 'none, icon-only frame'}")

    render.render(data, local, handle=config.opt("BRAND_HANDLE", ""), art=art)
    print(f"[render] {local} ({os.path.getsize(local)} bytes)")

    caps = build_captions(data)
    with open(os.path.join(config.OUT_DIR, "payload.json"), "w") as f:
        json.dump({"data": data, "captions": caps}, f, indent=2, ensure_ascii=False)

    print(f"[text] fb={len(caps['facebook'])}/{limits.FB_LIMIT} "
          f"ig={len(caps['instagram'])}/{limits.IG_LIMIT} "
          f"x={limits.x_weight(caps['x'])} weighted")

    if args.dry_run:
        print("\n--- DRY RUN, nothing published ---")
        for net in ("facebook", "instagram", "x"):
            print(f"\n===== {net.upper()} =====\n{caps[net]}")
        return 0

    image_url = storage.upload(local, f"posts/{stamp}/{slug}.jpg")
    print(f"[upload] {image_url}")

    results, failures = {}, []
    if "facebook" in targets:
        try:
            results["facebook"] = facebook.publish(image_url, caps["facebook"])
        except Exception as e:  # one dead network must not block the others
            failures.append(f"facebook: {e}")
    if "instagram" in targets:
        try:
            results["instagram"] = instagram.publish(image_url, caps["instagram"])
        except Exception as e:
            failures.append(f"instagram: {e}")
    if "x" in targets:
        try:
            results["x"] = xpub.publish(local, caps["x"])
        except Exception as e:
            failures.append(f"x: {e}")

    for net, post_id in results.items():
        print(f"[ok] {net}: {post_id}")
    for f in failures:
        print(f"[fail] {f}", file=sys.stderr)

    # Only burn the topic if it actually reached at least one timeline.
    if results:
        generate.save_used(used, data)
        print(f"[used] recorded '{data['title']}'")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
