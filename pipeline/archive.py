"""Writes one day's output to archive/<date>/:

  final.png          - the published pixelated duotone image
  share_card.png       - final.png plus EMO/date/emotion badges baked in, for
                          sharing outside the site (see pipeline/share_card.py)
  instagram_card.png    - 1080x1350 (4:5) card for Instagram feed posts, rendered
                          independently from final_image with badges in the white
                          margins rather than overlaid (see pipeline/share_card.py);
                          not used by the site itself, kept for manual/future use only
  source.png          - the raw (possibly fallback) image before pixelation
  grid_values.json     - the quantized brightness grid behind final.png, plus the
                          day's emotion/color; kept as a raw data trace only -- the
                          published site reads final.png directly (see
                          website/build_site.py)
  metadata.json        - concept, explanation, emotion, headlines, render params,
                          fallback flags
  exchange_log.json    - full request/response trace for Claude and the image provider
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


def previously_used_links(archive_root: Path, window_days: int | None = None) -> set[str]:
    """Raccoglie i link delle notizie già usate nei giorni precedenti.

    Legge archive/<date>/metadata.json per ogni giorno esistente ed
    estrae il campo "link" di ogni voce in "headlines". Usata da
    pipeline.news per evitare di riprendere una notizia già usata da
    EMO, anche se resta ancora in cima al feed RSS. `window_days`, se
    indicato, limita la ricerca alle N cartelle-giorno più recenti
    invece che a tutto l'archivio, così una notizia molto vecchia può
    tornare a essere selezionabile.
    """
    if not archive_root.exists():
        return set()

    day_dirs = sorted(p for p in archive_root.iterdir() if p.is_dir())
    if window_days is not None:
        day_dirs = day_dirs[-window_days:]

    links: set[str] = set()
    for day_dir in day_dirs:
        metadata_path = day_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for headline in metadata.get("headlines", []):
            link = headline.get("link")
            if link:
                links.add(link)
    return links


def load_recent_days(archive_root: Path, n: int = 7) -> list[dict]:
    """Reads the n most recent EMO days for ORACLE to reread.

    Same iteration model as previously_used_links: the last n day
    folders sorted by name, each metadata.json read once. Returns
    date/concept/explanation/emotion for each, oldest to newest --
    ORACLE reads EMO's own past interpretations, not the raw news, so
    headlines are deliberately left out. Fallback days (concept or
    image generation failed that day) are included with no filtering:
    a day EMO couldn't read the news on is still a real, honestly-told
    part of the week.
    """
    if not archive_root.exists():
        return []

    day_dirs = sorted(p for p in archive_root.iterdir() if p.is_dir())[-n:]

    days: list[dict] = []
    for day_dir in day_dirs:
        metadata_path = day_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        days.append(
            {
                "date": metadata.get("date", day_dir.name),
                "concept": metadata.get("concept", ""),
                "explanation": metadata.get("explanation", ""),
                "emotion": metadata.get("emotion", ""),
            }
        )
    return days


def write_day(
    date_str: str,
    archive_root: Path,
    final_image: Image.Image,
    source_image: Image.Image,
    share_image: Image.Image,
    instagram_image: Image.Image,
    grid: np.ndarray,
    emotion: str,
    emotion_color: str,
    metadata: dict,
    exchange_log: dict,
) -> Path:
    day_dir = archive_root / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    final_image.save(day_dir / "final.png")
    source_image.save(day_dir / "source.png")
    share_image.save(day_dir / "share_card.png")
    instagram_image.save(day_dir / "instagram_card.png")

    (day_dir / "grid_values.json").write_text(
        json.dumps(
            {
                "grid_size": grid.shape[0],
                "values": grid.tolist(),
                "emotion": emotion,
                "color": emotion_color,
            }
        ),
        encoding="utf-8",
    )
    (day_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (day_dir / "exchange_log.json").write_text(
        json.dumps(exchange_log, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return day_dir
