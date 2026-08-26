import json

import numpy as np
from PIL import Image

from pipeline.oracle_archive import write_week


def test_write_week_writes_all_expected_files(tmp_path):
    oracle_archive_root = tmp_path / "oracle_archive"
    grid = np.zeros((96, 144), dtype=np.uint8)
    metadata = {
        "week_start": "2026-08-20",
        "week_end": "2026-08-26",
        "concept": "a horizon",
        "explanation": "an undecided mood",
        "verdict": "negative",
        "verdict_color": "#5c1620",
        "used_fallback": False,
    }

    week_dir = write_week(
        "2026-08-26",
        oracle_archive_root,
        Image.new("RGB", (1440, 960), color=(20, 10, 15)),
        Image.new("RGB", (1536, 1024), color=(20, 10, 15)),
        Image.new("RGB", (1080, 720), color=(20, 10, 15)),
        grid,
        "negative",
        "#5c1620",
        metadata,
        {"claude": [], "image_provider": []},
    )

    assert week_dir == oracle_archive_root / "2026-08-26"
    assert (week_dir / "final.png").exists()
    assert (week_dir / "source.png").exists()
    assert (week_dir / "share_card.png").exists()

    grid_values = json.loads((week_dir / "grid_values.json").read_text(encoding="utf-8"))
    assert grid_values["grid_cols"] == 144
    assert grid_values["grid_rows"] == 96
    assert grid_values["verdict"] == "negative"
    assert grid_values["color"] == "#5c1620"

    written_metadata = json.loads((week_dir / "metadata.json").read_text(encoding="utf-8"))
    assert written_metadata == metadata

    exchange_log = json.loads((week_dir / "exchange_log.json").read_text(encoding="utf-8"))
    assert exchange_log == {"claude": [], "image_provider": []}


def test_write_week_names_folder_after_end_date_not_start_date(tmp_path):
    oracle_archive_root = tmp_path / "oracle_archive"
    grid = np.zeros((2, 2), dtype=np.uint8)

    week_dir = write_week(
        "2026-08-26",
        oracle_archive_root,
        Image.new("RGB", (10, 10)),
        Image.new("RGB", (10, 10)),
        Image.new("RGB", (10, 10)),
        grid,
        "positive",
        "#f3ead9",
        {"week_start": "2026-08-20", "week_end": "2026-08-26"},
        {},
    )

    assert week_dir.name == "2026-08-26"
    assert not (oracle_archive_root / "2026-08-20").exists()
