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


def test_case_study_page_renders_with_diagram(site: Path) -> None:
    page = site / "projects" / "devflow-kit" / "index.html"
    assert page.exists()
    html = page.read_text()
    assert "case study" in html.lower()
    assert "devflow-kit-architecture.svg" in html
    assert (site / "static" / "images" / "devflow-kit-architecture.svg").exists()


def test_project_cards_link_to_existing_case_studies(site: Path) -> None:
    projects = (site / "projects" / "index.html").read_text()
    # DevFlow Kit has a case study; its card links to it.
    assert 'href="/projects/devflow-kit/">Case study' in projects
    # A project without a case study gets no such link.
    assert 'href="/projects/costtracker/"' not in projects


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
    assert (site / "static" / "fonts" / "space-grotesk-700.woff2").exists()
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
    HTML itself."""
    for page in site.rglob("*.html"):
        assert 'http-equiv="Content-Security-Policy"' in page.read_text(), page


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
