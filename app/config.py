from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"


class Settings(BaseSettings):
    """Runtime configuration, sourced from environment variables.

    Secrets (SMTP/Resend credentials) must never be committed; they are read
    from the environment in production per the design doc's security section.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    site_name: str = "Manas Rai"
    site_tagline: str = "Engineer — building useful software."
    contact_email: str = "rai.manas12@gmail.com"

    # Set to True in production so drafts are excluded from the content index.
    is_production: bool = False

    # Email delivery. If resend_api_key is set, Resend is used; otherwise SMTP.
    resend_api_key: str | None = None
    email_from: str = "portfolio@manasrai.dev"
    email_to: str = "rai.manas12@gmail.com"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
