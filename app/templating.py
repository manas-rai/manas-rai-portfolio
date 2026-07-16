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
    request-first TemplateResponse signature.

    Templates build internal links with `path_for` (root-relative paths) rather
    than `url_for` (absolute URLs). Behind a proxy that rewrites the host — e.g.
    CloudFront in front of a Lambda Function URL — absolute URLs would point at
    the origin host (the signed Function URL), which breaks navigation. A
    root-relative path always resolves against whatever host the browser is on.
    """

    def path_for(route_name: str, **path_params: object) -> str:
        return request.url_for(route_name, **path_params).path

    context = _base_context(request) | {"path_for": path_for} | (extra or {})
    return templates.TemplateResponse(
        request, name, context, status_code=status_code
    )
