"""EMO's fixed visual signature: turns any source image into a
duotone (black -> a color), pixelated, tonally-quantized block image.

This module is deliberately simple and untouched by the daily AI
calls -- it is the one part of the pipeline meant to produce visually
consistent output every single day, whatever Claude and the image
provider produced upstream. The one thing that *does* vary day to day
is the duotone's hue, driven by the emotion Claude extracts from the
news (see concept.py and pipeline/emotions.py) -- brightness always
maps the same way, only the target color changes.

Steps: grayscale -> box-filter downsample to a grid -> quantize
brightness levels -> render each cell as a hard-edged solid block,
interpolated between black and the day's emotion color.

`quantize_grid` and `render_grid` are split apart (rather than one
`pixelate` function) because the site also needs the raw quantized
values, not just the rendered PNG: the homepage draws its own grid on
a <canvas> so it can size cells to fit any screen without cropping or
upscaling final.png (see archive.py and website/static/script.js).
`quantize_grid` stays plain brightness (not yet colored) so the exact
same grid can be re-rendered with any hue.
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def quantize_grid(source: Image.Image, grid_size: int, gray_levels: int) -> np.ndarray:
    """Returns a grid_size x grid_size array of quantized brightness values (0-255)."""
    grayscale = source.convert("L")

    # Box filter: PIL's BOX resample averages all source pixels that
    # fall into each destination pixel, i.e. one mean per grid cell.
    small = grayscale.resize((grid_size, grid_size), resample=Image.BOX)

    values = np.array(small, dtype=np.float64)
    bucket = np.clip(np.floor(values / 256.0 * gray_levels), 0, gray_levels - 1)
    return (bucket * (255.0 / (gray_levels - 1))).round().astype(np.uint8)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def render_grid(grid: np.ndarray, px_per_cell: int, hue_hex: str) -> Image.Image:
    """Renders a quantized grid as hard-edged solid blocks, px_per_cell pixels each.

    Each cell's brightness (0-255) interpolates between black (0) and
    `hue_hex` (255) -- a duotone ramp instead of a plain grayscale one.
    A pure white hue would reproduce the old grayscale look exactly,
    but every real caller passes a specific emotion color (see
    pipeline/emotions.py), including "neutral"'s dark gray -- hue_hex
    has no default so callers can't forget to pass one.
    """
    r, g, b = _hex_to_rgb(hue_hex)
    fraction = grid.astype(np.float64) / 255.0
    rgb = np.stack(
        [
            (fraction * r).round().astype(np.uint8),
            (fraction * g).round().astype(np.uint8),
            (fraction * b).round().astype(np.uint8),
        ],
        axis=-1,
    )
    grid_image = Image.fromarray(rgb, mode="RGB")
    final_size = grid.shape[0] * px_per_cell
    # Nearest-neighbour upscale turns each cell into a hard-edged solid
    # block, with no antialiasing at cell boundaries.
    return grid_image.resize((final_size, final_size), resample=Image.NEAREST)


def pixelate(source: Image.Image, grid_size: int, gray_levels: int, px_per_cell: int, hue_hex: str) -> Image.Image:
    """Convenience wrapper: source image -> final rendered duotone PNG in one call."""
    return render_grid(quantize_grid(source, grid_size, gray_levels), px_per_cell, hue_hex)
