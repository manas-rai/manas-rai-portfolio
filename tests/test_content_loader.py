from __future__ import annotations

from pathlib import Path

import pytest

from app.services.content_loader import ContentError, build_index

VALID_POST = """---
title: "A Post"
date: 2026-07-16
summary: "A summary."
tags: [python, meta]
---

# Heading

Some **body** text.
"""


def _write(path: Path, content: str) -> None:
    path.write_text(content)


def test_build_index_parses_projects_and_posts(tmp_path: Path) -> None:
    projects = tmp_path / "projects.yaml"
    _write(projects, "- title: X\n  summary: Y\n  tech: [Python]\n  featured: true\n")
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir()
    _write(posts_dir / "2026-07-16-a-post.md", VALID_POST)

    index = build_index(projects, posts_dir, include_drafts=False)

    assert len(index.projects) == 1
    assert index.featured_projects[0].title == "X"
    assert index.post("2026-07-16-a-post").title == "A Post"
    assert "python" in index.all_tags


def test_malformed_frontmatter_raises_at_build(tmp_path: Path) -> None:
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir()
    # Missing required 'summary'.
    _write(
        posts_dir / "bad.md",
        '---\ntitle: "T"\ndate: 2026-07-16\n---\n\nBody\n',
    )

    with pytest.raises(ContentError):
        build_index(tmp_path / "projects.yaml", posts_dir, include_drafts=False)


def test_drafts_excluded_in_production(tmp_path: Path) -> None:
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir()
    draft = VALID_POST.replace("tags: [python, meta]", "draft: true")
    _write(posts_dir / "draft.md", draft)

    prod = build_index(tmp_path / "projects.yaml", posts_dir, include_drafts=False)
    dev = build_index(tmp_path / "projects.yaml", posts_dir, include_drafts=True)

    assert prod.posts == []
    assert len(dev.posts) == 1


def test_rendered_html_is_sanitized(tmp_path: Path) -> None:
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir()
    xss = VALID_POST + "\n<script>alert('x')</script>\n"
    _write(posts_dir / "2026-07-16-a-post.md", xss)

    index = build_index(tmp_path / "projects.yaml", posts_dir, include_drafts=False)

    assert "<script>" not in index.post("2026-07-16-a-post").html
