from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter
import markdown as md
import nh3
import yaml

# Tags/attributes permitted in rendered post HTML. Anything outside this set is
# stripped by nh3 — see design doc §4.2. Widening this is a deliberate, reviewed
# change, not an incidental one.
ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3",
    "h4", "h5", "h6", "hr", "i", "img", "li", "ol", "p", "pre", "span", "strong",
    "table", "tbody", "td", "th", "thead", "tr", "ul",
}
# nh3 manages the "rel" attribute on <a> itself (adds noopener/noreferrer), so
# it must not appear here.
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "code": {"class"},
    "span": {"class"},
}


class ContentError(Exception):
    """Raised when content on disk is malformed. Surfaced at startup so a bad
    commit fails the deploy rather than 500-ing on a live request."""


@dataclass(frozen=True)
class Project:
    title: str
    summary: str
    tech: list[str]
    github: str | None = None
    demo: str | None = None
    featured: bool = False
    # Short italic descriptor used on the printable resume ("Open Source",
    # "Multi-Agent SDLC Automation").
    descriptor: str = ""


@dataclass(frozen=True)
class Post:
    slug: str
    title: str
    date: date
    summary: str
    tags: list[str]
    html: str
    draft: bool = False


@dataclass(frozen=True)
class CaseStudy:
    slug: str
    title: str
    subtitle: str
    tech: list[str]
    html: str
    github: str | None = None
    demo: str | None = None
    diagram: str | None = None
    diagram_caption: str = ""


@dataclass(frozen=True)
class ExperienceEntry:
    role: str
    company: str
    period: str
    highlights: list[str]


@dataclass(frozen=True)
class EducationEntry:
    qualification: str
    institution: str
    period: str
    note: str = ""


@dataclass(frozen=True)
class SkillGroup:
    group: str
    items: list[str]


@dataclass(frozen=True)
class Resume:
    name: str
    title: str
    location: str
    email: str
    summary: str
    links: list[dict[str, str]]
    skills: list[SkillGroup]
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    certifications: list[str] = field(default_factory=list)
    awards: list[str] = field(default_factory=list)
    phone: str = ""


@dataclass(frozen=True)
class ContentIndex:
    """Immutable, in-memory view of all content, built once at startup."""

    projects: list[Project]
    posts: list[Post] = field(default_factory=list)
    resume: Resume | None = None
    case_studies: list[CaseStudy] = field(default_factory=list)
    _by_slug: dict[str, Post] = field(default_factory=dict)
    _by_tag: dict[str, list[Post]] = field(default_factory=dict)

    def post(self, slug: str) -> Post | None:
        return self._by_slug.get(slug)

    def posts_for_tag(self, tag: str) -> list[Post]:
        return self._by_tag.get(tag, [])

    @property
    def featured_projects(self) -> list[Project]:
        return [p for p in self.projects if p.featured]

    @property
    def all_tags(self) -> list[str]:
        return sorted(self._by_tag)


def _load_projects(projects_file: Path) -> list[Project]:
    if not projects_file.exists():
        return []
    try:
        raw = yaml.safe_load(projects_file.read_text()) or []
    except yaml.YAMLError as exc:
        raise ContentError(f"Malformed projects file {projects_file}: {exc}") from exc
    if not isinstance(raw, list):
        raise ContentError(f"{projects_file} must contain a list of projects")

    projects: list[Project] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or "title" not in item or "summary" not in item:
            raise ContentError(f"Project #{i} in {projects_file} needs title + summary")
        projects.append(
            Project(
                title=item["title"],
                summary=item["summary"],
                tech=list(item.get("tech", [])),
                github=item.get("github"),
                demo=item.get("demo"),
                featured=bool(item.get("featured", False)),
                descriptor=str(item.get("descriptor", "")),
            )
        )
    return projects


def _render_markdown(body: str) -> str:
    html = md.markdown(
        body,
        extensions=["fenced_code", "tables", "codehilite", "toc"],
    )
    return nh3.clean(
        html, tags=ALLOWED_TAGS, attributes={k: set(v) for k, v in ALLOWED_ATTRIBUTES.items()}
    )


def _load_post(path: Path) -> Post:
    try:
        fm = frontmatter.load(path)
    except Exception as exc:  # frontmatter raises a variety of parse errors
        raise ContentError(f"Cannot parse frontmatter in {path}: {exc}") from exc

    missing = [k for k in ("title", "date", "summary") if k not in fm.metadata]
    if missing:
        raise ContentError(f"{path} missing frontmatter keys: {', '.join(missing)}")

    raw_date = fm["date"]
    if not isinstance(raw_date, date):
        raise ContentError(f"{path} 'date' must be a YYYY-MM-DD date, got {raw_date!r}")

    slug = path.stem
    return Post(
        slug=slug,
        title=str(fm["title"]),
        date=raw_date,
        summary=str(fm["summary"]),
        tags=list(fm.get("tags", [])),
        html=_render_markdown(fm.content),
        draft=bool(fm.get("draft", False)),
    )


def _load_case_study(path: Path) -> CaseStudy:
    try:
        fm = frontmatter.load(path)
    except Exception as exc:
        raise ContentError(f"Cannot parse frontmatter in {path}: {exc}") from exc

    missing = [k for k in ("title", "subtitle") if k not in fm.metadata]
    if missing:
        raise ContentError(f"{path} missing frontmatter keys: {', '.join(missing)}")

    return CaseStudy(
        slug=path.stem,
        title=str(fm["title"]),
        subtitle=str(fm["subtitle"]),
        tech=list(fm.get("tech", [])),
        html=_render_markdown(fm.content),
        github=fm.get("github"),
        demo=fm.get("demo"),
        diagram=fm.get("diagram"),
        diagram_caption=str(fm.get("diagram_caption", "")),
    )


def _load_resume(resume_file: Path) -> Resume | None:
    if not resume_file.exists():
        return None
    try:
        raw = yaml.safe_load(resume_file.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ContentError(f"Malformed resume file {resume_file}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContentError(f"{resume_file} must be a mapping")

    required = ("name", "title", "summary")
    missing = [k for k in required if k not in raw]
    if missing:
        raise ContentError(f"{resume_file} missing keys: {', '.join(missing)}")

    try:
        return Resume(
            name=raw["name"],
            title=raw["title"],
            location=raw.get("location", ""),
            email=raw.get("email", ""),
            summary=raw["summary"],
            links=[dict(link) for link in raw.get("links", [])],
            skills=[
                SkillGroup(group=s["group"], items=list(s.get("items", [])))
                for s in raw.get("skills", [])
            ],
            experience=[
                ExperienceEntry(
                    role=e["role"],
                    company=e["company"],
                    period=e["period"],
                    highlights=list(e.get("highlights", [])),
                )
                for e in raw.get("experience", [])
            ],
            education=[
                EducationEntry(
                    qualification=ed["qualification"],
                    institution=ed.get("institution", ""),
                    period=ed["period"],
                    note=str(ed.get("note", "")),
                )
                for ed in raw.get("education", [])
            ],
            certifications=[str(c) for c in raw.get("certifications", [])],
            awards=[str(a) for a in raw.get("awards", [])],
            phone=str(raw.get("phone", "")),
        )
    except (KeyError, TypeError) as exc:
        raise ContentError(f"Invalid entry in {resume_file}: {exc}") from exc


def build_index(
    projects_file: Path,
    posts_dir: Path,
    resume_file: Path,
    *,
    include_drafts: bool,
    case_studies_dir: Path | None = None,
) -> ContentIndex:
    """Parse all content once and build lookup structures. Raises ContentError
    on any malformed file so failures happen at boot, not per-request."""
    projects = _load_projects(projects_file)
    resume = _load_resume(resume_file)

    case_studies: list[CaseStudy] = []
    if case_studies_dir and case_studies_dir.exists():
        case_studies = [
            _load_case_study(p) for p in sorted(case_studies_dir.glob("*.md"))
        ]
        slugs = [c.slug for c in case_studies]
        if len(set(slugs)) != len(slugs):
            raise ContentError("Duplicate case-study slug detected")

    posts: list[Post] = []
    if posts_dir.exists():
        for path in sorted(posts_dir.glob("*.md")):
            post = _load_post(path)
            if post.draft and not include_drafts:
                continue
            posts.append(post)

    posts.sort(key=lambda p: p.date, reverse=True)

    by_slug = {p.slug: p for p in posts}
    if len(by_slug) != len(posts):
        raise ContentError("Duplicate post slug detected in content/posts")

    by_tag: dict[str, list[Post]] = {}
    for post in posts:
        for tag in post.tags:
            by_tag.setdefault(tag, []).append(post)

    return ContentIndex(
        projects=projects,
        posts=posts,
        resume=resume,
        case_studies=case_studies,
        _by_slug=by_slug,
        _by_tag=by_tag,
    )
