"""EMO's fixed visual signature: turns any source image into a
grayscale, pixelated, tonally-quantized block image.

This module is deliberately simple and untouched by the daily AI
calls -- it is the one part of the pipeline meant to produce visually
consistent output every single day, whatever Claude and the image
provider produced upstream.

Steps: grayscale -> box-filter downsample to a grid -> quantize gray
levels -> render each cell as a hard-edged solid block.

`quantize_grid` and `render_grid` are split apart (rather than one
`pixelate` function) because the site also needs the raw quantized
values, not just the rendered PNG: the homepage draws its own grid on
a <canvas> so it can size cells to fit any screen without cropping or
upscaling final.png (see archive.py and website/static/script.js).
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def quantize_grid(source: Image.Image, grid_size: int, gray_levels: int) -> np.ndarray:
    """Returns a grid_size x grid_size array of quantized gray values (0-255)."""
    grayscale = source.convert("L")

    # Box filter: PIL's BOX resample averages all source pixels that
    # fall into each destination pixel, i.e. one mean per grid cell.
    small = grayscale.resize((grid_size, grid_size), resample=Image.BOX)

    values = np.array(small, dtype=np.float64)
    bucket = np.clip(np.floor(values / 256.0 * gray_levels), 0, gray_levels - 1)
    return (bucket * (255.0 / (gray_levels - 1))).round().astype(np.uint8)


def render_grid(grid: np.ndarray, px_per_cell: int) -> Image.Image:
    """Renders a quantized grid as hard-edged solid blocks, px_per_cell pixels each."""
    grid_image = Image.fromarray(grid, mode="L")
    final_size = grid.shape[0] * px_per_cell
    # Nearest-neighbour upscale turns each cell into a hard-edged solid
    # block, with no antialiasing at cell boundaries.
    final_image = grid_image.resize((final_size, final_size), resample=Image.NEAREST)
    return final_image.convert("L")


def pixelate(source: Image.Image, grid_size: int, gray_levels: int, px_per_cell: int) -> Image.Image:
    """Convenience wrapper: source image -> final rendered PNG in one call."""
    return render_grid(quantize_grid(source, grid_size, gray_levels), px_per_cell)
