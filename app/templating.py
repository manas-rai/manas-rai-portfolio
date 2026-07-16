from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR, get_settings
from app.services.content_loader import ContentIndex

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_index(request: Request) -> ContentIndex:
    return request.app.state.content_index


def _base_context(request: Request) -> dict:
    """Context shared by every page (site chrome, nav)."""
    settings = get_settings()
    return {
        "site_name": settings.site_name,
        "site_tagline": settings.site_tagline,
        "contact_email": settings.contact_email,
    }


def render(
    request: Request,
    name: str,
    extra: dict | None = None,
    *,
    status_code: int = 200,
) -> HTMLResponse:
    """Render a template with the shared base context, using Starlette's
    request-first TemplateResponse signature."""
    context = _base_context(request) | (extra or {})
    return templates.TemplateResponse(
        request, name, context, status_code=status_code
    )
