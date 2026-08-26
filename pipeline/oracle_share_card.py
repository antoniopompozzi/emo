"""Renders ORACLE's share card: the week's final image with pixel-art
badges (EMO - ORACLE brand, week range, verdict) baked directly into
the pixels.

Reuses _badge_layout and _draw_pixel_badge from pipeline/share_card.py
(that module's docstring says explicitly they are meant to be shared)
so a proportion change only ever has to happen in one place. ORACLE's
final image is square (1024x1024, same grid/cell size as EMO's own
daily image) -- render_oracle_share_card forces a square resize just
like render_share_card does for EMO.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

from pipeline.oracle_palette import ORACLE_PALETTE
from pipeline.share_card import _badge_layout, _draw_pixel_badge, _hex_to_rgb

_MONTH_ABBR = {
    1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
}


def format_week_range(start_str: str, end_str: str) -> str:
    """"2026-08-20", "2026-08-26" -> "AUG 20-26".

    Same month -> one month abbreviation shared by both ends. Crossing
    a month boundary -> the abbreviation is repeated on both ends, e.g.
    "2026-12-27", "2027-01-02" -> "DEC 27-JAN 2". No year shown, same
    convention as the daily share card's date badge.

    Public (not module-private) because website/build_site.py also
    calls it, to compute each archived week's range_label.
    """
    start_year, start_month, start_day = (int(part) for part in start_str.split("-"))
    _, end_month, end_day = (int(part) for part in end_str.split("-"))

    if start_month == end_month:
        return f"{_MONTH_ABBR[start_month]} {start_day}–{end_day}"
    return f"{_MONTH_ABBR[start_month]} {start_day}–{_MONTH_ABBR[end_month]} {end_day}"


def render_oracle_share_card(
    final_image: Image.Image,
    week_start: str,
    week_end: str,
    verdict: str,
    config: dict,
) -> Image.Image:
    """Returns a size x size RGB share card built from final_image, with
    badges overlaid directly on the (already square) resized image --
    same logic as share_card.render_share_card for EMO's own daily card.
    """
    size = config["share_card"]["size"]
    card = final_image.resize((size, size), resample=Image.NEAREST).convert("RGB")
    draw = ImageDraw.Draw(card)
    layout = _badge_layout(size)

    _draw_pixel_badge(
        draw,
        (layout.margin, layout.margin),
        "EMO - ORACLE",
        layout.title_font,
        border_width=layout.border_width,
        pad_x=layout.title_pad_x,
        pad_y=layout.title_pad_y,
        anchor="top-left",
    )

    week_label = format_week_range(week_start, week_end)
    verdict_label = verdict.upper()
    bottom_y = size - layout.margin

    week_w, _ = _draw_pixel_badge(
        draw,
        (layout.margin, bottom_y),
        week_label,
        layout.badge_font,
        border_width=layout.border_width,
        pad_x=layout.badge_pad_x,
        pad_y=layout.badge_pad_y,
        anchor="bottom-left",
    )
    _draw_pixel_badge(
        draw,
        (layout.margin + week_w + layout.badge_gap, bottom_y),
        verdict_label,
        layout.badge_font,
        border_width=layout.border_width,
        pad_x=layout.badge_pad_x,
        pad_y=layout.badge_pad_y,
        anchor="bottom-left",
        swatch_color=_hex_to_rgb(ORACLE_PALETTE[verdict]),
        swatch_size=layout.swatch_size,
        swatch_gap=layout.swatch_gap,
    )

    return card
