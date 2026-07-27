from __future__ import annotations

from pathlib import Path

import pytest

from app.build import build, path_for, slugify
from app.services.content_loader import ContentError


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dist = tmp_path_factory.mktemp("dist")
    build(dist, include_drafts=False)
    return dist


def test_renders_all_top_level_pages(site: Path) -> None:
    for page in (
        "index.html",
        "projects/index.html",
        "blog/index.html",
        "resume/index.html",
        "contact/index.html",
        "404.html",
    ):
        assert (site / page).exists(), f"missing {page}"


def test_home_contains_site_name(site: Path) -> None:
    assert "Manas Rai" in (site / "index.html").read_text()


def test_mechanism_components_render(site: Path) -> None:
    """Odometer stats and the plate title-block footer are the mechanism design
    language — assert they reach the built home page."""
    html = (site / "index.html").read_text()
    assert "digit-strip d3" in html  # odometer for 3000 concurrent sessions
    assert "story-section" in html  # Mechanical vs AI superpower comparison
    assert 'class="plate"' in html and "Drawn by" in html  # title-block footer


def test_superpower_story_renders(site: Path) -> None:
    """The mechanical-to-AI story is the home page's differentiator; assert all
    three cards reach the build."""
    html = (site / "index.html").read_text()
    assert "Why Mechanical Engineering Makes Me a Better AI Engineer" in html
    assert "ERROR BUDGETING" in html
    assert "CLOSED-LOOP CONTROL" in html
    assert "LOAD TESTING" in html


def test_home_page_leads_with_projects_not_chrome(site: Path) -> None:
    """The generic RAG schematic and the simple/tech copy toggle were removed:
    both put chrome (and unsourced metrics) ahead of the actual work."""
    html = (site / "index.html").read_text()
    for gone in (
        "ai-schematic-section",
        "DWG-AI-01",
        "view-toggle",
        "vt-simple",
        "tech-label",
        "simple-label",
    ):
        assert gone not in html, gone


def test_headline_stats_link_to_their_source(site: Path) -> None:
    """An unsourced number is decoration — every home-page stat must link to the
    page that substantiates it."""
    html = (site / "index.html").read_text()
    assert 'href="/projects/clinical-simulation-platform/"' in html  # 3,000 sessions
    assert html.count('class="stat-link"') == 3


def test_no_undefined_css_custom_properties() -> None:
    """A `var(--x)` with no definition invalidates the whole declaration, so a
    missing token shows up as a stray currentColor border, not a build error."""
    import re

    css = (Path(__file__).parent.parent / "static" / "css" / "style.css").read_text()
    defined = set(re.findall(r"^\s*(--[\w-]+)\s*:", css, re.MULTILINE))
    # Only fallback-less references matter — `var(--mx, 50%)` is how the JS-set
    # cursor properties degrade before a pointer has moved.
    used = set(re.findall(r"var\(\s*(--[\w-]+)\s*\)", css))
    assert not (used - defined), f"undefined CSS variables: {sorted(used - defined)}"


def test_interaction_layer_present(site: Path) -> None:
    """The unscrew-reveal + specular JS ships and is wired; the enhancement
    script is same-origin (CSP-safe) and referenced with defer."""
    assert (site / "static" / "js" / "mech.js").exists()
    home = (site / "index.html").read_text()
    assert "static/js/mech.js" in home


def test_project_card_reveals_spec_sheet(site: Path) -> None:
    """Cards carry a collapsible spec sheet with real, comma-safe values that
    the bolt reveals — the interaction has actual content behind it."""
    projects = (site / "projects" / "index.html").read_text()
    assert 'class="spec-sheet"' in projects
    assert "unscrew for spec" in projects
    assert "2,000+ concurrent · sub-second" in projects  # comma survived YAML
    assert "Isolation Forest (idle EC2) + rules" in projects


def test_case_study_page_renders_with_diagram(site: Path) -> None:
    page = site / "projects" / "devflow-kit" / "index.html"
    assert page.exists()
    html = page.read_text()
    assert "deep dive" in html.lower()
    assert 'class="dwg dwg-devflow-kit"' in html  # inlined, not an <img>
    assert (site / "static" / "images" / "devflow-kit-architecture.svg").exists()


def test_inlined_diagrams_carry_no_inline_styles(site: Path) -> None:
    """Inlining the SVGs would smuggle their <style> blocks into the page, where
    `style-src 'self'` blocks them and the diagram renders unstyled. The rules
    must be lifted into a real stylesheet instead."""
    sheet = site / "static" / "css" / "diagrams.css"
    assert sheet.exists()
    assert ".dwg-devflow-kit .node" in sheet.read_text()  # scoped, not global

    for slug in ("devflow-kit", "healthcare-rag-platform", "reglens"):
        html = (site / "projects" / slug / "index.html").read_text()
        assert "<style>" not in html, slug
        assert 'href="/static/css/diagrams.css"' in html, slug


def test_diagram_flow_arrows_are_drawable(site: Path) -> None:
    """`pathLength="1"` normalises every arrow so one dashoffset rule animates
    them all. Dashed strokes are deliberately left alone — overriding their
    dasharray would destroy the dashes that carry meaning."""
    html = (site / "projects" / "devflow-kit" / "index.html").read_text()
    assert html.count("data-draw") >= 3
    assert html.count('pathLength="1"') == html.count("data-draw")
    assert 'class="sync" pathLength' not in html  # dashed edges stay dashed


def test_diagram_slugs_are_namespaced(site: Path) -> None:
    """Every source SVG defines the same `accent`/`arrow` ids; inlined, two on
    one page would collide."""
    html = (site / "projects" / "reglens" / "index.html").read_text()
    assert 'id="dwg-reglens-accent"' in html
    assert 'id="accent"' not in html


def test_project_cards_link_to_existing_case_studies(site: Path) -> None:
    projects = (site / "projects" / "index.html").read_text()
    # Every project now has a deep-dive page; each card links to its own.
    for slug in (
        "healthcare-rag-platform",
        "clinical-simulation-platform",
        "devflow-kit",
        "reglens",
        "costtracker",
        "cloud-waste-hunter",
    ):
        assert f'href="/projects/{slug}/">Deep dive' in projects, slug


def test_console_content_is_server_rendered(site: Path) -> None:
    """The console only toggles visibility — its panels ship in the HTML so the
    content is indexable and reachable without JS."""
    for page in ("index.html", "projects/index.html", "blog/index.html"):
        html = (site / page).read_text()
        assert html.count('class="console-panel') == 3, page
        assert "/stack" in html and "/interview" in html, page


def test_interview_answers_load_and_link_to_case_studies(site: Path) -> None:
    """Every trade-off points at the work behind it — the whole reason the
    answers live in content/ rather than a template."""
    html = (site / "index.html").read_text()
    assert html.count('class="qa"') >= 5
    assert "Architectural trade-offs" in html
    for slug in ("reglens", "cloud-waste-hunter", "devflow-kit"):
        assert f'href="/projects/{slug}/"' in html, slug


def test_console_trigger_is_progressively_enhanced(site: Path) -> None:
    """The ⌘K button ships hidden and is revealed by mech.js — advertising a
    keyboard shortcut that cannot fire is worse than staying quiet."""
    html = (site / "index.html").read_text()
    assert 'class="console-open" id="console-open" hidden' in html
    assert 'id="console" hidden' in html


def test_blog_post_and_tag_pages_render(site: Path) -> None:
    post = site / "blog" / "2026-07-16-hello-world" / "index.html"
    assert post.exists()
    assert "Building this site" in post.read_text()

    tag_page = site / "blog" / "tag" / "python" / "index.html"
    assert tag_page.exists()
    assert "Building this site" in tag_page.read_text()


def test_contact_page_offers_direct_channels(site: Path) -> None:
    html = (site / "contact" / "index.html").read_text()
    assert 'href="mailto:rai.manas12@gmail.com"' in html
    assert "linkedin.com/in/manasrai12" in html


def test_static_assets_copied(site: Path) -> None:
    assert (site / "static" / "css" / "style.css").exists()
    assert (site / "static" / "fonts" / "oswald-700.woff2").exists()
    assert (site / "static" / "fonts" / "plex-mono-500.woff2").exists()
    assert (site / "static" / "fonts" / "inter-400.woff2").exists()
    assert (site / "static" / "images" / "favicon.svg").exists()


def test_pages_carry_canonical_and_og_meta(site: Path) -> None:
    from app.config import SITE_URL

    html = (site / "blog" / "2026-07-16-hello-world" / "index.html").read_text()
    assert f'<link rel="canonical" href="{SITE_URL}/blog/2026-07-16-hello-world/"' in html
    assert 'property="og:title"' in html


def test_nav_marks_current_section(site: Path) -> None:
    html = (site / "projects" / "index.html").read_text()
    assert 'aria-current="page">Projects</a>' in html
    assert 'aria-current="page">Blog</a>' not in html


def test_every_page_ships_csp_meta_tag(site: Path) -> None:
    """GitHub Pages cannot set response headers, so the CSP must be in the
    HTML itself. The printable resume is a deliberate standalone document
    (inline styles, meant for PDF export) and is exempt."""
    for page in site.rglob("*.html"):
        if page.parent.name == "print":
            continue
        assert 'http-equiv="Content-Security-Policy"' in page.read_text(), page


def test_seo_artifacts_generated(site: Path) -> None:
    assert (site / "robots.txt").exists()
    sitemap = (site / "sitemap.xml").read_text()
    assert "https://manasrai.is-a.dev/projects/reglens/" in sitemap
    assert "/resume/print/" not in sitemap  # noindex print page stays out
    feed = (site / "feed.xml").read_text()
    assert "<rss" in feed and "devflow-kit" in feed


def test_no_query_param_links_remain(site: Path) -> None:
    """Static hosting can't vary on query strings — every internal link must be
    a real path."""
    for page in site.rglob("*.html"):
        assert "?tech=" not in page.read_text()
        assert "?tag=" not in page.read_text()


def test_path_for_routes() -> None:
    assert path_for("home") == "/"
    assert path_for("blog_post", slug="a-post") == "/blog/a-post/"
    assert path_for("blog_tag", tag="Python 3") == "/blog/tag/python-3/"
    assert path_for("static", path="css/style.css") == "/static/css/style.css"


def test_path_for_honors_base_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """GitHub Pages serves under /manas-rai-portfolio/ until the custom domain
    flips; hrefs must carry the prefix while dist/ file paths must not."""
    import app.build as build_module

    monkeypatch.setattr(build_module, "BASE_PATH", "/manas-rai-portfolio")
    assert path_for("home") == "/manas-rai-portfolio/"
    assert path_for("blog_post", slug="x") == "/manas-rai-portfolio/blog/x/"
    assert build_module.route_path("blog_post", slug="x") == "/blog/x/"


def test_slugify_rejects_unusable_values() -> None:
    assert slugify("FastAPI / Jinja2") == "fastapi-jinja2"
    with pytest.raises(ContentError):
        slugify("···")
