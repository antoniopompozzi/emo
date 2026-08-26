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


def test_oracle_share_card_preserves_aspect_ratio_instead_of_forcing_square():
    # ORACLE's final image is panoramic (3:2, e.g. 1440x960) -- the share
    # card must scale it down proportionally, never force it square the
    # way render_share_card does for EMO's own square images.
    source = Image.new("RGB", (1440, 960), color=(50, 10, 10))
    config = {"share_card": {"size": 720}}
    card = render_oracle_share_card(source, "2026-08-20", "2026-08-26", "negative", config)
    assert card.size == (720, 480)
    assert card.mode == "RGB"


def test_oracle_share_card_respects_a_different_source_aspect_ratio():
    source = Image.new("RGB", (2000, 1000), color=(50, 10, 10))
    config = {"share_card": {"size": 400}}
    card = render_oracle_share_card(source, "2026-08-20", "2026-08-26", "positive", config)
    assert card.size == (400, 200)
