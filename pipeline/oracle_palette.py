"""ORACLE's fixed binary palette.

Same schema as pipeline/emotions.py, but ORACLE's verdict is always
one of exactly two values -- there is no "neutral" default, since a
binary reduction of the week's mood is the point (see
pipeline/oracle_concept.py for how an unparsable verdict still gets
normalized to one of these two, never dropped).
"""
from __future__ import annotations

ORACLE_PALETTE: dict[str, str] = {
    "positive": "#f3ead9",
    "negative": "#5c1620",
}

DEFAULT_VERDICT = "negative"
