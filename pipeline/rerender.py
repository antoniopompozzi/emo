"""Re-renders an already-archived day from its own source.png.

Run as: python -m pipeline.rerender <YYYY-MM-DD> [--backup-dir DIR]

Exists because the postprocess rule is not frozen forever: when it
changes (the 2026-09-11 tone curve and brightened render palette were
the first such change), a day already in the archive can be brought
onto the new rule without asking Claude or the image provider for
anything again.

What it touches, all of it derived from source.png:
    final.png, grid_values.json, share_card.png and instagram_card.png
    (each only if that day already has one), plus the derived fields of
    metadata.json -- emotion_color, emotion_base_color, render_params.

What it must never touch: source.png, the news, the concept, the
explanation, the emotion, the fallback flags, exchange_log.json. The
day's *content* was decided by Claude on the day and stays decided;
only the fixed transformation downstream of it is replayed.

This is a deliberately separate entry point from pipeline.main. It does
NOT reach into main.run() or its "archive already exists for today"
guard: that guard protects the daily workflow from two triggers firing
on the same date, and re-rendering must not become a way around it.
Running this module never generates a new day, and running the daily
pipeline never re-renders an old one.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

from pipeline import postprocess, share_card
from pipeline.emotions import DEFAULT_EMOTION, EMOTION_PALETTE, RENDER_PALETTE
from pipeline.main import REPO_ROOT, load_config

# Rebuilt from final_image when the day already has them; the site reads
# share_card.png (SHARE button, og:image), instagram_card.png is kept for
# manual use. Days archived before either existed simply don't get one.
DERIVED_CARDS = ("share_card.png", "instagram_card.png")


def _reordered(metadata: dict, emotion_color: str, emotion_base_color: str, render_params: dict) -> dict:
    """Returns metadata with the derived fields refreshed, key order preserved.

    emotion_base_color is inserted right after emotion_color rather than
    appended, so a re-rendered day's metadata.json has the same shape as
    one written fresh by pipeline.main.
    """
    updated: dict = {}
    for key, value in metadata.items():
        if key == "emotion_base_color":
            continue  # re-inserted below, in its canonical position
        if key == "emotion_color":
            updated["emotion_color"] = emotion_color
            updated["emotion_base_color"] = emotion_base_color
        elif key == "render_params":
            updated["render_params"] = render_params
        else:
            updated[key] = value
    return updated


def rerender_day(date_str: str, archive_root: Path, config: dict, backup_dir: Path | None = None) -> Path:
    day_dir = archive_root / date_str
    metadata_path = day_dir / "metadata.json"
    source_path = day_dir / "source.png"
    if not metadata_path.exists() or not source_path.exists():
        raise FileNotFoundError(f"{day_dir} non ha metadata.json e source.png: niente da rielaborare.")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    emotion = metadata.get("emotion") or DEFAULT_EMOTION
    emotion_base_color = EMOTION_PALETTE.get(emotion, EMOTION_PALETTE[DEFAULT_EMOTION])
    emotion_color = RENDER_PALETTE.get(emotion, RENDER_PALETTE[DEFAULT_EMOTION])

    if backup_dir is not None:
        target = backup_dir / date_str
        target.mkdir(parents=True, exist_ok=True)
        for name in ("final.png", "grid_values.json", "metadata.json", *DERIVED_CARDS):
            if (day_dir / name).exists():
                shutil.copy2(day_dir / name, target / name)
        print(f"Copia della versione precedente in {target}")

    pp_cfg = config["postprocess"]
    source_image = Image.open(source_path)
    grid = postprocess.quantize_grid(
        source_image,
        grid_size=pp_cfg["grid_size"],
        gray_levels=pp_cfg["gray_levels"],
        tone_curve_gamma=pp_cfg["tone_curve_gamma"],
    )
    final_image = postprocess.render_grid(grid, px_per_cell=pp_cfg["px_per_cell"], hue_hex=emotion_color)
    final_image.save(day_dir / "final.png")

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

    if (day_dir / "share_card.png").exists():
        share_card.render_share_card(final_image, date_str, emotion, emotion_color, config).save(
            day_dir / "share_card.png"
        )
    if (day_dir / "instagram_card.png").exists():
        share_card.render_instagram_card(final_image, date_str, emotion, emotion_color).save(
            day_dir / "instagram_card.png"
        )

    metadata_path.write_text(
        json.dumps(
            _reordered(metadata, emotion_color, emotion_base_color, pp_cfg), indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )

    print(f"Rielaborato {day_dir} (emozione {emotion}, {emotion_base_color} -> {emotion_color})")
    return day_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("date", help="giorno d'archivio da rielaborare, formato YYYY-MM-DD")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=None,
        help="cartella dove copiare i file del giorno prima di sovrascriverli",
    )
    args = parser.parse_args(argv)

    config = load_config()
    archive_root = REPO_ROOT / config["paths"]["archive_dir"]
    rerender_day(args.date, archive_root, config, args.backup_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
