from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templating import get_index, render

router = APIRouter()


@router.get("/projects", response_class=HTMLResponse)
def projects(request: Request, tech: str | None = None) -> HTMLResponse:
    index = get_index(request)
    items = index.projects
    if tech:
        items = [p for p in items if tech in p.tech]

    all_tech = sorted({t for p in index.projects for t in p.tech})
    return render(
        request,
        "projects.html",
        {"projects": items, "all_tech": all_tech, "active_tech": tech},
    )
