"""Writes one day's output to archive/<date>/:

  final.png          - the published pixelated image
  source.png          - the raw (possibly fallback) image before pixelation
  grid_values.json     - the quantized gray-value grid behind final.png, for the
                          homepage's <canvas> renderer (see website/static/script.js)
  metadata.json        - concept, explanation, headlines, render params, fallback flags
  exchange_log.json    - full request/response trace for Claude and the image provider
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


def write_day(
    date_str: str,
    archive_root: Path,
    final_image: Image.Image,
    source_image: Image.Image,
    grid: np.ndarray,
    metadata: dict,
    exchange_log: dict,
) -> Path:
    day_dir = archive_root / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    final_image.save(day_dir / "final.png")
    source_image.save(day_dir / "source.png")

    (day_dir / "grid_values.json").write_text(
        json.dumps({"grid_size": grid.shape[0], "values": grid.tolist()}),
        encoding="utf-8",
    )
    (day_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (day_dir / "exchange_log.json").write_text(
        json.dumps(exchange_log, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return day_dir
