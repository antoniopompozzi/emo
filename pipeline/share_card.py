"""Renders EMO's square share card: the day's final.png with pixel-art
badges (EMO brand, date, emotion) baked directly into the pixels.

This exists because the site's real badges are HTML/CSS overlaid on
top of <img class="hero-image">, which only exist inside the page --
anything shared outside it (a downloaded PNG, a social preview
scraping og:image) needs those badges burned into the image itself.

final_image is already square, so it's a direct resize (Image.NEAREST,
to keep the pixel blocks crisp) with no cropping. All badge
measurements below are expressed as fractions of `size` rather than
fixed px, and their ratios to each other mirror .brand-label /
.pixel-btn / .emotion-swatch in style.css, so the card keeps the same
proportions regardless of share_card.size in config.yaml.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

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
) -> int:
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


def render_share_card(
    final_image: Image.Image,
    date_str: str,
    emotion: str,
    emotion_color: str,
    config: dict,
) -> Image.Image:
    """Returns a size x size RGB share card built from final_image."""
    size = config["share_card"]["size"]
    card = final_image.resize((size, size), resample=Image.NEAREST).convert("RGB")
    draw = ImageDraw.Draw(card)

    border_width = max(2, round(size / 400))  # ~2-3px at the default 1080 size
    margin = round(size * 0.045)
    badge_gap = round(size * 0.02)

    title_font_size = round(size * 0.035)
    badge_font_size = round(size * 0.02)
    title_font = ImageFont.truetype(str(FONT_PATH), title_font_size)
    badge_font = ImageFont.truetype(str(FONT_PATH), badge_font_size)

    # Padding ratios mirror .brand-label (pad 0.6rem/0.9rem over a
    # 1.5rem font) and .pixel-btn (pad 0.65rem/0.85rem over a 0.65rem
    # font) in style.css.
    title_pad_x = round(title_font_size * 0.6)
    title_pad_y = round(title_font_size * 0.4)
    badge_pad_x = round(badge_font_size * 1.3)
    badge_pad_y = round(badge_font_size * 1.0)
    swatch_size = round(badge_font_size * 0.65)
    swatch_gap = round(badge_font_size * 0.5)

    _draw_pixel_badge(
        draw,
        (margin, margin),
        "EMO",
        title_font,
        border_width=border_width,
        pad_x=title_pad_x,
        pad_y=title_pad_y,
        anchor="top-left",
    )

    date_label = dt.datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d").upper()
    emotion_label = emotion.upper()

    bottom_y = size - margin
    date_w, _ = _draw_pixel_badge(
        draw,
        (margin, bottom_y),
        date_label,
        badge_font,
        border_width=border_width,
        pad_x=badge_pad_x,
        pad_y=badge_pad_y,
        anchor="bottom-left",
    )
    _draw_pixel_badge(
        draw,
        (margin + date_w + badge_gap, bottom_y),
        emotion_label,
        badge_font,
        border_width=border_width,
        pad_x=badge_pad_x,
        pad_y=badge_pad_y,
        anchor="bottom-left",
        swatch_color=_hex_to_rgb(emotion_color),
        swatch_size=swatch_size,
        swatch_gap=swatch_gap,
    )

    return card


def render_instagram_card(
    final_image: Image.Image,
    date_str: str,
    emotion: str,
    emotion_color: str,
    config: dict,
) -> Image.Image:
    """Returns a 1080x1350 (4:5) RGB card for Instagram's feed format.

    Unlike render_share_card, the badges aren't overlaid on the image --
    final_image is square but the 4:5 frame is taller, so that extra
    height becomes plain white margin above and below the image, and
    the badges live there instead of on top of the artwork.
    """
    width, height = INSTAGRAM_CARD_WIDTH, INSTAGRAM_CARD_HEIGHT
    card = Image.new("RGB", (width, height), color=WHITE)
    draw = ImageDraw.Draw(card)

    image_size = width  # final_image is already square; full width, no crop
    top_band = (height - image_size) // 2
    bottom_band = height - image_size - top_band

    resized = final_image.resize((image_size, image_size), resample=Image.NEAREST)
    card.paste(resized, (0, top_band))

    border_width = max(2, round(width / 400))
    margin = round(width * 0.045)
    badge_gap = round(width * 0.02)

    title_font_size = round(width * 0.035)
    badge_font_size = round(width * 0.02)
    title_font = ImageFont.truetype(str(FONT_PATH), title_font_size)
    badge_font = ImageFont.truetype(str(FONT_PATH), badge_font_size)

    title_pad_x = round(title_font_size * 0.6)
    title_pad_y = round(title_font_size * 0.4)
    badge_pad_x = round(badge_font_size * 1.3)
    badge_pad_y = round(badge_font_size * 1.0)
    swatch_size = round(badge_font_size * 0.65)
    swatch_gap = round(badge_font_size * 0.5)

    # EMO badge, vertically centered in the white margin above the image.
    title_bbox = draw.textbbox((0, 0), "EMO", font=title_font)
    title_box_h = (title_bbox[3] - title_bbox[1]) + title_pad_y * 2
    title_y = (top_band - title_box_h) // 2
    _draw_pixel_badge(
        draw,
        (margin, title_y),
        "EMO",
        title_font,
        border_width=border_width,
        pad_x=title_pad_x,
        pad_y=title_pad_y,
        anchor="top-left",
    )

    # Date + emotion badges, side by side, vertically centered in the
    # white margin below the image.
    date_label = dt.datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d").upper()
    emotion_label = emotion.upper()

    badge_bbox = draw.textbbox((0, 0), date_label, font=badge_font)
    badge_box_h = (badge_bbox[3] - badge_bbox[1]) + badge_pad_y * 2
    band_top = height - bottom_band
    bottom_y = band_top + (bottom_band - badge_box_h) // 2 + badge_box_h

    date_w, _ = _draw_pixel_badge(
        draw,
        (margin, bottom_y),
        date_label,
        badge_font,
        border_width=border_width,
        pad_x=badge_pad_x,
        pad_y=badge_pad_y,
        anchor="bottom-left",
    )
    _draw_pixel_badge(
        draw,
        (margin + date_w + badge_gap, bottom_y),
        emotion_label,
        badge_font,
        border_width=border_width,
        pad_x=badge_pad_x,
        pad_y=badge_pad_y,
        anchor="bottom-left",
        swatch_color=_hex_to_rgb(emotion_color),
        swatch_size=swatch_size,
        swatch_gap=swatch_gap,
    )

    return card
