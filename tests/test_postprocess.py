import numpy as np
from PIL import Image

from pipeline.postprocess import pixelate, quantize_grid, render_grid

WHITE = "#ffffff"


def test_output_size_matches_grid_times_px_per_cell():
    source = Image.new("RGB", (200, 340), color=(120, 60, 200))
    result = pixelate(source, grid_size=8, gray_levels=4, px_per_cell=5, hue_hex=WHITE)
    assert result.size == (40, 40)


def test_white_hue_reproduces_plain_grayscale():
    # A pure white hue should interpolate every cell between black and
    # white, i.e. R == G == B everywhere -- the old grayscale look,
    # unchanged, just now expressed as an RGB image instead of "L" mode
    # (RGB is required so any other hue can be rendered too).
    source = Image.new("RGB", (64, 64), color=(200, 30, 30))
    result = pixelate(source, grid_size=8, gray_levels=4, px_per_cell=4, hue_hex=WHITE)
    assert result.mode == "RGB"
    arr = np.array(result)
    assert np.array_equal(arr[:, :, 0], arr[:, :, 1])
    assert np.array_equal(arr[:, :, 1], arr[:, :, 2])


def test_solid_color_input_produces_a_single_quantized_value():
    source = Image.new("RGB", (100, 100), color=(128, 128, 128))
    result = pixelate(source, grid_size=4, gray_levels=5, px_per_cell=10, hue_hex=WHITE)
    colors = set(map(tuple, np.array(result).reshape(-1, 3).tolist()))
    assert len(colors) == 1


def test_quantized_output_uses_at_most_the_configured_levels():
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 256, size=(200, 200, 3), dtype=np.uint8)
    source = Image.fromarray(noise, mode="RGB")
    result = pixelate(source, grid_size=32, gray_levels=6, px_per_cell=2, hue_hex="#c0392b")
    distinct_colors = set(map(tuple, np.array(result).reshape(-1, 3).tolist()))
    assert len(distinct_colors) <= 6


def test_cell_edges_are_hard_no_antialiasing():
    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    pixels[:, 50:] = 255  # sharp black/white transition to preserve
    source = Image.fromarray(pixels)
    result = pixelate(source, grid_size=10, gray_levels=2, px_per_cell=10, hue_hex=WHITE)
    arr = np.array(result)
    # Within a single rendered cell (10px here) all pixels must be identical.
    cell = arr[0:10, 0:10]
    assert len(set(map(tuple, cell.reshape(-1, 3).tolist()))) == 1


def test_duotone_interpolates_between_black_and_the_hue_color():
    # Left half black, right half white -> after quantizing to 2 levels,
    # the darkest cell should render as black and the brightest as the
    # hue color itself (fraction 1.0), not white.
    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    pixels[:, 50:] = 255
    source = Image.fromarray(pixels)
    hue = "#c0392b"  # anger
    result = pixelate(source, grid_size=2, gray_levels=2, px_per_cell=10, hue_hex=hue)
    arr = np.array(result)
    dark_cell = tuple(arr[0, 0])
    bright_cell = tuple(arr[0, -1])
    assert dark_cell == (0, 0, 0)
    assert bright_cell == (0xC0, 0x39, 0x2B)


def test_quantize_grid_shape_matches_grid_size():
    source = Image.new("RGB", (300, 150), color=(90, 90, 90))
    grid = quantize_grid(source, grid_size=20, gray_levels=8)
    assert grid.shape == (20, 20)
    assert grid.dtype == np.uint8


def test_render_grid_is_consistent_with_pixelate():
    source = Image.new("RGB", (64, 64), color=(50, 150, 250))
    hue = "#1a9e8f"  # surprise
    grid = quantize_grid(source, grid_size=8, gray_levels=5)
    rendered = render_grid(grid, px_per_cell=6, hue_hex=hue)
    combined = pixelate(source, grid_size=8, gray_levels=5, px_per_cell=6, hue_hex=hue)
    assert np.array_equal(np.array(rendered), np.array(combined))
