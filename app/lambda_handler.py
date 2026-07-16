from __future__ import annotations

from mangum import Mangum

from app.main import app

# ASGI-to-Lambda adapter. lifespan="on" forces Starlette's startup to run on
# each cold container init, building the content index (design §4.5) before any
# request is served — a malformed content file fails the init, not a request.
handler = Mangum(app, lifespan="on")
