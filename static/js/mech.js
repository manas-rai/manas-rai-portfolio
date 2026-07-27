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

  /* ---- #3 architecture diagrams draw themselves on first view ----
     The SVGs are inlined at build time so their stages and arrows are real
     elements (services/diagrams.py). All this does is stamp a stagger index in
     document order and flip a class when the figure scrolls into view — the
     animation itself is CSS. Play-once, not scroll-scrubbed: a diagram that
     un-draws when you scroll back up is a distraction, not a feature. */
  var figures = document.querySelectorAll(".diagram.is-live");
  if (figures.length) {
    Array.prototype.forEach.call(figures, function (figure) {
      // Stages first, then the arrows between them, so the pipeline resolves
      // in the order a reader would trace it.
      var stages = figure.querySelectorAll("svg [class]:not([data-draw])");
      var edges = figure.querySelectorAll("svg [data-draw]");
      var step = 0;
      Array.prototype.forEach.call(stages, function (el) {
        el.style.setProperty("--i", step++);
      });
      Array.prototype.forEach.call(edges, function (el) {
        el.style.setProperty("--i", step++);
      });
    });

    if (!("IntersectionObserver" in window) || reduce) {
      Array.prototype.forEach.call(figures, function (f) {
        f.classList.add("is-revealed");
      });
    } else {
      var seen = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            entry.target.classList.add("is-revealed");
            seen.unobserve(entry.target); // once is enough
          });
        },
        { threshold: 0.2, rootMargin: "0px 0px -8% 0px" }
      );
      Array.prototype.forEach.call(figures, function (f) {
        seen.observe(f);
      });
    }
  }

  /* ---- #4 ⌘K system console ----
     Every panel is already in the DOM; this only toggles visibility, so the
     content is there for search engines and for no-JS visitors (who get to the
     same material through the normal nav). The trigger ships hidden and is
     revealed here — advertising a shortcut that can't fire is worse than
     staying quiet about it. */
  var consoleEl = document.getElementById("console");
  var openBtn = document.getElementById("console-open");

  if (consoleEl && openBtn) {
    var panels = consoleEl.querySelectorAll(".console-panel");
    var cmds = consoleEl.querySelectorAll(".console-cmd");
    var lastFocused = null;
    openBtn.hidden = false;

    var FOCUSABLE =
      'a[href], button:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

    function selectCmd(name) {
      Array.prototype.forEach.call(cmds, function (btn) {
        var on = btn.getAttribute("data-cmd") === name;
        btn.classList.toggle("is-active", on);
        btn.setAttribute("aria-selected", on ? "true" : "false");
      });
      Array.prototype.forEach.call(panels, function (panel) {
        panel.hidden = panel.getAttribute("data-panel") !== name;
      });
    }

    function openConsole(cmd) {
      lastFocused = document.activeElement;
      consoleEl.hidden = false;
      openBtn.setAttribute("aria-expanded", "true");
      // Stop the page scrolling behind the dialog.
      root.style.overflow = "hidden";
      if (cmd) selectCmd(cmd);
      var first = consoleEl.querySelector(".console-cmd");
      if (first) first.focus();
    }

    function closeConsole() {
      consoleEl.hidden = true;
      openBtn.setAttribute("aria-expanded", "false");
      root.style.removeProperty("overflow");
      // Send focus back where it came from, not to the top of the document.
      if (lastFocused && lastFocused.focus) lastFocused.focus();
      lastFocused = null;
    }

    openBtn.addEventListener("click", function () {
      openConsole();
    });

    Array.prototype.forEach.call(
      consoleEl.querySelectorAll("[data-console-close]"),
      function (el) {
        el.addEventListener("click", closeConsole);
      }
    );

    Array.prototype.forEach.call(cmds, function (btn) {
      btn.addEventListener("click", function () {
        selectCmd(btn.getAttribute("data-cmd"));
      });
    });

    document.addEventListener("keydown", function (e) {
      var isOpen = !consoleEl.hidden;

      if (isOpen && e.key === "Escape") {
        e.preventDefault();
        closeConsole();
        return;
      }

      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        // Don't steal the shortcut from a field the visitor is typing in.
        var el = document.activeElement;
        var tag = el ? el.tagName : "";
        if (tag === "INPUT" || tag === "TEXTAREA" || (el && el.isContentEditable)) return;
        e.preventDefault(); // browsers bind ⌘K to the address/search bar
        if (isOpen) closeConsole();
        else openConsole();
        return;
      }

      // Keep Tab inside the dialog while it owns the screen.
      if (isOpen && e.key === "Tab") {
        var items = consoleEl.querySelectorAll(FOCUSABLE);
        if (!items.length) return;
        var first = items[0];
        var last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    });
  }

})();
