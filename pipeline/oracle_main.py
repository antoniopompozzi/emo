"""Entry point for ORACLE's weekly pipeline.

Run as: python -m pipeline.oracle_main

Rereads EMO's own concept/explanation from the seven most recent
archived days (see pipeline.archive.load_recent_days) -- not the raw
news -- and asks Claude to imagine, from that week of EMO's own
interpretations alone, what future awaits humanity: a binary verdict
(positive/negative) rendered as a black-to-verdict-color duotone,
same fixed pixelation pipeline as EMO, on the same square grid.
Each step degrades gracefully on the same model as pipeline.main, so a
run always produces a publishable result even without live API keys.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from pipeline import archive, image_provider, oracle_archive, oracle_concept, oracle_share_card, postprocess
from pipeline.logging_utils import ExchangeLogger
from pipeline.oracle_palette import DEFAULT_VERDICT, ORACLE_PALETTE

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
    end_date = dt.datetime.now(dt.timezone.utc).date()
    end_date_str = end_date.strftime("%Y-%m-%d")
    week_start_str = (end_date - dt.timedelta(days=6)).strftime("%Y-%m-%d")

    archive_root = REPO_ROOT / config["paths"]["archive_dir"]
    recent_days = archive.load_recent_days(archive_root, n=7)

    if anthropic_api_key:
        concept_result = oracle_concept.choose_concept(recent_days, config, anthropic_api_key, logger)
    else:
        print("ANTHROPIC_API_KEY is not set; using the fallback concept.", file=sys.stderr)
        logger.log("claude", status="fallback_used", error="ANTHROPIC_API_KEY not set")
        concept_result = dict(oracle_concept.FALLBACK_CONCEPT)
        concept_result["used_fallback"] = True

    oracle_cfg = config["oracle"]

    if openai_api_key:
        image_result = image_provider.fetch_source_image(
            concept_result["concept"], config, openai_api_key, logger, size_override=oracle_cfg["image_size"]
        )
    else:
        print("OPENAI_API_KEY is not set; using a local placeholder image.", file=sys.stderr)
        logger.log("image_provider", provider="openai", status="fallback_used", error="OPENAI_API_KEY not set")
        image_result = {
            "image": image_provider.local_placeholder(
                concept_result["concept"], config, size_override=oracle_cfg["image_size"]
            ),
            "used_fallback": True,
        }

    verdict = concept_result.get("verdict", DEFAULT_VERDICT)
    verdict_color = ORACLE_PALETTE.get(verdict, ORACLE_PALETTE[DEFAULT_VERDICT])

    grid = postprocess.quantize_grid(
        image_result["image"],
        grid_cols=oracle_cfg["grid_cols"],
        grid_rows=oracle_cfg["grid_rows"],
        gray_levels=config["postprocess"]["gray_levels"],
    )
    final_image = postprocess.render_grid(grid, px_per_cell=config["postprocess"]["px_per_cell"], hue_hex=verdict_color)
    share_image = oracle_share_card.render_oracle_share_card(
        final_image, week_start_str, end_date_str, verdict, config
    )

    metadata = {
        "week_start": week_start_str,
        "week_end": end_date_str,
        "concept": concept_result["concept"],
        "explanation": concept_result["explanation"],
        "verdict": verdict,
        "verdict_color": verdict_color,
        "used_fallback": concept_result["used_fallback"] or image_result["used_fallback"],
        "concept_used_fallback": concept_result["used_fallback"],
        "image_used_fallback": image_result["used_fallback"],
        "claude_model": config["claude"]["model"],
        "render_params": {
            "grid_cols": oracle_cfg["grid_cols"],
            "grid_rows": oracle_cfg["grid_rows"],
            "gray_levels": config["postprocess"]["gray_levels"],
            "px_per_cell": config["postprocess"]["px_per_cell"],
        },
        "image_provider_params": {
            "provider": "openai",
            "model": config["openai_image"]["model"],
            "quality": config["openai_image"]["quality"],
            "size": oracle_cfg["image_size"],
        },
    }

    oracle_archive_root = REPO_ROOT / config["paths"]["oracle_archive_dir"]
    week_dir = oracle_archive.write_week(
        end_date_str,
        oracle_archive_root,
        final_image,
        image_result["image"],
        share_image,
        grid,
        verdict,
        verdict_color,
        metadata,
        logger.to_dict(),
    )
    print(f"Wrote {week_dir}")
    return week_dir


if __name__ == "__main__":
    run()
