"""Entry point for EMO's daily pipeline.

Run as: python -m pipeline.main

Reads today's headlines, asks Claude what to depict, generates a
source image, pixelates it into EMO's fixed visual style, and writes
everything to archive/<date>/. Each step degrades gracefully (see
concept.py and image_source.py) so a run always produces a publishable
result, even if news, Claude, or Pollinations are unavailable.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import yaml

from pipeline import archive, concept, image_source, news, postprocess
from pipeline.logging_utils import ExchangeLogger

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(REPO_ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run() -> Path:
    config = load_config()
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    logger = ExchangeLogger()
    date_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    headlines = news.fetch_headlines(config, logger)

    if api_key:
        concept_result = concept.choose_concept(headlines, config, api_key, logger)
    else:
        print("ANTHROPIC_API_KEY is not set; using the fallback concept.", file=sys.stderr)
        logger.log("claude", status="fallback_used", error="ANTHROPIC_API_KEY not set")
        concept_result = dict(concept.FALLBACK_CONCEPT)
        concept_result["used_fallback"] = True

    image_result = image_source.fetch_source_image(concept_result["concept"], config, logger)

    pp_cfg = config["postprocess"]
    final_image = postprocess.pixelate(
        image_result["image"],
        grid_size=pp_cfg["grid_size"],
        gray_levels=pp_cfg["gray_levels"],
        px_per_cell=pp_cfg["px_per_cell"],
    )

    metadata = {
        "date": date_str,
        "concept": concept_result["concept"],
        "explanation": concept_result["explanation"],
        "concept_used_fallback": concept_result["used_fallback"],
        "image_used_fallback": image_result["used_fallback"],
        "headlines": headlines,
        "render_params": pp_cfg,
        "pollinations_params": {
            "model": config["pollinations"]["model"],
            "width": config["pollinations"]["width"],
            "height": config["pollinations"]["height"],
        },
        "claude_model": config["claude"]["model"],
    }

    archive_root = REPO_ROOT / config["paths"]["archive_dir"]
    day_dir = archive.write_day(
        date_str, archive_root, final_image, image_result["image"], metadata, logger.to_dict()
    )
    print(f"Wrote {day_dir}")
    return day_dir


if __name__ == "__main__":
    run()
