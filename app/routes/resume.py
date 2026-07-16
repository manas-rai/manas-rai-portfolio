from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templating import get_index, render

router = APIRouter()


@router.get("/resume", response_class=HTMLResponse)
def resume(request: Request) -> HTMLResponse:
    index = get_index(request)
    return render(
        request,
        "resume.html",
        {"resume": index.resume, "projects": index.projects},
    )
