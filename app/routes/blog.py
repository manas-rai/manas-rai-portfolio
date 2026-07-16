from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.templating import get_index, render

router = APIRouter()

PAGE_SIZE = 10


@router.get("/blog", response_class=HTMLResponse)
def blog_list(request: Request, page: int = 1, tag: str | None = None) -> HTMLResponse:
    index = get_index(request)
    posts = index.posts_for_tag(tag) if tag else index.posts

    page = max(page, 1)
    start = (page - 1) * PAGE_SIZE
    page_posts = posts[start : start + PAGE_SIZE]
    has_next = start + PAGE_SIZE < len(posts)

    return render(
        request,
        "blog_list.html",
        {
            "posts": page_posts,
            "page": page,
            "has_next": has_next,
            "has_prev": page > 1,
            "active_tag": tag,
            "all_tags": index.all_tags,
        },
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
def blog_post(request: Request, slug: str) -> HTMLResponse:
    index = get_index(request)
    post = index.post(slug)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    return render(request, "blog_post.html", {"post": post})
