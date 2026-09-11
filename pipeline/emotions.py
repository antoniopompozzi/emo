"""EMO's fixed emotion palette, plus the rule that brightens it for rendering.

Each day, Claude extracts a single dominant emotion from the news (see
concept.py) and it gets mapped to one of these hex colors for the
duotone pixelation (see postprocess.render_grid). Kept as one small,
standalone module because both concept.py (to validate what Claude
returns) and postprocess.py / the website's script.js (to render the
duotone) need the same palette as their single source of truth.

Site copy is English-only (see README), so the emotion names are too.

Two palettes, one derived from the other by a fixed rule:

  EMOTION_PALETTE  - the base identity color of each emotion. This is
                     the palette of record (thesis, CLAUDE.md); it is
                     NOT what gets painted since 2026-09-11.
  RENDER_PALETTE   - what render_grid actually receives, obtained by
                     applying `brighten_for_render` to every entry.

Splitting them keeps the emotion->color mapping a documented constant
while the brightening stays a rule with one parameter, rather than
seven hand-picked new hex values.
"""
from __future__ import annotations

import colorsys

EMOTION_PALETTE: dict[str, str] = {
    "anger": "#c0392b",
    "sadness": "#2e5c9a",
    "fear": "#5b2c6f",
    "joy": "#d4a017",
    "surprise": "#1a9e8f",
    "disgust": "#556b2f",
    "neutral": "#555555",
}

DEFAULT_EMOTION = "neutral"

# How far each color is pushed toward full brightness, as a fraction of
# the headroom it still has (see brighten_for_render). 0.5 was chosen so
# fear's #5b2c6f lands on #9649b7, the value validated on the 2026-09-11
# preview; every other emotion follows from the same number.
BRIGHTNESS_LIFT = 0.5


def _hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def brighten_for_render(hex_color: str, lift: float = BRIGHTNESS_LIFT) -> str:
    """Raises a color's HSV value, leaving hue and saturation untouched.

    V' = V + lift * (1 - V) -- a *relative* lift of the remaining
    headroom, not an absolute target value. That matters: an absolute
    target would darken any emotion already brighter than it (joy's
    #d4a017 sits at V 0.83), while this rule can only ever brighten,
    and brightens the dark emotions most. Hue and saturation are carried
    over untouched, so each emotion keeps its own chromatic family and
    stays distinct from the others -- fear stays a purple, disgust stays
    an olive green.
    """
    h, s, v = colorsys.rgb_to_hsv(*_hex_to_rgb01(hex_color))
    r, g, b = colorsys.hsv_to_rgb(h, s, v + lift * (1.0 - v))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


# The colors actually painted into final.png since 2026-09-11.
RENDER_PALETTE: dict[str, str] = {
    emotion: brighten_for_render(color) for emotion, color in EMOTION_PALETTE.items()
}
