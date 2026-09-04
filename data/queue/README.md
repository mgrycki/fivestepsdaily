# Payload queue

One file per day, written by the Claude routine, named `YYYY-MM-DD.json`. Pushing a new file
to `main` is what starts the publish workflow. Files stay here afterwards as the archive.

Schema (validated by `src/generate.py:validate` — a file that fails validation fails the run):

```json
{
  "title": "max 45 chars, no trailing period",
  "hook": "one sentence, max 95 chars",
  "field": "one lowercase word, e.g. biology",
  "steps": [
    {"n": 1, "label": "3-5 words", "text": "max 80 chars, what physically happens",
     "icon": "a key from templates/icons.json"}
  ],
  "stats": [{"value": "max 7 chars, e.g. 98.5%", "label": "max 45 chars, what it measures"}],
  "quote": {"text": "max 110 chars, verbatim from a source", "who": "name, role or institution"},
  "art": "one sentence: a single concrete illustration subject, no text in the scene",
  "body": "900-2000 chars, the post text itself, plain, blank lines between paragraphs, no hashtags, no links",
  "x_text": "max 230 chars, standalone",
  "hashtags": ["#six", "#to", "#twelve", "#lowercase"],
  "sources": ["https://..."]
}
```

Rules the validator enforces: exactly 5 steps; 2-3 stats; body >= 900 chars; `quote` may be
`null` and is dropped if it lacks text or attribution; unknown icons fall back to `gear`.
The title must not match anything in `data/used_topics.json` (slug comparison).
