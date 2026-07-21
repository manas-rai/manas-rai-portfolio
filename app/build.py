"""Static site generator: renders the Jinja templates + flat-file content into
`dist/`, ready for any static host (Cloudflare Pages). Run as:

    uv run python -m app.build [--drafts] [--out DIR]
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import (
    BASE_PATH,
    CONTACT_EMAIL,
    CONTENT_DIR,
    DIST_DIR,
    GITHUB_URL,
    LINKEDIN_URL,
    POSTS_DIR,
    SITE_NAME,
    SITE_ROLE,
    SITE_TAGLINE,
    SITE_URL,
    STATIC_DIR,
    TEMPLATES_DIR,
)
from app.services.content_loader import ContentError, ContentIndex, Post, build_index

PAGE_SIZE = 10

# The CSP allows only same-origin resources — no third-party anything — so an
# injected tag has nothing it is allowed to load or execute. GitHub Pages
# cannot set response headers, so it ships as a <meta> tag in base.html
# (frame-ancestors and non-CSP headers like X-Frame-Options are not
# expressible that way — an accepted limitation of static-only hosting).
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'"
)

ROUTES = {
    "home": "/",
    "projects": "/projects/",
    "blog_list": "/blog/",
    "resume": "/resume/",
    "contact_form": "/contact/",
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ContentError(f"Cannot build a URL slug from {value!r}")
    return slug


def route_path(name: str, **params: object) -> str:
    """Un-prefixed site path — used for file locations in dist/ and as the
    canonical suffix appended to SITE_URL."""
    if name == "static":
        return f"/static/{params['path']}"
    if name == "blog_post":
        return f"/blog/{params['slug']}/"
    if name == "blog_tag":
        return f"/blog/tag/{slugify(str(params['tag']))}/"
    if name == "projects_tech":
        return f"/projects/tech/{slugify(str(params['tech']))}/"
    return ROUTES[name]


def path_for(name: str, **params: object) -> str:
    """Href for templates: route_path prefixed with BASE_PATH, so the same
    build works at a domain root or under a project subpath."""
    return f"{BASE_PATH}{route_path(name, **params)}"


def _unique_slugs(values: list[str], kind: str) -> dict[str, str]:
    """Map each value to its slug, failing the build on collisions so two
    filters never silently overwrite each other's page."""
    slugs: dict[str, str] = {}
    for value in values:
        slug = slugify(value)
        if slug in slugs.values():
            raise ContentError(f"Duplicate {kind} slug {slug!r} (from {value!r})")
        slugs[value] = slug
    return slugs


def _filter_links(
    all_url: str, values: list[str], url_for_value, active: str | None
) -> list[dict[str, object]]:
    links = [{"label": "All", "url": all_url, "active": active is None}]
    links += [
        {"label": v, "url": url_for_value(v), "active": v == active} for v in values
    ]
    return links


def _paginate(posts: list[Post], base_url: str) -> list[dict[str, object]]:
    """Split posts into per-page render contexts. Page 1 lives at base_url,
    page N at base_url + 'page/N/'."""
    pages = [posts[i : i + PAGE_SIZE] for i in range(0, len(posts), PAGE_SIZE)] or [[]]

    def url(page_num: int) -> str:
        return base_url if page_num == 1 else f"{base_url}page/{page_num}/"

    return [
        {
            "posts": page_posts,
            "url": url(n),
            "prev_url": url(n - 1) if n > 1 else None,
            "next_url": url(n + 1) if n < len(pages) else None,
        }
        for n, page_posts in enumerate(pages, start=1)
    ]


class SiteWriter:
    def __init__(self, env: Environment, dist: Path, base_context: dict) -> None:
        self.env = env
        self.dist = dist
        self.base_context = base_context

    def page(self, template: str, url: str, context: dict | None = None) -> None:
        """Render template to dist/<url>/index.html (or a literal *.html path).
        Injects page_url so templates can emit canonical/OG URLs."""
        html = self.env.get_template(template).render(
            self.base_context | {"page_url": url} | (context or {})
        )
        relative = url.lstrip("/")
        out = (
            self.dist / relative
            if relative.endswith(".html")
            else self.dist / relative / "index.html"
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html)


def build(dist: Path = DIST_DIR, *, include_drafts: bool = False) -> None:
    index = build_index(
        CONTENT_DIR / "projects.yaml",
        POSTS_DIR,
        CONTENT_DIR / "resume.yaml",
        include_drafts=include_drafts,
    )

    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(("html",)),
    )
    writer = SiteWriter(
        env,
        dist,
        {
            "site_name": SITE_NAME,
            "site_role": SITE_ROLE,
            "site_tagline": SITE_TAGLINE,
            "contact_email": CONTACT_EMAIL,
            "site_url": SITE_URL,
            "github_url": GITHUB_URL,
            "linkedin_url": LINKEDIN_URL,
            "csp": CSP,
            "path_for": path_for,
        },
    )

    _write_home(writer, index)
    _write_projects(writer, index)
    _write_blog(writer, index)
    writer.page(
        "resume.html",
        "/resume/",
        {"resume": index.resume, "projects": index.projects, "active_nav": "resume"},
    )
    writer.page("contact.html", "/contact/", {"active_nav": "contact"})
    writer.page("errors/404.html", "/404.html")

    shutil.copytree(STATIC_DIR, dist / "static")


def _write_home(writer: SiteWriter, index: ContentIndex) -> None:
    writer.page(
        "home.html",
        "/",
        {"featured_projects": index.featured_projects, "recent_posts": index.posts[:3]},
    )


def _write_projects(writer: SiteWriter, index: ContentIndex) -> None:
    all_tech = sorted({t for p in index.projects for t in p.tech})
    _unique_slugs(all_tech, "tech")

    def render(url: str, active: str | None) -> None:
        projects = (
            [p for p in index.projects if active in p.tech] if active else index.projects
        )
        filters = _filter_links(
            path_for("projects"),
            all_tech,
            lambda t: path_for("projects_tech", tech=t),
            active,
        )
        writer.page(
            "projects.html",
            url,
            {"projects": projects, "filters": filters, "active_nav": "projects"},
        )

    render(ROUTES["projects"], None)
    for tech in all_tech:
        render(route_path("projects_tech", tech=tech), tech)


def _write_blog(writer: SiteWriter, index: ContentIndex) -> None:
    _unique_slugs(index.all_tags, "tag")

    def render_list(base_url: str, posts: list[Post], active: str | None) -> None:
        filters = _filter_links(
            path_for("blog_list"),
            index.all_tags,
            lambda t: path_for("blog_tag", tag=t),
            active,
        )
        for page in _paginate(posts, base_url):
            writer.page(
                "blog_list.html",
                page["url"],
                {
                    "posts": page["posts"],
                    "filters": filters,
                    "prev_url": f"{BASE_PATH}{page['prev_url']}" if page["prev_url"] else None,
                    "next_url": f"{BASE_PATH}{page['next_url']}" if page["next_url"] else None,
                    "active_nav": "blog",
                },
            )

    render_list(ROUTES["blog_list"], index.posts, None)
    for tag in index.all_tags:
        render_list(route_path("blog_tag", tag=tag), index.posts_for_tag(tag), tag)

    for post in index.posts:
        writer.page(
            "blog_post.html",
            route_path("blog_post", slug=post.slug),
            {"post": post, "active_nav": "blog"},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static site into dist/")
    parser.add_argument("--drafts", action="store_true", help="include draft posts")
    parser.add_argument("--out", type=Path, default=DIST_DIR, help="output directory")
    args = parser.parse_args()
    build(args.out, include_drafts=args.drafts)
    print(f"Built site into {args.out}")


if __name__ == "__main__":
    main()
