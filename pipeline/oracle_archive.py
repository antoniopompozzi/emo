"""Writes one week's ORACLE output to oracle_archive/<end-date>/:

  final.png          - the published pixelated binary-duotone image
  share_card.png       - final.png plus EMO - ORACLE/week-range/verdict badges
                          baked in, for sharing outside the site (see
                          pipeline/oracle_share_card.py)
  source.png          - the raw (possibly fallback) image before pixelation
  grid_values.json     - the quantized brightness grid behind final.png, plus
                          the week's verdict/color; a raw data trace only, same
                          role as EMO's own grid_values.json
  metadata.json        - week_start, week_end, concept, explanation, verdict,
                          render params, fallback flag
  exchange_log.json    - full request/response trace for Claude and the image
                          provider

Deliberately a separate root from archive/, never nested inside it:
archive.previously_used_links iterates archive_root.iterdir() assuming
every subfolder is an EMO day with headlines in its metadata --
mixing the two archives in one root would break that function.

The folder is named after the week's end date (the run date), not its
start date -- mirrors archive.write_day naming its folder after the
day it ran, and keeps every ORACLE folder name consistent with the
day EMO's own daily commit landed that week.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


def write_week(
    end_date_str: str,
    oracle_archive_root: Path,
    final_image: Image.Image,
    source_image: Image.Image,
    share_image: Image.Image,
    grid: np.ndarray,
    verdict: str,
    verdict_color: str,
    metadata: dict,
    exchange_log: dict,
) -> Path:
    week_dir = oracle_archive_root / end_date_str
    week_dir.mkdir(parents=True, exist_ok=True)

    final_image.save(week_dir / "final.png")
    source_image.save(week_dir / "source.png")
    share_image.save(week_dir / "share_card.png")

    (week_dir / "grid_values.json").write_text(
        json.dumps(
            {
                "grid_cols": grid.shape[1],
                "grid_rows": grid.shape[0],
                "values": grid.tolist(),
                "verdict": verdict,
                "color": verdict_color,
            }
        ),
        encoding="utf-8",
    )
    (week_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (week_dir / "exchange_log.json").write_text(
        json.dumps(exchange_log, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return week_dir
