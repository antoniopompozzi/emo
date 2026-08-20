"""Renders EMO's share cards: the day's final.png with pixel-art badges
(EMO brand, date, emotion) baked directly into the pixels.

This exists because the site's real badges are HTML/CSS overlaid on
top of <img class="hero-image">, which only exist inside the page --
anything shared outside it (a downloaded PNG, a social preview
scraping og:image) needs those badges burned into the image itself.

Two variants share the same badge styling (see _badge_layout and
_draw_pixel_badge below), sized off one `size`/`width` value so both
stay in proportional sync with each other and with .brand-label /
.pixel-btn / .emotion-swatch in style.css:

  render_share_card()     - size x size, badges overlaid on the image,
                             used on-site (og:image) and for download/copy-link
  render_instagram_card() - fixed 1080x1350 (Instagram's 4:5 feed ratio),
                             badges in white margins instead of overlaid;
                             manual/future use only, not wired into the site
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = REPO_ROOT / "website" / "static" / "fonts" / "PressStart2P-Regular.ttf"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Instagram's current recommended feed post ratio (4:5, taller than
# it is wide) -- fixed regardless of share_card.size in config.yaml,
# since it's a platform constraint, not a site-visual choice.
INSTAGRAM_CARD_WIDTH = 1080
INSTAGRAM_CARD_HEIGHT = 1350


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


class _BadgeLayout(NamedTuple):
    border_width: int
    margin: int
    badge_gap: int
    title_font: ImageFont.FreeTypeFont
    badge_font: ImageFont.FreeTypeFont
    title_pad_x: int
    title_pad_y: int
    badge_pad_x: int
    badge_pad_y: int
    swatch_size: int
    swatch_gap: int


def _badge_layout(size: int) -> _BadgeLayout:
    """Badge sizing constants derived from `size`, shared by both card
    renderers so a proportion change (e.g. to match a style.css tweak)
    only has to happen in one place. Padding ratios mirror .brand-label
    (pad 0.6rem/0.9rem over a 1.5rem font) and .pixel-btn (pad
    0.65rem/0.85rem over a 0.65rem font) in style.css.
    """
    title_font_size = round(size * 0.035)
    badge_font_size = round(size * 0.02)
    return _BadgeLayout(
        border_width=max(2, round(size / 400)),  # ~2-3px at the default 1080 size
        margin=round(size * 0.045),
        badge_gap=round(size * 0.02),
        title_font=ImageFont.truetype(str(FONT_PATH), title_font_size),
        badge_font=ImageFont.truetype(str(FONT_PATH), badge_font_size),
        title_pad_x=round(title_font_size * 0.6),
        title_pad_y=round(title_font_size * 0.4),
        badge_pad_x=round(badge_font_size * 1.3),
        badge_pad_y=round(badge_font_size * 1.0),
        swatch_size=round(badge_font_size * 0.65),
        swatch_gap=round(badge_font_size * 0.5),
    )


def _draw_pixel_badge(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    *,
    border_width: int,
    pad_x: int,
    pad_y: int,
    anchor: str,
    swatch_color: tuple[int, int, int] | None = None,
    swatch_size: int = 0,
    swatch_gap: int = 0,
) -> tuple[int, int]:
    """Draws one white-fill/black-border badge (mirrors .brand-label /
    .pixel-btn), optionally preceded by a solid color swatch (mirrors
    .emotion-swatch). `xy` is the box's top-left corner if anchor is
    "top-left", or the (x, bottom-y) point it hangs from if anchor is
    "bottom-left". Returns the badge's rendered (width, height), so
    callers can place further badges beside or above this one.
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    swatch_span = (swatch_size + swatch_gap) if swatch_color else 0
    box_w = text_w + swatch_span + pad_x * 2
    box_h = text_h + pad_y * 2

    x, y = xy
    if anchor == "bottom-left":
        y = y - box_h

    draw.rectangle([x, y, x + box_w, y + box_h], fill=WHITE, outline=BLACK, width=border_width)

    inner_x = x + pad_x
    inner_y = y + pad_y - bbox[1]

    if swatch_color:
        swatch_y = y + (box_h - swatch_size) // 2
        draw.rectangle(
            [inner_x, swatch_y, inner_x + swatch_size, swatch_y + swatch_size],
            fill=swatch_color,
            outline=BLACK,
            width=max(1, border_width - 1),
        )
        inner_x += swatch_span

    draw.text((inner_x, inner_y), text, font=font, fill=BLACK)

    return box_w, box_h


def _draw_date_and_emotion_badges(
    draw: ImageDraw.ImageDraw,
    layout: _BadgeLayout,
    bottom_y: int,
    date_str: str,
    emotion: str,
    emotion_color: str,
) -> None:
    """Date badge then emotion badge (with its color swatch), side by
    side, both bottom-anchored at `bottom_y`. Shared by both card
    renderers.
    """
    date_label = dt.datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d").upper()
    emotion_label = emotion.upper()

    date_w, _ = _draw_pixel_badge(
        draw,
        (layout.margin, bottom_y),
        date_label,
        layout.badge_font,
        border_width=layout.border_width,
        pad_x=layout.badge_pad_x,
        pad_y=layout.badge_pad_y,
        anchor="bottom-left",
    )
    _draw_pixel_badge(
        draw,
        (layout.margin + date_w + layout.badge_gap, bottom_y),
        emotion_label,
        layout.badge_font,
        border_width=layout.border_width,
        pad_x=layout.badge_pad_x,
        pad_y=layout.badge_pad_y,
        anchor="bottom-left",
        swatch_color=_hex_to_rgb(emotion_color),
        swatch_size=layout.swatch_size,
        swatch_gap=layout.swatch_gap,
    )


def render_share_card(
    final_image: Image.Image,
    date_str: str,
    emotion: str,
    emotion_color: str,
    config: dict,
) -> Image.Image:
    """Returns a size x size RGB share card built from final_image, with
    badges overlaid directly on the (already square) resized image.
    """
    size = config["share_card"]["size"]
    card = final_image.resize((size, size), resample=Image.NEAREST).convert("RGB")
    draw = ImageDraw.Draw(card)
    layout = _badge_layout(size)

    _draw_pixel_badge(
        draw,
        (layout.margin, layout.margin),
        "EMO",
        layout.title_font,
        border_width=layout.border_width,
        pad_x=layout.title_pad_x,
        pad_y=layout.title_pad_y,
        anchor="top-left",
    )
    _draw_date_and_emotion_badges(draw, layout, size - layout.margin, date_str, emotion, emotion_color)

    return card


def render_instagram_card(
    final_image: Image.Image,
    date_str: str,
    emotion: str,
    emotion_color: str,
) -> Image.Image:
    """Returns a fixed 1080x1350 (4:5) RGB card for Instagram's feed
    format -- dimensions are an Instagram platform constraint, not a
    site-visual choice, so unlike render_share_card this isn't sized
    off config.

    Unlike render_share_card, the badges aren't overlaid on the image --
    final_image is square but the 4:5 frame is taller, so that extra
    height becomes plain white margin above and below the image, and
    the badges live there instead of on top of the artwork.
    """
    width, height = INSTAGRAM_CARD_WIDTH, INSTAGRAM_CARD_HEIGHT
    card = Image.new("RGB", (width, height), color=WHITE)
    draw = ImageDraw.Draw(card)
    layout = _badge_layout(width)

    image_size = width  # final_image is already square; full width, no crop
    top_band = (height - image_size) // 2
    bottom_band = height - image_size - top_band

    resized = final_image.resize((image_size, image_size), resample=Image.NEAREST)
    card.paste(resized, (0, top_band))

    # EMO badge, vertically centered in the white margin above the image.
    title_bbox = draw.textbbox((0, 0), "EMO", font=layout.title_font)
    title_box_h = (title_bbox[3] - title_bbox[1]) + layout.title_pad_y * 2
    title_y = (top_band - title_box_h) // 2
    _draw_pixel_badge(
        draw,
        (layout.margin, title_y),
        "EMO",
        layout.title_font,
        border_width=layout.border_width,
        pad_x=layout.title_pad_x,
        pad_y=layout.title_pad_y,
        anchor="top-left",
    )

    # Date + emotion badges, side by side, vertically centered in the
    # white margin below the image.
    date_label = dt.datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d").upper()
    badge_bbox = draw.textbbox((0, 0), date_label, font=layout.badge_font)
    badge_box_h = (badge_bbox[3] - badge_bbox[1]) + layout.badge_pad_y * 2
    band_top = height - bottom_band
    bottom_y = band_top + (bottom_band - badge_box_h) // 2 + badge_box_h

    _draw_date_and_emotion_badges(draw, layout, bottom_y, date_str, emotion, emotion_color)

    return card
