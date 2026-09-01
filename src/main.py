"""Daily run: research -> dedupe -> render -> upload -> publish -> record."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

from . import config, generate, render, storage
from .publishers import facebook, instagram
from .publishers import x as xpub


def build_captions(data: dict) -> tuple:
    tags = " ".join(data["hashtags"])
    long_caption = f"{data['title']}\n\n{data['caption']}\n\n{tags}"
    short = f"{data['title']} — {data['caption']}"
    if len(short) > 240:
        short = f"{data['title']} — {data['hook']}"
    short = f"{short}\n\n{' '.join(data['hashtags'][:2])}"
    return long_caption, short


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="generate + render, print everything, publish nothing")
    ap.add_argument("--targets", default=",".join(config.TARGETS),
                    help="comma list: facebook,instagram,x")
    ap.add_argument("--attempts", type=int, default=3,
                    help="how many topics to try before giving up on dedupe")
    args = ap.parse_args()
    targets = [t.strip().lower() for t in args.targets.split(",") if t.strip()]

    used = generate.load_used()
    data = None
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
    render.render(data, local, handle=config.opt("BRAND_HANDLE", ""))
    print(f"[render] {local} ({os.path.getsize(local)} bytes)")

    long_caption, short_caption = build_captions(data)
    with open(os.path.join(config.OUT_DIR, "payload.json"), "w") as f:
        json.dump({"data": data, "caption": long_caption, "short": short_caption}, f,
                  indent=2, ensure_ascii=False)

    if args.dry_run:
        print("\n--- DRY RUN, nothing published ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("\nFB/IG caption:\n" + long_caption)
        print("\nX text:\n" + short_caption)
        return 0

    image_url = storage.upload(local, f"posts/{stamp}/{slug}.jpg")
    print(f"[upload] {image_url}")

    results, failures = {}, []
    if "facebook" in targets:
        try:
            results["facebook"] = facebook.publish(image_url, long_caption)
        except Exception as e:  # one dead network must not block the others
            failures.append(f"facebook: {e}")
    if "instagram" in targets:
        try:
            results["instagram"] = instagram.publish(image_url, long_caption)
        except Exception as e:
            failures.append(f"instagram: {e}")
    if "x" in targets:
        try:
            results["x"] = xpub.publish(local, short_caption)
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
