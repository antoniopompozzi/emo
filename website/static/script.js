// Shared by every <dialog> on the page: clicking the backdrop (outside
// the dialog's own box) closes it, same as clicking outside a native
// <select> or similar. ESC-to-close and the backdrop itself come free
// from showModal(); this is just the "click outside" part.
function closeOnBackdropClick(dialog) {
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

// The "Why this image?" modal, on every hero page.
function initWhyModal() {
  const dialog = document.getElementById("why-modal");
  const openBtn = document.getElementById("why-btn");
  const closeBtn = document.getElementById("why-close");
  if (!dialog || !openBtn || !closeBtn) return;

  openBtn.addEventListener("click", () => dialog.showModal());
  closeBtn.addEventListener("click", () => dialog.close());
  closeOnBackdropClick(dialog);
}

// The AI-disclosure modal, opened from the small "AI-generated ·
// updated daily" label on every hero page.
function initAiDisclosureModal() {
  const dialog = document.getElementById("ai-disclosure-modal");
  const openBtn = document.getElementById("ai-disclosure-btn");
  const closeBtn = document.getElementById("ai-disclosure-close");
  if (!dialog || !openBtn || !closeBtn) return;

  openBtn.addEventListener("click", () => dialog.showModal());
  closeBtn.addEventListener("click", () => dialog.close());
  closeOnBackdropClick(dialog);
}

// The SHARE modal: card preview, download link, copy-link button.
// Deliberately not using the native Web Share API -- its picker varies
// unpredictably across browsers (a full app list on Windows/Edge,
// inconsistent behavior on Firefox), so one consistent modal beats a
// native/fallback split.
function initShareButton() {
  const modal = document.getElementById("share-modal");
  const openBtn = document.getElementById("share-btn");
  if (!modal || !openBtn) return;

  const closeBtn = document.getElementById("share-modal-close");
  const preview = document.getElementById("share-preview");
  const downloadLink = document.getElementById("share-download");
  const copyBtn = document.getElementById("share-copy-link");

  closeBtn.addEventListener("click", () => modal.close());
  closeOnBackdropClick(modal);

  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      const original = copyBtn.textContent;
      copyBtn.textContent = "COPIED!";
      setTimeout(() => {
        copyBtn.textContent = original;
      }, 1500);
    } catch (error) {
      // Clipboard access denied or unavailable -- the link is still
      // visible in the address bar, so there's nothing more to do.
    }
  });

  openBtn.addEventListener("click", () => {
    preview.src = openBtn.dataset.shareImage;
    downloadLink.href = openBtn.dataset.shareImage;
    modal.showModal();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initWhyModal();
  initAiDisclosureModal();
  initShareButton();
});
