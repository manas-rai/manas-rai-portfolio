from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
DIST_DIR = BASE_DIR / "dist"

SITE_NAME = "Manas Rai"
SITE_TAGLINE = (
    "I build production backend systems and GenAI platforms — RAG pipelines, "
    "multi-agent systems, and the cloud infrastructure behind them."
)
CONTACT_EMAIL = "rai.manas12@gmail.com"
SITE_URL = "https://manas-rai-portfolio.pages.dev"
GITHUB_URL = "https://github.com/manas-rai"
LINKEDIN_URL = "https://www.linkedin.com/in/manas-rai-a84179213"
