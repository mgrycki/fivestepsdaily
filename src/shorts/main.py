"""Reel run: topic -> HeyGen Video Agent -> upload -> publish."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

from .. import config, costs, disclosure, generate, limits, notify, storage
from . import heygen
from . import publish as pub


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="render the reel, publish nothing")
    ap.add_argument("--from-payload", default=os.path.join(config.OUT_DIR, "payload.json"),
                    help="reuse the topic of an already generated post")
    ap.add_argument("--fresh", action="store_true", help="ignore payload.json, research a new topic")
    ap.add_argument("--prompt-only", action="store_true", help="print the HeyGen prompt and stop")
    ap.add_argument("--targets", default=config.opt("REEL_TARGETS", "instagram,facebook,youtube,x"))
    args = ap.parse_args()
    targets = [t.strip().lower() for t in args.targets.split(",") if t.strip()]

    if not args.fresh and os.path.exists(args.from_payload):
        source = json.load(open(args.from_payload))["data"]
        print(f"[topic] reusing '{source['title']}'")
    else:
        source = generate.generate()
        print(f"[topic] fresh '{source['title']}'")

    if args.prompt_only:
        print(heygen.build_prompt(source))
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    slug = generate.slug(source["title"])[:50]
    os.makedirs(config.OUT_DIR, exist_ok=True)
    path = os.path.join(config.OUT_DIR, f"reel-{stamp}-{slug}.mp4")
    est = int(config.opt("REEL_SECONDS", "50")) * costs.PRICING["heygen_second"]
    if not costs.guard(est, "HeyGen reel"):
        return 3
    r = heygen.generate(source, path)
    costs.record("heygen_second", float(r.get("duration") or config.opt("REEL_SECONDS", "50")),
                 run=f"reel-{stamp}-{slug}")
    print(f"[reel] {path} ({os.path.getsize(path)} bytes, {r.get('duration')}s)")

    body = f"{source['title']}\n\n{source['body']}"
    caps = {
        "instagram": limits.for_instagram(body, source["hashtags"], suffix=disclosure.CAPTION),
        "facebook": limits.for_facebook(body, source["hashtags"], suffix=disclosure.CAPTION),
        "youtube": limits.compose(body, source["hashtags"], 5000, suffix=disclosure.CAPTION),
        "x": limits.for_x(source["x_text"], int(config.opt("X_CHAR_LIMIT", str(limits.X_LIMIT))),
                          suffix=disclosure.X_TAG),
    }
    with open(os.path.join(config.OUT_DIR, "reel.json"), "w") as f:
        json.dump({"heygen": r, "captions": caps}, f, indent=2, ensure_ascii=False)

    if args.dry_run:
        print("\n--- DRY RUN, nothing published ---")
        print(r["prompt"])
        return 0

    video_url = storage.upload(path, f"reels/{stamp}/{slug}.mp4")
    print(f"[upload] {video_url}")

    results, failures = {}, []
    for net in targets:
        try:
            if net == "instagram":
                results[net] = pub.instagram(video_url, caps["instagram"])
            elif net == "facebook":
                results[net] = pub.facebook(video_url, caps["facebook"], source["title"])
            elif net == "youtube":
                results[net] = pub.youtube(path, source["title"], caps["youtube"], source["hashtags"])
            elif net == "x":
                results[net] = pub.x(path, caps["x"])
        except Exception as e:  # one dead network must not block the others
            failures.append(f"{net}: {e}")
    for net, pid in results.items():
        print(f"[ok] {net}: {pid}")
    for f in failures:
        print(f"[fail] {f}", file=sys.stderr)
    notify.summary("reel", source["title"], results, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
