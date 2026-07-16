from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templating import render

router = APIRouter()


@router.get("/resume", response_class=HTMLResponse)
def resume(request: Request) -> HTMLResponse:
    return render(request, "resume.html")
