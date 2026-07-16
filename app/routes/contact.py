from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, ValidationError

from app.config import get_settings
from app.limiter import limiter
from app.services.email_sender import EmailError, send_contact_message
from app.templating import render

router = APIRouter()


class ContactSubmission(BaseModel):
    name: str
    email: EmailStr
    message: str

    @classmethod
    def field_errors(cls, exc: ValidationError) -> dict[str, str]:
        return {str(e["loc"][0]): e["msg"] for e in exc.errors()}


def _render_form(
    request: Request,
    *,
    values: dict[str, str] | None = None,
    errors: dict[str, str] | None = None,
    flash: str | None = None,
    sent: bool = False,
) -> HTMLResponse:
    return render(
        request,
        "contact.html",
        {
            "values": values or {},
            "errors": errors or {},
            "flash": flash,
            "sent": sent,
        },
    )


@router.get("/contact", response_class=HTMLResponse)
def contact_form(request: Request) -> HTMLResponse:
    return _render_form(request)


@router.post("/contact", response_class=HTMLResponse)
@limiter.limit("5/minute")
def contact_submit(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    message: str = Form(""),
    website: str = Form(""),  # honeypot — real users never fill this
) -> HTMLResponse:
    values = {"name": name, "email": email, "message": message}

    # Honeypot: silently accept-and-drop so bots get no signal.
    if website.strip():
        return _render_form(request, sent=True)

    try:
        submission = ContactSubmission(name=name, email=email, message=message)
    except ValidationError as exc:
        return _render_form(
            request, values=values, errors=ContactSubmission.field_errors(exc)
        )

    settings = get_settings()
    try:
        send_contact_message(
            settings,
            name=submission.name,
            sender_email=submission.email,
            message=submission.message,
        )
    except EmailError:
        # Graceful fallback (§6.1): never a 500 — offer the direct address.
        return _render_form(
            request,
            values=values,
            flash=(
                "Something went wrong sending your message — you can also reach "
                f"me directly at {settings.contact_email}."
            ),
        )

    return _render_form(request, sent=True)
