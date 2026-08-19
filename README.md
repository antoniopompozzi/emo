# EMO

EMO is a generative art artifact that publishes one pixelated, duotone image every day,
generated from that day's international news. It runs fully automatically on a daily
GitHub Actions schedule, at no recurring cost.

## How a day's image comes to be

1. **News** ([pipeline/news.py](pipeline/news.py)) — fetch the day's top headlines from the
   BBC World News RSS feed, falling back to Google News' World section if BBC is unreachable.
2. **Concept** ([pipeline/concept.py](pipeline/concept.py)) — send the headlines to Claude
   Haiku and let it freely decide what to depict: an object, a scene, a reference to a known
   artwork, an abstract composition, anything the news evokes (literally, obliquely, or not at
   all). Claude returns a JSON object with an image-generation `concept` and a short English
   `explanation` of its choice.
3. **Source image** ([pipeline/image_provider.py](pipeline/image_provider.py)) — send the
   concept to OpenAI's Images API (`gpt-image-1.5`) to render a source image. This is the only
   module that talks to an image generation service, so swapping providers again later only
   means changing this one file.
4. **Pixelation** ([pipeline/postprocess.py](pipeline/postprocess.py)) — a fixed, deterministic
   transform turns *any* source image into EMO's visual signature: grayscale brightness →
   box-filter downsample to a grid of cells (`quantize_grid`) → quantize to a handful of
   brightness levels → render each cell as a sharp-edged solid block, interpolated between
   black and that day's emotion color instead of black and white (`render_grid`, see Task 4
   below). This step never calls an AI model, so the output style is always consistent.
5. **Archive** ([pipeline/archive.py](pipeline/archive.py)) — write the day's `final.png`,
   unprocessed `source.png`, `grid_values.json` (the quantized brightness grid behind
   `final.png`, plus that day's emotion/color -- kept as raw data for reference, not used by
   the site itself), `metadata.json` (concept, explanation, emotion, headlines, render params),
   and `exchange_log.json` (the full Claude + image provider request/response trace) to
   `archive/<YYYY-MM-DD>/`.
6. **Site** ([website/build_site.py](website/build_site.py)) — render the static site from
   every `archive/*/metadata.json`: the homepage shows today's `final.png` large and centered,
   scaled to fit the screen (never cropped or stretched) with `image-rendering: pixelated` so
   the blocks stay crisp, with an "EMO" label and "WHY THIS IMAGE?" / "ARCHIVE" buttons
   overlaid; `/archive/` lists every previous day as a thumbnail gallery; `days/<date>/` shows
   that exact same layout for an archived day (see [website/templates/_hero.html](website/templates/_hero.html),
   shared by both routes).

Dates use UTC throughout, matching the GitHub Actions schedule.

## Graceful degradation

Every network step can fail, and EMO is designed to publish something every day regardless:

- If **both** RSS feeds fail, the pipeline continues with an empty headline list and asks
  Claude to decide freely, noting that no headlines were available.
- If the **Claude call** fails (or its JSON can't be parsed) after retries, a fixed fallback
  concept is used instead (a "static/noise" image, with an explanation that says outright that
  the AI step failed that day).
- If **OpenAI image generation** fails after retries (or `OPENAI_API_KEY` isn't set), a
  deterministic local placeholder image (seeded from a hash of the concept text) is generated
  and pixelated instead, so the visual style stays consistent even without the external service.

Every fallback is recorded in that day's `metadata.json` (`concept_used_fallback`,
`image_used_fallback`) and shown on the site itself, rather than hidden.

## Project layout

```
config.yaml                 all tunable parameters (feed URLs, model, grid size, retries, ...)
pipeline/
  news.py                   RSS fetching with fallback feed
  concept.py                Claude call + fallback concept
  image_provider.py         OpenAI Images API call + fallback placeholder image
  postprocess.py            deterministic duotone/pixelate/quantize transform
  archive.py                writes archive/<date>/
  logging_utils.py          structured request/response logger
  main.py                   orchestrates one full daily run
website/
  build_site.py             renders the static site from archive/
  templates/                Jinja2 templates (base/index/day/archive/_hero)
  static/style.css
  static/script.js          "why this image?" modal
archive/                    one folder per published day (committed to the repo)
tests/                      pytest tests, mainly for postprocess.py and the fallback paths
.github/workflows/daily.yml scheduled pipeline run + site build + GitHub Pages deploy
```

## Running locally

```bash
pip install -r requirements.txt

# Copy .env.example to .env and fill in your own keys -- pipeline/main.py
# loads it automatically. Without a key, that step's fallback runs instead
# (fixed concept, or a local placeholder image), so the pipeline still
# completes end to end.
cp .env.example .env

python -m pipeline.main

# Rebuilds the static site into _site/ from whatever is in archive/.
python website/build_site.py

pytest
```

### API keys

- `ANTHROPIC_API_KEY` — Claude Haiku, the concept-generation step. Get one at
  [console.anthropic.com](https://console.anthropic.com/).
- `OPENAI_API_KEY` — OpenAI's Images API (`gpt-image-1.5`, `quality: medium`,
  `size: 1024x1024`), the image-generation step. Get one at
  [platform.openai.com/api-keys](https://platform.openai.com/api-keys). At OpenAI's published
  pricing at the time this was written, one `medium`-quality `1024x1024` image costs roughly
  **$0.02-0.07** — check [openai.com/api/pricing](https://openai.com/api/pricing) for the
  current rate, since the daily workflow generates exactly one image per day (~$1-2/month).

Never hardcode either key — both are read from the environment only (`.env` locally,
repository secrets in CI, see Automation below).

## Automation

[.github/workflows/daily.yml](.github/workflows/daily.yml) runs once a day (06:00 UTC): it
executes the pipeline, commits the new `archive/<date>/` folder, rebuilds the site, and deploys
it to GitHub Pages. It needs two secrets, set under Settings → Secrets and variables → Actions:
`ANTHROPIC_API_KEY` and `OPENAI_API_KEY`.

The same workflow also runs on every push to `main` (ignoring pushes that only touch
`archive/`, i.e. its own commits) — but on a push it skips straight to rebuilding and
redeploying the site from whatever is already in `archive/`, without running the pipeline
again. That's what makes template/CSS/JS changes go live immediately, instead of sitting
unpublished until the next scheduled run.

To enable publishing: in the repository's Settings → Pages, set the source to
"GitHub Actions".
