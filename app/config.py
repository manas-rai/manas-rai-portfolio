from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
DIST_DIR = BASE_DIR / "dist"

SITE_NAME = "Manas Rai"
SITE_TAGLINE = "Engineer — building useful software."
CONTACT_EMAIL = "rai.manas12@gmail.com"
