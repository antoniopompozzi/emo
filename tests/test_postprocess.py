import numpy as np
from PIL import Image

from pipeline.postprocess import pixelate


def test_output_size_matches_grid_times_px_per_cell():
    source = Image.new("RGB", (200, 340), color=(120, 60, 200))
    result = pixelate(source, grid_size=8, gray_levels=4, px_per_cell=5)
    assert result.size == (40, 40)


def test_output_is_grayscale():
    source = Image.new("RGB", (64, 64), color=(200, 30, 30))
    result = pixelate(source, grid_size=8, gray_levels=4, px_per_cell=4)
    assert result.mode == "L"


def test_solid_color_input_produces_a_single_quantized_value():
    source = Image.new("RGB", (100, 100), color=(128, 128, 128))
    result = pixelate(source, grid_size=4, gray_levels=5, px_per_cell=10)
    values = set(np.array(result).flatten().tolist())
    assert len(values) == 1


def test_quantized_output_uses_at_most_the_configured_levels():
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 256, size=(200, 200, 3), dtype=np.uint8)
    source = Image.fromarray(noise, mode="RGB")
    result = pixelate(source, grid_size=32, gray_levels=6, px_per_cell=2)
    distinct_values = set(np.array(result).flatten().tolist())
    assert len(distinct_values) <= 6


def test_cell_edges_are_hard_no_antialiasing():
    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    pixels[:, 50:] = 255  # sharp black/white transition to preserve
    source = Image.fromarray(pixels)
    result = pixelate(source, grid_size=10, gray_levels=2, px_per_cell=10)
    arr = np.array(result)
    # Within a single rendered cell (10px here) all values must be identical.
    cell = arr[0:10, 0:10]
    assert len(set(cell.flatten().tolist())) == 1
