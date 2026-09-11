import colorsys

import pytest

from pipeline.emotions import (
    BRIGHTNESS_LIFT,
    DEFAULT_EMOTION,
    EMOTION_PALETTE,
    RENDER_PALETTE,
    brighten_for_render,
)


def _hsv(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    rgb = tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(*rgb)


def test_render_palette_covers_exactly_the_base_palette():
    assert RENDER_PALETTE.keys() == EMOTION_PALETTE.keys()
    assert DEFAULT_EMOTION in RENDER_PALETTE


@pytest.mark.parametrize("emotion", sorted(EMOTION_PALETTE))
def test_rendering_never_darkens_an_emotion(emotion):
    # The point of a relative lift rather than an absolute target
    # brightness: joy (#d4a017) is already bright and must not be
    # dragged down to meet the dark emotions.
    _, _, base_v = _hsv(EMOTION_PALETTE[emotion])
    _, _, render_v = _hsv(RENDER_PALETTE[emotion])
    assert render_v > base_v


@pytest.mark.parametrize("emotion", sorted(EMOTION_PALETTE))
def test_rendering_keeps_the_emotion_chromatic_family(emotion):
    base_h, base_s, _ = _hsv(EMOTION_PALETTE[emotion])
    render_h, render_s, _ = _hsv(RENDER_PALETTE[emotion])
    # Tolerances absorb 8-bit rounding only: fear stays a purple,
    # disgust stays an olive green, nothing drifts to a new hue.
    assert render_h == pytest.approx(base_h, abs=0.005)
    assert render_s == pytest.approx(base_s, abs=0.01)


def test_render_colors_stay_distinct_from_each_other():
    assert len(set(RENDER_PALETTE.values())) == len(RENDER_PALETTE)


def test_fear_matches_the_validated_preview_color():
    # The value signed off on the 2026-09-11 preview; every other
    # emotion is derived from the same BRIGHTNESS_LIFT.
    assert RENDER_PALETTE["fear"] == "#9649b7"


def test_lift_is_a_fraction_of_the_remaining_headroom():
    _, _, v = _hsv(brighten_for_render("#000000"))
    assert v == pytest.approx(BRIGHTNESS_LIFT, abs=0.005)
    # White has no headroom left, so the rule is a no-op on it.
    assert brighten_for_render("#ffffff") == "#ffffff"


def test_zero_lift_returns_the_base_color():
    for color in EMOTION_PALETTE.values():
        assert brighten_for_render(color, lift=0.0) == color
