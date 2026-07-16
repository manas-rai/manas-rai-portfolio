# manas-rai-portfolio

Personal portfolio site built with FastAPI + Jinja2 — projects, blog, resume, and
contact, all server-rendered from Markdown and YAML content. No database.

See [`docs/design.md`](docs/design.md) for the full solution design.

## Stack

FastAPI · Jinja2 · Markdown (posts) + YAML (projects) · `nh3` sanitization ·
`uv` for dependencies · Docker · Render for hosting.

## Local development

```bash
uv sync                 # install dependencies
cp .env.example .env    # configure (optional for local — contact will fallback)
uv run uvicorn app.main:app --reload
```

The site is then at http://127.0.0.1:8000.

Content is parsed **once at startup** into an in-memory index (design §4.5), so a
malformed post fails the boot rather than a live request. Drafts (`draft: true` in
frontmatter) are shown locally and hidden when `IS_PRODUCTION=true`.

## Tests & linting

```bash
uv run pytest
uv run ruff check .
```

## Content workflow

- **Projects**: edit `content/projects.yaml`.
- **Blog posts**: add a Markdown file to `content/posts/` with YAML frontmatter
  (`title`, `date`, `summary`, optional `tags`, `draft`). Commit and push.
- **Resume**: replace `static/resume.pdf`; keep the on-page `/resume` view in sync.

## Deployment

Deployed on Render from the committed [`render.yaml`](render.yaml) blueprint
(Docker web service, free plan, health check at `/healthz`, auto-deploy on push
to `main`).

### First-time setup

1. **Create the service**: in the Render dashboard → **New → Blueprint** → connect
   this repo. Render reads `render.yaml` and provisions the service.
2. **Set the email secret** (optional): add either `RESEND_API_KEY` or the
   `SMTP_*` variables under the service's **Environment**. Until one is set, the
   contact form fails gracefully rather than sending (design §6.1).
3. **Custom domain** (optional): add it under **Settings → Custom Domains** and
   point DNS at Render.

### Keep-alive (free tier)

The free plan spins down after ~15 min idle (30–60s cold start). The
[`keep-alive` workflow](.github/workflows/keep-alive.yml) pings `/healthz` every
~10 min to mitigate this. To enable it, add a repo **variable** (Settings →
Secrets and variables → Actions → Variables):

```
RENDER_PING_URL = https://<your-service>.onrender.com/healthz
```

A dedicated uptime monitor (e.g. UptimeRobot, 5-min interval) is more reliable
than GitHub's scheduler if cold starts remain a problem. To eliminate them
entirely, switch `plan: free` to `plan: starter` in `render.yaml` (design §7.1).

Verify the image builds and serves locally the same way Render does:

```bash
docker build -t portfolio .
docker run --rm -e PORT=10000 -p 10000:10000 portfolio
# then: curl localhost:10000/healthz
```
