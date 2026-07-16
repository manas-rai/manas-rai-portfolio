from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:  # triggers lifespan -> builds content index
        yield c


def test_home_ok(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Manas Rai" in resp.text


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_unknown_post_renders_404(client: TestClient) -> None:
    resp = client.get("/blog/does-not-exist")
    assert resp.status_code == 404
    assert "Not found" in resp.text


def test_contact_validation_error_rerenders_form(client: TestClient) -> None:
    resp = client.post("/contact", data={"name": "A", "email": "bad", "message": "hi"})
    assert resp.status_code == 200
    assert "contact-form" in resp.text  # form re-rendered, not a 500


def test_contact_honeypot_silently_accepts(client: TestClient) -> None:
    resp = client.post(
        "/contact",
        data={"name": "Bot", "email": "b@b.com", "message": "spam", "website": "x"},
    )
    assert resp.status_code == 200
    assert "on its way" in resp.text
