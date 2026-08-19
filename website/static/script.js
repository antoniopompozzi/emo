// Two independent pieces of page behaviour:
//
// 1. The homepage's pixel grid: drawn on a <canvas> from grid_values.json
//    rather than shown as a plain <img>, so it can be sized to fit any
//    screen (phone or desktop, portrait or landscape) without cropping
//    or blowing up the square source image.
// 2. The "Why this image?" modal, on every hero page. Uses the native
//    <dialog> element so focus handling, ESC-to-close and the backdrop
//    come for free from the browser.

// The grid is always square (see pipeline/postprocess.py). Art cells
// (one per value in grid_values.json) are capped at this size so the
// image stays a dense mosaic on large screens; on small screens they
// shrink further so the whole grid still fits without being cropped.
const MAX_ART_CELL_SIZE = 14;

// Each art cell is itself subdivided into FINE_CELLS_PER_ART_CELL x
// FINE_CELLS_PER_ART_CELL background grid squares, all filled with the
// art cell's own colour -- this is what gives the fine graph-paper
// texture from the EMO mockup instead of a coarse blocky grid, while
// the actual image detail (one colour per art cell) is unchanged.
const FINE_CELLS_PER_ART_CELL = 4;
// Below this, subdividing further would make the fine lines themselves
// the dominant visual (near-solid grey) rather than a texture -- so on
// very small screens we fall back to drawing lines only at art-cell
// boundaries instead of subdividing.
const MIN_FINE_CELL_SIZE = 3;
const GRID_LINE_COLOR = "#cccccc";

function artCellSizeFor(gridSize, viewportWidth, viewportHeight) {
  const maxFit = Math.floor(Math.min(viewportWidth, viewportHeight) / gridSize);
  return Math.max(1, Math.min(MAX_ART_CELL_SIZE, maxFit));
}

function drawGrid(canvas, values) {
  const gridSize = values.length;
  const artCellSize = artCellSizeFor(gridSize, window.innerWidth, window.innerHeight);
  const pixelSize = artCellSize * gridSize;
  const dpr = window.devicePixelRatio || 1;

  canvas.width = pixelSize * dpr;
  canvas.height = pixelSize * dpr;
  canvas.style.width = `${pixelSize}px`;
  canvas.style.height = `${pixelSize}px`;

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.imageSmoothingEnabled = false;

  for (let row = 0; row < gridSize; row++) {
    for (let col = 0; col < gridSize; col++) {
      const gray = values[row][col];
      ctx.fillStyle = `rgb(${gray}, ${gray}, ${gray})`;
      ctx.fillRect(col * artCellSize, row * artCellSize, artCellSize, artCellSize);
    }
  }

  // Fine grid lines, subdividing each art cell into a dense mosaic of
  // background squares -- like graph paper -- rather than one line per
  // (large) art cell.
  const fineCellSize = artCellSize / FINE_CELLS_PER_ART_CELL;
  const subdivide = fineCellSize >= MIN_FINE_CELL_SIZE;
  const lineSpacing = subdivide ? fineCellSize : artCellSize;
  const lineCount = subdivide ? gridSize * FINE_CELLS_PER_ART_CELL : gridSize;

  ctx.strokeStyle = GRID_LINE_COLOR;
  ctx.lineWidth = 1;
  for (let i = 0; i <= lineCount; i++) {
    const pos = Math.round(i * lineSpacing) + 0.5; // +0.5 keeps 1px lines crisp, not antialiased
    ctx.beginPath();
    ctx.moveTo(pos, 0);
    ctx.lineTo(pos, pixelSize);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, pos);
    ctx.lineTo(pixelSize, pos);
    ctx.stroke();
  }
}

function fallBackToPlainImage(canvas) {
  // grid_values.json is missing or invalid (e.g. an older archive entry
  // written before this file existed) -- fall back to the plain
  // pixelated PNG so the page still shows something.
  const img = document.createElement("img");
  img.className = "hero-image";
  img.src = canvas.dataset.imageUrl;
  img.alt = canvas.getAttribute("aria-label") || "";
  canvas.replaceWith(img);
}

async function initHeroCanvas() {
  const canvas = document.getElementById("hero-canvas");
  if (!canvas) return;

  try {
    const response = await fetch(canvas.dataset.gridUrl);
    if (!response.ok) throw new Error(`grid fetch failed: ${response.status}`);
    const { values } = await response.json();

    const redraw = () => drawGrid(canvas, values);
    redraw();

    let resizeTimer;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(redraw, 150);
    });
  } catch (err) {
    fallBackToPlainImage(canvas);
  }
}

function initWhyModal() {
  const dialog = document.getElementById("why-modal");
  const openBtn = document.getElementById("why-btn");
  const closeBtn = document.getElementById("why-close");
  if (!dialog || !openBtn || !closeBtn) return;

  openBtn.addEventListener("click", () => dialog.showModal());
  closeBtn.addEventListener("click", () => dialog.close());

  // Clicking the backdrop (outside the dialog's own box) closes it.
  dialog.addEventListener("click", (event) => {
    const rect = dialog.getBoundingClientRect();
    const insideDialog =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom;
    if (!insideDialog) dialog.close();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initHeroCanvas();
  initWhyModal();
});
