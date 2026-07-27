"""Inline architecture SVGs so their internals can be animated.

An `<img src="...svg">` is an opaque box — the nodes and flow arrows inside it
can't be styled or animated from the page. Inlining the markup fixes that, but
brings two problems this module solves at build time:

1. Each SVG carries its own `<style>` block. Inlined, that becomes an inline
   stylesheet, which `style-src 'self'` blocks — the diagram would render
   unstyled. The rules are lifted out, scoped to the diagram, and written to a
   real stylesheet instead.
2. Every SVG defines the same `accent` / `arrow` ids. One diagram per page makes
   that harmless today, but ids are namespaced anyway so two can coexist.

Flow arrows are marked `data-draw` so CSS can stroke-dash them into existence.
Already-dashed strokes are skipped: overriding their dasharray would destroy the
dashes that carry meaning (async hops, sync links).
"""

from __future__ import annotations

import re
from pathlib import Path

from app.services.content_loader import ContentError

# Shapes that read as "a stage in the pipeline" — these fade in one after another.
NODE_CLASSES = ("node", "agent", "pill")
# Strokes that read as "flow between stages" — candidates for the draw-on effect.
EDGE_CLASSES = ("flow", "flow2", "sync", "a2a")

_STYLE_BLOCK = re.compile(r"[ \t]*<style>(.*?)</style>\n?", re.S)
_SELECTOR_SPLIT = re.compile(r"(?<=\})\s*")
# Matched tolerantly rather than assuming the hand-authored formatting: a
# diagram re-exported from a design tool may use single quotes, several classes
# on one element, or a separate closing tag.
_PATH_TAG = re.compile(r"<path\b[^>]*>")
_CLASS_ATTR = re.compile(r"""class\s*=\s*["']([^"']*)["']""")


def _scoped_rules(css: str, scope: str) -> str:
    """Prefix every selector in the SVG's stylesheet with the diagram's scope
    class, so six diagrams' worth of `.node` rules can share one stylesheet."""
    out: list[str] = []
    for rule in _SELECTOR_SPLIT.split(css):
        rule = rule.strip()
        if not rule or "{" not in rule:
            continue
        selectors, _, body = rule.partition("{")
        scoped = ", ".join(
            f".{scope} {s.strip()}" for s in selectors.split(",") if s.strip()
        )
        out.append(f"{scoped} {{{body.rstrip().rstrip('}')}}}")
    return "\n".join(out)


def _dashed_classes(css: str) -> set[str]:
    """Classes whose stroke is already dashed. Their dash pattern is meaningful,
    so they fade in rather than draw."""
    dashed: set[str] = set()
    for rule in _SELECTOR_SPLIT.split(css):
        selectors, _, body = rule.partition("{")
        if "stroke-dasharray" not in body:
            continue
        dashed.update(m.group(1) for m in re.finditer(r"\.([\w-]+)", selectors))
    return dashed


def _is_drawable(classes: str, dashed: set[str]) -> bool:
    """A stroke draws itself if it carries an edge class that isn't dashed."""
    names = classes.split()
    return any(c in EDGE_CLASSES and c not in dashed for c in names)


def _count_drawable(svg: str, dashed: set[str]) -> int:
    """How many strokes *should* be marked — derived from the class attributes
    directly, so it stays honest even if the tag matcher misses something."""
    return sum(
        1 for classes in _CLASS_ATTR.findall(svg) if _is_drawable(classes, dashed)
    )


def _mark_drawable(svg: str, dashed: set[str]) -> str:
    """Tag solid flow paths for the draw-on animation.

    `pathLength="1"` normalises every path to a unit length, so one CSS rule
    animates `stroke-dashoffset: 1 -> 0` regardless of the path's real geometry.
    """

    def rewrite(match: re.Match[str]) -> str:
        tag = match.group(0)
        classes = _CLASS_ATTR.search(tag)
        if not classes or not _is_drawable(classes.group(1), dashed):
            return tag
        if "data-draw" in tag:
            return tag
        close = "/>" if tag.endswith("/>") else ">"
        return f'{tag[: -len(close)].rstrip()} pathLength="1" data-draw{close}'

    return _PATH_TAG.sub(rewrite, svg)


def prepare(svg_path: Path, slug: str) -> tuple[str, str]:
    """Return (inline SVG markup, stylesheet text) for one diagram."""
    raw = svg_path.read_text()
    scope = f"dwg-{slug}"

    style_match = _STYLE_BLOCK.search(raw)
    css = style_match.group(1) if style_match else ""
    svg = _STYLE_BLOCK.sub("", raw)

    # Namespace the shared ids and every url(#...) that points at them.
    for ident in re.findall(r'\bid="([\w-]+)"', svg):
        svg = svg.replace(f'id="{ident}"', f'id="{scope}-{ident}"')
        svg = svg.replace(f"url(#{ident})", f"url(#{scope}-{ident})")
    css = re.sub(r"url\(#([\w-]+)\)", rf"url(#{scope}-\1)", css)

    dashed = _dashed_classes(css)
    expected = _count_drawable(svg, dashed)
    svg = _mark_drawable(svg, dashed)
    marked = svg.count("data-draw")

    # Without this the failure is silent: the tag matcher quietly marks nothing,
    # the diagram renders correctly, and the arrows simply never animate. Fail
    # the build instead — a re-exported SVG should be loud about it.
    if marked != expected:
        raise ContentError(
            f"{svg_path.name}: expected {expected} drawable flow paths, marked "
            f"{marked}. The markup shape probably changed — check services/diagrams.py"
        )

    svg = svg.replace("<svg", f'<svg class="dwg {scope}"', 1)

    return svg, _scoped_rules(css, scope)


def build_stylesheet(diagrams: dict[str, Path]) -> tuple[dict[str, str], str]:
    """Prepare every diagram at once.

    Returns the per-slug inline markup and the single stylesheet that styles
    them all — one same-origin file, so the CSP has no objection.
    """
    markup: dict[str, str] = {}
    sheets: list[str] = []
    for slug, path in sorted(diagrams.items()):
        svg, css = prepare(path, slug)
        markup[slug] = svg
        sheets.append(f"/* {path.name} */\n{css}")
    return markup, "\n\n".join(sheets) + "\n"
