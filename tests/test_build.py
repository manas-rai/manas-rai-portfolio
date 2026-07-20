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
        "contact/sent/index.html",
        "404.html",
    ):
        assert (site / page).exists(), f"missing {page}"


def test_home_contains_site_name(site: Path) -> None:
    assert "Manas Rai" in (site / "index.html").read_text()


def test_blog_post_and_tag_pages_render(site: Path) -> None:
    post = site / "blog" / "2026-07-16-hello-world" / "index.html"
    assert post.exists()
    assert "Building this site" in post.read_text()

    tag_page = site / "blog" / "tag" / "python" / "index.html"
    assert tag_page.exists()
    assert "Building this site" in tag_page.read_text()


def test_contact_form_posts_to_pages_function(site: Path) -> None:
    html = (site / "contact" / "index.html").read_text()
    assert 'action="/api/contact"' in html
    assert 'name="website"' in html  # honeypot survives the static build
    assert "js/contact.js" in html


def test_static_assets_copied(site: Path) -> None:
    assert (site / "static" / "css" / "style.css").exists()
    assert (site / "static" / "js" / "contact.js").exists()
    assert (site / "static" / "fonts" / "space-grotesk-700.woff2").exists()
    assert (site / "static" / "images" / "favicon.svg").exists()


def test_pages_carry_canonical_and_og_meta(site: Path) -> None:
    html = (site / "blog" / "2026-07-16-hello-world" / "index.html").read_text()
    assert '<link rel="canonical" href="https://manas-rai-portfolio.pages.dev/blog/2026-07-16-hello-world/"' in html
    assert 'property="og:title"' in html


def test_nav_marks_current_section(site: Path) -> None:
    html = (site / "projects" / "index.html").read_text()
    assert 'aria-current="page">Projects</a>' in html
    assert 'aria-current="page">Blog</a>' not in html


def test_headers_file_sets_security_headers(site: Path) -> None:
    headers = (site / "_headers").read_text()
    assert "Content-Security-Policy" in headers
    assert "X-Frame-Options: DENY" in headers


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


def test_slugify_rejects_unusable_values() -> None:
    assert slugify("FastAPI / Jinja2") == "fastapi-jinja2"
    with pytest.raises(ContentError):
        slugify("···")
