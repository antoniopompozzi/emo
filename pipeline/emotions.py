"""EMO's fixed emotion palette.

Each day, Claude extracts a single dominant emotion from the news (see
concept.py) and it gets mapped to one of these hex colors for the
duotone pixelation (see postprocess.render_grid). Kept as one small,
standalone module because both concept.py (to validate what Claude
returns) and postprocess.py / the website's script.js (to render the
duotone) need the same palette as their single source of truth.

Site copy is English-only (see README), so the emotion names are too.
"""
from __future__ import annotations

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
