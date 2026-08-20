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

// The SHARE button: tries the native Web Share API first, sharing the
// day's share_card.png as an actual file (not just a link) so the
// receiving app gets the image directly. Falls back to a plain modal
// (card preview + download link + copy-link button) when the browser
// can't share files, doesn't have the API at all, or the share attempt
// fails for a real reason -- but not when the user simply cancelled
// the native share sheet (AbortError), where doing nothing is correct.
function initShareButton() {
  const shareBtn = document.getElementById("share-btn");
  const modal = document.getElementById("share-modal");
  if (!shareBtn || !modal) return;

  const closeBtn = document.getElementById("share-modal-close");
  const preview = document.getElementById("share-preview");
  const downloadLink = document.getElementById("share-download");
  const copyBtn = document.getElementById("share-copy-link");

  closeBtn.addEventListener("click", () => modal.close());
  closeOnBackdropClick(modal);

  function openFallbackModal(imageUrl) {
    preview.src = imageUrl;
    downloadLink.href = imageUrl;
    modal.showModal();
  }

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

  shareBtn.addEventListener("click", async () => {
    const imageUrl = shareBtn.dataset.shareImage;

    if (navigator.share) {
      try {
        const response = await fetch(imageUrl);
        const blob = await response.blob();
        const file = new File([blob], "emo-share.png", { type: blob.type || "image/png" });

        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          await navigator.share({
            files: [file],
            title: "EMO",
            text: "EMO -- a daily pixelated duotone generated from the day's news",
            url: window.location.href,
          });
          return;
        }
      } catch (error) {
        if (error && error.name === "AbortError") return;
        // Any other failure (fetch, canShare, share itself) falls
        // through to the fallback modal below.
      }
    }

    openFallbackModal(imageUrl);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initWhyModal();
  initShareButton();
});
