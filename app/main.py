from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import POSTS_DIR, STATIC_DIR, CONTENT_DIR, get_settings
from app.limiter import limiter
from app.routes import blog, contact, health, home, projects, resume
from app.services.content_loader import build_index
from app.templating import render


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build the content index once at startup (design doc §4.5). A malformed
    # file raises ContentError here, failing the boot instead of a live request.
    settings = get_settings()
    app.state.content_index = build_index(
        CONTENT_DIR / "projects.yaml",
        POSTS_DIR,
        CONTENT_DIR / "resume.yaml",
        include_drafts=not settings.is_production,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Manas Rai — Portfolio", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    for module in (home, projects, blog, resume, contact, health):
        app.include_router(module.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> HTMLResponse:
        if exc.status_code == 404:
            return render(request, "errors/404.html", status_code=404)
        return render(
            request,
            "errors/500.html",
            {"status_code": exc.status_code},
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> HTMLResponse:
        # No framework stack traces leak to users (§6.1).
        return render(request, "errors/500.html", {"status_code": 500}, status_code=500)

    return app


app = create_app()
