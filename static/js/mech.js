/* Mechanism interactions — progressive enhancement, no dependencies.
   Everything degrades: without JS the cards show their full spec sheet and
   still link to the deep dive; this layer adds the unscrew-to-reveal toy and
   a cursor-tracked specular highlight. All motion respects the user's
   reduced-motion preference; parallax runs only on fine pointers. */
(function () {
  "use strict";
  var root = document.body;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = window.matchMedia("(pointer: fine)").matches;

  root.classList.add("js");
  if (fine) root.classList.add("fine");

  /* ---- #1 unscrew-to-reveal ---- */
  var cards = document.querySelectorAll(".mech-card");
  Array.prototype.forEach.call(cards, function (card) {
    var bolt = card.querySelector(".fastener");
    var sheet = card.querySelector(".spec-sheet");
    if (!bolt || !sheet) return;

    // Turn the decorative fastener into a real control.
    bolt.removeAttribute("aria-hidden");
    bolt.setAttribute("role", "button");
    bolt.setAttribute("tabindex", "0");
    bolt.setAttribute("aria-expanded", "false");
    if (sheet.id) bolt.setAttribute("aria-controls", sheet.id);
    var title = card.querySelector("h3");
    bolt.setAttribute(
      "aria-label",
      "Unscrew to reveal the spec sheet" + (title ? " for " + title.textContent : "")
    );

    function toggle() {
      var open = card.classList.toggle("is-open");
      bolt.setAttribute("aria-expanded", open ? "true" : "false");
    }
    bolt.addEventListener("click", toggle);
    bolt.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
        e.preventDefault();
        toggle();
      }
    });
  });

  /* ---- #2 specular parallax (fine pointers, motion allowed) ---- */
  if (fine && !reduce) {
    var bodies = document.querySelectorAll(".mech-card-body");
    Array.prototype.forEach.call(bodies, function (el) {
      var ticking = false;
      el.addEventListener("pointermove", function (e) {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(function () {
          ticking = false;
          var r = el.getBoundingClientRect();
          el.style.setProperty("--mx", ((e.clientX - r.left) / r.width) * 100 + "%");
          el.style.setProperty("--my", ((e.clientY - r.top) / r.height) * 100 + "%");
        });
      });
      el.addEventListener("pointerleave", function () {
        el.style.removeProperty("--mx");
        el.style.removeProperty("--my");
      });
    });
  }
})();
