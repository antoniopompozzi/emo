from PIL import Image

from pipeline.share_card import render_instagram_card, render_share_card


def test_share_card_is_size_by_size_rgb():
    source = Image.new("RGB", (960, 960), color=(20, 40, 80))
    config = {"share_card": {"size": 400}}
    card = render_share_card(source, "2026-08-20", "sadness", "#2e5c9a", config)
    assert card.size == (400, 400)
    assert card.mode == "RGB"


def test_instagram_card_is_1080x1350_rgb():
    source = Image.new("RGB", (960, 960), color=(20, 40, 80))
    config = {"share_card": {"size": 400}}
    card = render_instagram_card(source, "2026-08-20", "sadness", "#2e5c9a", config)
    assert card.size == (1080, 1350)
    assert card.mode == "RGB"
