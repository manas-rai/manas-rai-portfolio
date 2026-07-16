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

Containerized via the `Dockerfile` and deployed on Render. Set `RESEND_API_KEY` (or
the `SMTP_*` variables) and `IS_PRODUCTION=true` in the environment. See design §7.1
for the cold-start/availability decision.
