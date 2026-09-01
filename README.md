# Publisher

Daily autonomous poster: Claude researches one interesting *process*, renders it into a
1080×1350 JPEG, and publishes it to a Facebook Page, an Instagram Business account and X.

Fully automatic — no human approval step. If that turns out to be too spicy, the place to
add a gate is between `storage.upload` and the publisher calls in `src/main.py`.

## Flow

```
cron 07:00 UTC
  └─ generate.py   Claude + web_search → brief → JSON (title, hook, 5 steps, caption, tags)
     └─ dedupe     data/used_topics.json, slug match
        └─ render.py    templates/template.html → Playwright → out/YYYYMMDD-slug.jpg
           └─ storage.py  → R2/S3 → public https URL (IG requires image_url, not upload)
              ├─ facebook.py    POST /{page-id}/photos
              ├─ instagram.py   POST /media → poll status → POST /media_publish
              └─ x.py           OAuth1 media_upload + v2 create_tweet
                 └─ commit used_topics.json
```

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
   `PUBLIC_BASE_URL`, `META_APP_ID`, `META_APP_SECRET`, `REPO_PAT`.
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

`render.rotation()` hashes the title into one of 5 palettes × 2 layouts. Instagram throttles
accounts that post a pixel-identical frame every day, so the deck never repeats back-to-back.
Add palettes by adding a `body[data-theme="N"]` block and bumping `THEMES` in `render.py`.

## Failure modes

| Symptom | Cause |
|---|---|
| IG `/media` errors | image is PNG (must be JPEG), URL not publicly readable, or aspect ratio outside 4:5–1.91:1 |
| IG `/media_publish` 500s | container not `FINISHED` yet — handled by `_poll_ready`, raise the retry count if it still trips |
| `(#200) Permissions error` | User token instead of Page token, or `instagram_content_publish` missing |
| `(#190) token expired` | run *refresh-meta-token*; it needs `REPO_PAT` to write the secret back |
| X 403 on media | free tier lost media access — this is the one line item that may need a paid plan |
| JSON parse failure | handled: the format call is prefilled with `{` and retried 3× |

## Known unknowns

- **X API tiers move.** The free tier has repeatedly been capped (a few hundred posts/month)
  and has lost media upload at times. Check your current tier before relying on it; if media
  needs a paid plan, that is the only real cost in this project.
- **`v21.0` ages out.** Bump `GRAPH_API_VERSION` when Meta deprecates it.
- **Daily automated posting is rate-limit adjacent.** IG allows 50 API-published posts per
  24h, so 1/day is safe on volume; the risk is reach throttling on repetitive formats, which
  is what the template rotation is for.
