"""EMO's fixed visual signature: turns any source image into a
grayscale, pixelated, tonally-quantized block image.

This module is deliberately simple and untouched by the daily AI
calls -- it is the one part of the pipeline meant to produce visually
consistent output every single day, whatever Claude and Pollinations
produced upstream.

Steps: grayscale -> box-filter downsample to a grid -> quantize gray
levels -> render each cell as a hard-edged solid block.
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def pixelate(source: Image.Image, grid_size: int, gray_levels: int, px_per_cell: int) -> Image.Image:
    grayscale = source.convert("L")

    # Box filter: PIL's BOX resample averages all source pixels that
    # fall into each destination pixel, i.e. one mean per grid cell.
    small = grayscale.resize((grid_size, grid_size), resample=Image.BOX)

    values = np.array(small, dtype=np.float64)
    bucket = np.clip(np.floor(values / 256.0 * gray_levels), 0, gray_levels - 1)
    quantized = (bucket * (255.0 / (gray_levels - 1))).round().astype(np.uint8)

    grid_image = Image.fromarray(quantized, mode="L")

    final_size = grid_size * px_per_cell
    # Nearest-neighbour upscale turns each cell into a hard-edged solid
    # block, with no antialiasing at cell boundaries.
    final_image = grid_image.resize((final_size, final_size), resample=Image.NEAREST)
    return final_image.convert("L")
