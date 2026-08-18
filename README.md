# EMO

EMO is a generative art artifact that publishes one pixelated, grayscale image every day,
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
3. **Source image** ([pipeline/image_source.py](pipeline/image_source.py)) — send the concept
   to [Pollinations.ai](https://pollinations.ai) (free, no API key) to render a source image.
4. **Pixelation** ([pipeline/postprocess.py](pipeline/postprocess.py)) — a fixed, deterministic
   transform turns *any* source image into EMO's visual signature: grayscale → box-filter
   downsample to a grid of cells (`quantize_grid`) → quantize to a handful of gray levels →
   render each cell as a sharp-edged solid block (`render_grid`). This step never calls an AI
   model, so the output style is always consistent.
5. **Archive** ([pipeline/archive.py](pipeline/archive.py)) — write the day's `final.png`,
   unprocessed `source.png`, `grid_values.json` (the quantized gray-value grid behind
   `final.png`, used by the homepage's `<canvas>` renderer), `metadata.json` (concept,
   explanation, headlines, render params), and `exchange_log.json` (the full Claude +
   Pollinations request/response trace) to `archive/<YYYY-MM-DD>/`.
6. **Site** ([website/build_site.py](website/build_site.py)) — render the static site from
   every `archive/*/metadata.json`: the homepage shows today's grid full-screen with an "EMO"
   label and "WHY THIS IMAGE?" / "ARCHIVE" buttons overlaid; `/archive/` lists every previous
   day as a thumbnail gallery; `days/<date>/` gives each day its own permanent page.
   The homepage draws its grid on a `<canvas>` from `grid_values.json` (see
   [website/static/script.js](website/static/script.js)) instead of showing `final.png`
   directly, so the cell size can adapt to any screen — phone or desktop, portrait or
   landscape — without cropping the square image or blowing it up past its native
   resolution. Individual day pages still show the plain `final.png` full-bleed.

Dates use UTC throughout, matching the GitHub Actions schedule.

## Graceful degradation

Every network step can fail, and EMO is designed to publish something every day regardless:

- If **both** RSS feeds fail, the pipeline continues with an empty headline list and asks
  Claude to decide freely, noting that no headlines were available.
- If the **Claude call** fails (or its JSON can't be parsed) after retries, a fixed fallback
  concept is used instead (a "static/noise" image, with an explanation that says outright that
  the AI step failed that day).
- If **Pollinations** fails after retries, a deterministic local placeholder image (seeded from
  a hash of the concept text) is generated and pixelated instead, so the visual style stays
  consistent even without the external service.

Every fallback is recorded in that day's `metadata.json` (`concept_used_fallback`,
`image_used_fallback`) and shown on the site itself, rather than hidden.

## Project layout

```
config.yaml                 all tunable parameters (feed URLs, model, grid size, retries, ...)
pipeline/
  news.py                   RSS fetching with fallback feed
  concept.py                Claude call + fallback concept
  image_source.py           Pollinations call + fallback placeholder image
  postprocess.py            deterministic grayscale/pixelate/quantize transform
  archive.py                writes archive/<date>/
  logging_utils.py          structured request/response logger
  main.py                   orchestrates one full daily run
website/
  build_site.py             renders the static site from archive/
  templates/                Jinja2 templates (base/index/day/archive)
  static/style.css
  static/script.js          homepage grid canvas + "why this image?" modal
archive/                    one folder per published day (committed to the repo)
tests/                      pytest tests, mainly for postprocess.py and the fallback paths
.github/workflows/daily.yml scheduled pipeline run + site build + GitHub Pages deploy
```

## Running locally

```bash
pip install -r requirements.txt

# Requires ANTHROPIC_API_KEY in the environment (falls back to the
# static/noise concept if unset).
python -m pipeline.main

# Rebuilds the static site into _site/ from whatever is in archive/.
python website/build_site.py

pytest
```

## Automation

[.github/workflows/daily.yml](.github/workflows/daily.yml) runs once a day (06:00 UTC): it
executes the pipeline, commits the new `archive/<date>/` folder, rebuilds the site, and deploys
it to GitHub Pages. The only secret it needs is `ANTHROPIC_API_KEY`
(Settings → Secrets and variables → Actions). Pollinations.ai needs no key.

To enable publishing: in the repository's Settings → Pages, set the source to
"GitHub Actions".
