from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templating import get_index, render

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    index = get_index(request)
    return render(
        request,
        "home.html",
        {
            "featured_projects": index.featured_projects,
            "recent_posts": index.posts[:3],
        },
    )
