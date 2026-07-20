// Progressive enhancement for the contact form. Without JS the form posts
// normally and the Function redirects to /contact/sent/; with JS we submit
// via fetch and show the outcome inline.
(function () {
  const form = document.querySelector(".contact-form");
  if (!form) return;

  const status = document.getElementById("contact-status");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    status.hidden = true;

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: new FormData(form),
      });
      const data = await response.json().catch(() => ({}));

      if (response.ok && data.ok) {
        const done = document.createElement("p");
        done.className = "flash flash-success";
        done.textContent = "Thanks — your message is on its way. I'll be in touch.";
        form.replaceWith(done);
        return;
      }

      status.textContent = data.errors
        ? Object.values(data.errors).join(" ")
        : data.error || form.dataset.fallback;
    } catch {
      status.textContent = form.dataset.fallback;
    } finally {
      status.hidden = !status.textContent;
      button.disabled = false;
    }
  });
})();
