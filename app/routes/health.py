from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe for the keep-alive ping and platform health checks
    (design doc §7.1)."""
    return {"status": "ok"}
