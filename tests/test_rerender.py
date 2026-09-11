import json

import numpy as np
import pytest
from PIL import Image

from pipeline import main as pipeline_main
from pipeline.emotions import EMOTION_PALETTE, RENDER_PALETTE
from pipeline.rerender import rerender_day

DAY = "2026-01-02"


@pytest.fixture
def config(tmp_path):
    return {
        "postprocess": {"grid_size": 8, "gray_levels": 10, "px_per_cell": 4, "tone_curve_gamma": 0.7},
        "share_card": {"size": 64},
        "paths": {"archive_dir": str(tmp_path / "archive")},
    }


@pytest.fixture
def day_dir(tmp_path):
    """An archived day rendered the pre-2026-09-11 way: no curve, base palette."""
    day_dir = tmp_path / "archive" / DAY
    day_dir.mkdir(parents=True)

    rng = np.random.default_rng(3)
    source = Image.fromarray(rng.integers(0, 120, size=(64, 64, 3), dtype=np.uint8), mode="RGB")
    source.save(day_dir / "source.png")

    from pipeline import postprocess

    old_grid = postprocess.quantize_grid(source, 8, 10, tone_curve_gamma=1.0)
    postprocess.render_grid(old_grid, 4, EMOTION_PALETTE["fear"]).save(day_dir / "final.png")
    (day_dir / "grid_values.json").write_text(
        json.dumps({"grid_size": 8, "values": old_grid.tolist(), "emotion": "fear", "color": "#5b2c6f"}),
        encoding="utf-8",
    )
    (day_dir / "metadata.json").write_text(
        json.dumps(
            {
                "date": DAY,
                "concept": "a concept decided on the day",
                "explanation": "an explanation decided on the day",
                "emotion": "fear",
                "emotion_color": "#5b2c6f",
                "concept_used_fallback": False,
                "image_used_fallback": False,
                "headlines": [{"title": "t", "summary": "s", "link": "http://example.test/a"}],
                "render_params": {"grid_size": 8, "gray_levels": 10, "px_per_cell": 4},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (day_dir / "exchange_log.json").write_text('{"steps": []}', encoding="utf-8")
    return day_dir


def test_rerender_repaints_with_the_current_rule(day_dir, config):
    before = (day_dir / "final.png").read_bytes()
    rerender_day(DAY, day_dir.parent, config)

    assert (day_dir / "final.png").read_bytes() != before
    metadata = json.loads((day_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["emotion_color"] == RENDER_PALETTE["fear"]
    assert metadata["emotion_base_color"] == EMOTION_PALETTE["fear"]
    assert metadata["render_params"]["tone_curve_gamma"] == 0.7

    grid_values = json.loads((day_dir / "grid_values.json").read_text(encoding="utf-8"))
    assert grid_values["color"] == RENDER_PALETTE["fear"]
    assert grid_values["emotion"] == "fear"


def test_rerender_leaves_the_days_content_untouched(day_dir, config):
    source_before = (day_dir / "source.png").read_bytes()
    log_before = (day_dir / "exchange_log.json").read_bytes()
    metadata_before = json.loads((day_dir / "metadata.json").read_text(encoding="utf-8"))

    rerender_day(DAY, day_dir.parent, config)

    assert (day_dir / "source.png").read_bytes() == source_before
    assert (day_dir / "exchange_log.json").read_bytes() == log_before
    metadata_after = json.loads((day_dir / "metadata.json").read_text(encoding="utf-8"))
    for key in ("date", "concept", "explanation", "emotion", "headlines",
                "concept_used_fallback", "image_used_fallback"):
        assert metadata_after[key] == metadata_before[key]


def test_rerender_only_rebuilds_cards_the_day_already_had(day_dir, config):
    # This day predates share_card.png, so re-rendering must not invent one.
    rerender_day(DAY, day_dir.parent, config)
    assert not (day_dir / "share_card.png").exists()
    assert not (day_dir / "instagram_card.png").exists()

    Image.new("RGB", (10, 10)).save(day_dir / "share_card.png")
    placeholder = (day_dir / "share_card.png").read_bytes()
    rerender_day(DAY, day_dir.parent, config)
    assert (day_dir / "share_card.png").read_bytes() != placeholder
    assert not (day_dir / "instagram_card.png").exists()


def test_rerender_keeps_metadata_key_order_stable(day_dir, config):
    rerender_day(DAY, day_dir.parent, config)
    keys = list(json.loads((day_dir / "metadata.json").read_text(encoding="utf-8")))
    assert keys.index("emotion_base_color") == keys.index("emotion_color") + 1
    # Idempotent: a second pass must not duplicate or move the field.
    rerender_day(DAY, day_dir.parent, config)
    assert list(json.loads((day_dir / "metadata.json").read_text(encoding="utf-8"))) == keys


def test_rerender_writes_backup_when_asked(day_dir, config, tmp_path):
    final_before = (day_dir / "final.png").read_bytes()
    backup = tmp_path / "backup"
    rerender_day(DAY, day_dir.parent, config, backup_dir=backup)

    assert (backup / DAY / "final.png").read_bytes() == final_before
    assert json.loads((backup / DAY / "metadata.json").read_text(encoding="utf-8"))["emotion_color"] == "#5b2c6f"


def test_rerender_refuses_a_day_that_is_not_archived(tmp_path, config):
    with pytest.raises(FileNotFoundError):
        rerender_day("2026-01-03", tmp_path / "archive", config)


def test_rerender_does_not_reach_into_the_daily_pipeline_guard(day_dir, config, monkeypatch):
    # Re-rendering must never become a way around main.run()'s
    # "archive already exists for today" skip.
    def explode(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("rerender must not invoke the daily pipeline")

    monkeypatch.setattr(pipeline_main, "run", explode)
    rerender_day(DAY, day_dir.parent, config)
