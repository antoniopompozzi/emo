// The "Why this image?" modal, on every hero page. Uses the native
// <dialog> element so focus handling, ESC-to-close and the backdrop
// come for free from the browser.
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

// "Magnetic" hover effect for the WHY THIS IMAGE? / ARCHIVE buttons: the
// button nudges toward the cursor while the mouse is over it, and eases
// back to center on mouseleave. Only on devices with a real mouse -- on
// touch there's no hover state to drive this from, so it's skipped
// entirely rather than firing on tap. The EMO brand label intentionally
// isn't included here: it should stay fixed.
function initMagneticButtons() {
  if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

  const PULL_FRACTION = 0.375; // how much of the cursor's offset from center to follow
  const MAX_OFFSET_PX = 12; // clamp so the effect stays subtle, not a jump

  document.querySelectorAll(".hero-actions .pixel-btn").forEach((btn) => {
    btn.addEventListener("mousemove", (event) => {
      const rect = btn.getBoundingClientRect();
      const offsetX = event.clientX - (rect.left + rect.width / 2);
      const offsetY = event.clientY - (rect.top + rect.height / 2);
      const x = Math.max(-MAX_OFFSET_PX, Math.min(MAX_OFFSET_PX, offsetX * PULL_FRACTION));
      const y = Math.max(-MAX_OFFSET_PX, Math.min(MAX_OFFSET_PX, offsetY * PULL_FRACTION));
      btn.style.transition = "transform 0s";
      btn.style.transform = `translate(${x}px, ${y}px)`;
    });

    btn.addEventListener("mouseleave", () => {
      btn.style.transition = "transform 0.3s ease-out";
      btn.style.transform = "translate(0, 0)";
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initWhyModal();
  initMagneticButtons();
});
