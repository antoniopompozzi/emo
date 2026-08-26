from PIL import Image

from pipeline.oracle_share_card import format_week_range, render_oracle_share_card


def test_format_week_range_within_the_same_month():
    assert format_week_range("2026-08-20", "2026-08-26") == "AUG 20–26"


def test_format_week_range_across_a_month_boundary():
    assert format_week_range("2026-12-27", "2027-01-02") == "DEC 27–JAN 2"


def test_format_week_range_shows_no_year():
    label = format_week_range("2026-08-20", "2026-08-26")
    assert "2026" not in label
    label_cross_month = format_week_range("2026-12-27", "2027-01-02")
    assert "2026" not in label_cross_month and "2027" not in label_cross_month


def test_oracle_share_card_is_size_by_size_rgb():
    # ORACLE's final image is square (1024x1024, same grid/cell size as
    # EMO's own daily image) -- same square-forcing resize as
    # share_card.render_share_card, not an aspect-ratio-preserving one.
    source = Image.new("RGB", (960, 960), color=(50, 10, 10))
    config = {"share_card": {"size": 720}}
    card = render_oracle_share_card(source, "2026-08-20", "2026-08-26", "negative", config)
    assert card.size == (720, 720)
    assert card.mode == "RGB"
