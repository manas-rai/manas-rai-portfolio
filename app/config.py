from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
DIST_DIR = BASE_DIR / "dist"

SITE_NAME = "Manas Rai"
# Short role for the <title>/og:title; the long tagline is the meta description.
SITE_ROLE = "Software Engineer · GenAI Engineer"
SITE_TAGLINE = (
    "I build production backend systems and GenAI platforms — RAG pipelines, "
    "multi-agent systems, and the cloud infrastructure behind them."
)
# Hero-only lede — the mechanism voice. SITE_TAGLINE stays keyword-rich for
# meta/OG; this carries personality on the homepage.
SITE_LEDE = (
    "Mechanical engineer by training, systems engineer by trade — I build GenAI "
    "platforms with the same discipline as a tolerance stack-up: nothing ships "
    "until it's measured."
)
CONTACT_EMAIL = "rai.manas12@gmail.com"
# Primary host is GitHub Pages at the custom domain, served at the root. The
# Cloudflare Pages mirror (manas-rai-portfolio.pages.dev) builds from the same
# defaults; its canonical/OG URLs therefore point at the primary domain, which
# is the correct SEO signal. SITE_URL/BASE_PATH remain env-overridable for any
# future subpath host.
SITE_URL = os.environ.get("SITE_URL", "https://manasrai.is-a.dev").rstrip("/")
BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")
GITHUB_URL = "https://github.com/manas-rai"
LINKEDIN_URL = "https://www.linkedin.com/in/manasrai12"
