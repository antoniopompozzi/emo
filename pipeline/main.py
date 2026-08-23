"""Entry point for EMO's daily pipeline.

Run as: python -m pipeline.main

Reads today's headlines, asks Claude what to depict (plus a dominant
emotion for the day), generates a source image, pixelates it into
EMO's fixed visual style -- a black-to-emotion-color duotone -- and
writes everything to archive/<date>/. Each step degrades gracefully
(see concept.py and image_provider.py) so a run always produces a
publishable result, even if news, Claude, or the image provider are
unavailable.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from pipeline import archive, concept, image_provider, news, postprocess, share_card
from pipeline.emotions import DEFAULT_EMOTION, EMOTION_PALETTE
from pipeline.logging_utils import ExchangeLogger

REPO_ROOT = Path(__file__).resolve().parent.parent

# Loads variables from a local .env file if one exists (see .env.example);
# a no-op when it doesn't, so this is safe in CI where the real secrets
# are already injected as environment variables by GitHub Actions.
load_dotenv(REPO_ROOT / ".env")


def load_config() -> dict:
    with open(REPO_ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run() -> Path:
    config = load_config()
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    logger = ExchangeLogger()
    date_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    archive_root = REPO_ROOT / config["paths"]["archive_dir"]
    exclude_links = archive.previously_used_links(
        archive_root, window_days=config["news"].get("dedup_window_days")
    )
    headlines = news.fetch_headlines(config, logger, exclude_links=exclude_links)

    if anthropic_api_key:
        concept_result = concept.choose_concept(headlines, config, anthropic_api_key, logger)
    else:
        print("ANTHROPIC_API_KEY is not set; using the fallback concept.", file=sys.stderr)
        logger.log("claude", status="fallback_used", error="ANTHROPIC_API_KEY not set")
        concept_result = dict(concept.FALLBACK_CONCEPT)
        concept_result["used_fallback"] = True

    if openai_api_key:
        image_result = image_provider.fetch_source_image(
            concept_result["concept"], config, openai_api_key, logger
        )
    else:
        print("OPENAI_API_KEY is not set; using a local placeholder image.", file=sys.stderr)
        logger.log("image_provider", provider="openai", status="fallback_used", error="OPENAI_API_KEY not set")
        image_result = {
            "image": image_provider.local_placeholder(concept_result["concept"], config),
            "used_fallback": True,
        }

    emotion = concept_result.get("emotion", DEFAULT_EMOTION)
    emotion_color = EMOTION_PALETTE.get(emotion, EMOTION_PALETTE[DEFAULT_EMOTION])

    pp_cfg = config["postprocess"]
    grid = postprocess.quantize_grid(
        image_result["image"], grid_size=pp_cfg["grid_size"], gray_levels=pp_cfg["gray_levels"]
    )
    final_image = postprocess.render_grid(grid, px_per_cell=pp_cfg["px_per_cell"], hue_hex=emotion_color)
    share_image = share_card.render_share_card(final_image, date_str, emotion, emotion_color, config)
    instagram_image = share_card.render_instagram_card(final_image, date_str, emotion, emotion_color)

    metadata = {
        "date": date_str,
        "concept": concept_result["concept"],
        "explanation": concept_result["explanation"],
        "emotion": emotion,
        "emotion_color": emotion_color,
        "concept_used_fallback": concept_result["used_fallback"],
        "image_used_fallback": image_result["used_fallback"],
        "headlines": headlines,
        "render_params": pp_cfg,
        "image_provider_params": {
            "provider": "openai",
            "model": config["openai_image"]["model"],
            "quality": config["openai_image"]["quality"],
            "size": config["openai_image"]["size"],
        },
        "claude_model": config["claude"]["model"],
    }

    day_dir = archive.write_day(
        date_str,
        archive_root,
        final_image,
        image_result["image"],
        share_image,
        instagram_image,
        grid,
        emotion,
        emotion_color,
        metadata,
        logger.to_dict(),
    )
    print(f"Wrote {day_dir}")
    return day_dir


if __name__ == "__main__":
    run()
