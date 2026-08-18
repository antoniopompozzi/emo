// Opens/closes the "Why this image?" modal. Uses the native <dialog>
// element so focus handling, ESC-to-close and the backdrop come for
// free from the browser.
document.addEventListener("DOMContentLoaded", () => {
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
});
