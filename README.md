# Publisher

Daily autonomous poster: Claude researches one interesting *process*, renders it into a
1080×1350 JPEG, and publishes it to a Facebook Page, an Instagram Business account and X.

Fully automatic — no human approval step. If that turns out to be too spicy, the place to
add a gate is between `storage.upload` and the publisher calls in `src/main.py`.

## What gets published

- **Text**: one long body written to fill the platform limit, not a one-liner.
  `src/limits.py` clamps it per network — Instagram 2200 chars / 30 hashtags,
  Facebook 63206, X 280 using X's own weighted count (Latin 1, everything else 2).
  Trimming happens on a word boundary and hashtags are reserved first, so the body
  absorbs the cut and the tags always survive.
- **Image**: a 1080×1350 infographic. A generated flat-vector illustration sits in the
  middle, three headline statistics orbit it with leader lines, the five stages run
  underneath as icon tiles, and a sourced quote closes the frame. Step icons come from a
  65-glyph local SVG set (`templates/icons.json`); the model picks one name per stage from
  that fixed list and anything unrecognised falls back to `gear`.

## The illustration

`src/illustrate.py` asks an image provider for one transparent PNG per post and composites
it into the palette of the day. The style prompt is locked and the palette names are taken
from `render.ACCENTS[theme]`, so a month of posts still reads as one account rather than a
stock bin. The prompt forbids text outright — image models render garbled letters and
nothing here needs them.

Any OpenAI-compatible `/images/generations` endpoint works: point `IMAGE_API_BASE` at
OpenAI, or at a gateway that speaks the same shape. Set `IMAGE_TRANSPARENT=0` for providers
that reject the `background` flag.

**Generation is never fatal.** If the key is missing, the provider is down, or the request
times out after two retries, the run logs it and renders the icon-only frame instead, where
the statistics become a row of cards. The post still goes out.

Cost is one image per day. Skip it with `--no-art` while iterating on layout or text.

## Flow

```
cron 07:00 UTC
  └─ generate.py   Claude + web_search → brief → JSON (title, hook, 5 steps + icons,
     │                                                 3 stats, quote, art brief,
     │                                                 body, x_text, tags, sources)
     ├─ illustrate.py  art brief + palette → image provider → transparent PNG (fail-soft)
     └─ dedupe     data/used_topics.json, slug match
        └─ render.py    templates/template.html → Playwright → out/YYYYMMDD-slug.jpg
           └─ storage.py  → R2/S3 → public https URL (IG requires image_url, not upload)
              └─ limits.py    one body → three clamped captions
              ├─ facebook.py    POST /{page-id}/photos
              ├─ instagram.py   POST /media → poll status → POST /media_publish
              └─ x.py           OAuth1 media_upload + v2 create_tweet
                 └─ commit used_topics.json
```

## Reels

Same topic, second format. After the image post, an optional job hands the day's brief
(title, hook, five stages, statistics, quote) to **HeyGen Video Agent** and gets back a
finished vertical reel: script, voice, b-roll, captions, music -- nothing is assembled here.

```
post job → out/payload.json
  └─ src/shorts/heygen.py   brief → POST /v3/video-agents → poll session → poll video → MP4
     └─ storage.py           → public URL
        ├─ Instagram Reels   /media (REELS) → poll → /media_publish
        ├─ Facebook Page     /videos
        ├─ YouTube Shorts    Data API v3 resumable upload, "#Shorts" in the title
        └─ X                 chunked media_upload + tweet
```

The prompt is built by `heygen.build_prompt()` from the brief and says: use only these
facts, no invented numbers or quotes, portrait, faceless voice-over by default. Print it
without spending anything:

```bash
python -m src.shorts.main --prompt-only
```

Config in `.env.example` under *Reels*. `REEL_LANGUAGE` sets both narration and on-screen
text. `REEL_FACELESS=0` puts a presenter on screen; pair it with `HEYGEN_AVATAR_ID`.

Cost: HeyGen bills the Video Agent per second of output -- roughly $2 per 60 s reel at
2026 list price. Render takes 5-10x the reel length; the job budgets 45 minutes.

Enable it on the schedule with the repo variable `REELS_ENABLED=true`, or tick *reel* on a
manual run. YouTube needs a one-time OAuth: `python scripts/youtube_auth.py client_secret.json`
prints the three `YT_*` secrets.

## Setup

1. **Meta.** Instagram account must be Business/Creator and linked to a Facebook Page.
   In `developers.facebook.com` create a **Business** app, add *Facebook Login* and
   *Instagram Graph API*.
2. **Page token.** Generate a long-lived Page Access Token with `pages_manage_posts`,
   `pages_read_engagement`, `instagram_basic`, `instagram_content_publish`. Lives ~60 days.
   Verify it is a *Page* token (not a User token) in the Access Token Debugger.
3. **IG user id:**
   ```bash
   curl "https://graph.facebook.com/v21.0/{page-id}?fields=instagram_business_account&access_token=$TOKEN"
   ```
4. **X.** Developer Portal project → OAuth 1.0a keys, **Read and Write**. OAuth 1.0a is
   mandatory: media upload does not work with app-only OAuth 2.
5. **Bucket.** Cloudflare R2 or S3 with public read, mapped to a domain → `PUBLIC_BASE_URL`.
6. **Secrets.** Settings → Secrets and variables → Actions:
   `ANTHROPIC_API_KEY`, `PAGE_ID`, `IG_USER_ID`, `PAGE_ACCESS_TOKEN`,
   `X_CONSUMER_KEY`, `X_CONSUMER_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`,
   `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`,
   `PUBLIC_BASE_URL`, `META_APP_ID`, `META_APP_SECRET`, `REPO_PAT`,
   and for reels `HEYGEN_API_KEY`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
   Variables (non-secret): `GRAPH_API_VERSION`, `S3_REGION`, `ANTHROPIC_MODEL`, `BRAND_HANDLE`.
7. **Dry run first.** Actions → *daily-post* → Run workflow with `dry_run: true`.
   Download the `post-*` artifact, look at the JPEG and the caption. Only then let the cron run.

## Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env    # fill it in
python -m src.main --dry-run
```

Render only, no API calls:

```bash
python -m scripts.preview
```

## Design rotation

`render.rotation()` hashes the title into one of 6 palettes × 2 layouts (`cards`, `flow`).
Instagram throttles accounts that post a pixel-identical frame every day, so the deck never
repeats back-to-back. All 12 combinations were rendered and checked for overflow.

Every palette is light: a soft gradient background, two blurred colour washes behind the
content, white cards, dark type, and a saturated accent paired with a second hue that
alternates down the step column. Sky, coral, mint, lemon, lavender, rose.

Add palettes by adding a `body[data-theme="N"]` block and bumping `THEMES` in `render.py`.
A palette needs `--bg1/2/3`, `--fg`, `--muted`, `--accent`, `--accent2`, `--card`, `--tint`,
`--wash1`, `--wash2`.
Add icons by adding a key to `templates/icons.json` — the name is offered to the model
automatically, no prompt edit needed.

The layout auto-fits: the headline shrinks while the page overflows 1350px, then a scale
variable grows the step block into whatever vertical space is left. Short and long copy
both fill the frame. Overflow is measured on the step block, not on `body` -- the decorative
washes are `position: fixed` precisely so they stay out of that measurement.

Override the rotation when testing:

```python
render.render(data, "out/test.jpg", theme=3, layout="cards", art=png_bytes)
```

Four layout paths are covered and were each rendered and checked: illustration present,
illustration missing, quote missing, and only two statistics.

## Failure modes

| Symptom | Cause |
|---|---|
| IG `/media` errors | image is PNG (must be JPEG), URL not publicly readable, or aspect ratio outside 4:5–1.91:1 |
| IG `/media_publish` 500s | container not `FINISHED` yet — handled by `_poll_ready`, raise the retry count if it still trips |
| `(#200) Permissions error` | User token instead of Page token, or `instagram_content_publish` missing |
| `(#190) token expired` | run *refresh-meta-token*; it needs `REPO_PAT` to write the secret back |
| X 403 on media | free tier lost media access — this is the one line item that may need a paid plan |
| JSON parse failure | handled: the format call is prefilled with `{` and retried 3× |
| Frame has no illustration | `IMAGE_API_KEY` unset or the provider failed — check the `[art]` line in the run log |
| Illustration has garbled text in it | the model ignored the no-text instruction; rerun, or lower `IMAGE_SIZE` |
| Reel job: "waiting for input" | HeyGen found the prompt ambiguous; tighten `REEL_*` or add `HEYGEN_STYLE_ID` |
| Reel job times out | raise `HEYGEN_TIMEOUT` and the job's `timeout-minutes` together |
| YouTube 403 `quotaExceeded` | default Data API quota is 10 000 units/day, one upload costs ~1 600 |

## Known unknowns

- **X API tiers move.** The free tier has repeatedly been capped (a few hundred posts/month)
  and has lost media upload at times. Check your current tier before relying on it; if media
  needs a paid plan, that is the only real cost in this project.
- **`v21.0` ages out.** Bump `GRAPH_API_VERSION` when Meta deprecates it.
- **Daily automated posting is rate-limit adjacent.** IG allows 50 API-published posts per
  24h, so 1/day is safe on volume; the risk is reach throttling on repetitive formats, which
  is what the template rotation is for.
