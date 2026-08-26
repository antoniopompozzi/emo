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

// The ORACLE modal, on every hero page: same open/close pattern as
// initWhyModal, just a second static dialog showing the most recent
// ORACLE week instead of a separate /oracle/ page.
function initOracleModal() {
  const dialog = document.getElementById("oracle-modal");
  const openBtn = document.getElementById("oracle-btn");
  const closeBtn = document.getElementById("oracle-modal-close");
  if (!dialog || !openBtn || !closeBtn) return;

  openBtn.addEventListener("click", () => dialog.showModal());
  closeBtn.addEventListener("click", () => dialog.close());
  closeOnBackdropClick(dialog);
}

// The SHARE modal: one shared dialog (card preview + download link +
// copy-link button), opened by any number of trigger buttons on the
// page (the page's own SHARE button, "SHARE THIS ORACLE" inside the
// ORACLE modal, "SHARE THIS ORACLE" inside the ORACLE archive modal --
// see initOracleArchiveModal). Each trigger carries its own
// data-share-image/data-share-filename, read fresh at click time, so
// the same modal always shows whichever card was actually clicked.
// Deliberately not using the native Web Share API -- its picker varies
// unpredictably across browsers (a full app list on Windows/Edge,
// inconsistent behavior on Firefox), so one consistent modal beats a
// native/fallback split.
function initShareButton() {
  const modal = document.getElementById("share-modal");
  const triggers = document.querySelectorAll(".share-trigger");
  if (!modal || triggers.length === 0) return;

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

  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      preview.src = trigger.dataset.shareImage;
      downloadLink.href = trigger.dataset.shareImage;
      downloadLink.download = trigger.dataset.shareFilename;
      modal.showModal();
    });
  });
}

// The ORACLE archive's dynamic modal, on archive.html: every
// .oracle-archive-item button carries that week's data as data-oracle-*
// attributes (see archive.html). Clicking one populates
// #oracle-archive-modal from those attributes -- image, date range,
// verdict + swatch, explanation -- and rewrites the dataset on its own
// "SHARE THIS ORACLE" button (already wired up generically by
// initShareButton, since it also has the .share-trigger class) before
// opening the dialog, so sharing always matches whichever week was
// just clicked without any dedicated share logic here.
function initOracleArchiveModal() {
  const dialog = document.getElementById("oracle-archive-modal");
  const items = document.querySelectorAll(".oracle-archive-item");
  if (!dialog || items.length === 0) return;

  const closeBtn = document.getElementById("oracle-archive-modal-close");
  const rangeEl = document.getElementById("oracle-archive-modal-range");
  const verdictSwatch = document.getElementById("oracle-archive-modal-verdict-swatch");
  const verdictText = document.getElementById("oracle-archive-modal-verdict-text");
  const image = document.getElementById("oracle-archive-modal-image");
  const explanation = document.getElementById("oracle-archive-modal-explanation");
  const shareBtn = document.getElementById("oracle-archive-modal-share-btn");

  closeBtn.addEventListener("click", () => dialog.close());
  closeOnBackdropClick(dialog);

  items.forEach((item) => {
    item.addEventListener("click", () => {
      const data = item.dataset;
      rangeEl.textContent = data.oracleRange;
      verdictSwatch.style.background = data.oracleVerdictColor;
      verdictText.textContent = data.oracleVerdict;
      image.src = data.oracleImage;
      image.alt = `ORACLE's verdict image for the week ${data.oracleRange}`;
      explanation.textContent = data.oracleExplanation;
      shareBtn.dataset.shareImage = data.oracleShareImage;
      shareBtn.dataset.shareFilename = data.oracleShareFilename;
      dialog.showModal();
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initWhyModal();
  initOracleModal();
  initShareButton();
  initOracleArchiveModal();
});
