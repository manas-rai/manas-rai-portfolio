# manas-rai-portfolio

Personal portfolio site — projects, blog, resume, and contact — statically
generated from Markdown and YAML content and hosted on **Cloudflare Pages**.
No database, no server: the Jinja2 templates are rendered once at build time,
and the only dynamic piece is the contact form, which posts to a tiny
Cloudflare Pages Function.

See [`docs/design.md`](docs/design.md) for the full solution design.

## Stack

Jinja2 (build-time rendering) · Markdown (posts) + YAML (projects/resume) ·
`nh3` sanitization · `uv` for dependencies · Cloudflare Pages (hosting +
contact Function).

## Local development

```bash
uv sync                        # install dependencies
uv run python -m app.build     # render the site into dist/  (--drafts to include drafts)
python -m http.server -d dist  # preview at http://127.0.0.1:8000
```

To exercise the contact form locally, run the Pages dev server instead (it
serves `dist/` *and* the Function):

```bash
cp .dev.vars.example .dev.vars   # add your Resend key (never commit .dev.vars)
npx wrangler pages dev dist
```

Content is parsed once per build; a malformed post fails the build rather than
a live request. Drafts (`draft: true` in frontmatter) are excluded unless you
pass `--drafts`.

## Tests & linting

```bash
uv run pytest
uv run ruff check .
```

## Content workflow

- **Projects**: edit `content/projects.yaml`.
- **Blog posts**: add a Markdown file to `content/posts/` with YAML frontmatter
  (`title`, `date`, `summary`, optional `tags`, `draft`). Commit and push.
- **Resume**: replace `static/resume.pdf`; keep `content/resume.yaml` in sync.

Pushing to `main` rebuilds and publishes the site automatically.

## Deployment

The [`deploy` workflow](.github/workflows/deploy.yml) builds `dist/` and
publishes it (plus the `functions/` directory) to Cloudflare Pages on every
push to `main`. Pull requests run tests + a build check only.

### One-time setup

1. **Cloudflare account** (free plan is enough — unlimited static bandwidth).
2. **API token**: dashboard → My Profile → API Tokens → Create Token → use the
   "Edit Cloudflare Workers" template or a custom token with **Pages: Edit**
   permission. Also note your **Account ID** (dashboard → Workers & Pages →
   right sidebar).
3. **Repo secrets** (Settings → Secrets and variables → Actions):
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
4. **First deploy** creates the Pages project, or create it up front:
   `npx wrangler pages project create manas-rai-portfolio --production-branch=main`.
5. **Contact-form env vars** (Pages project → Settings → Environment
   variables, Production): `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_TO`.
   Until they're set the form fails gracefully with a mailto fallback.

### Custom domain

Pages project → **Custom domains** → add your domain. If the domain's DNS is
on Cloudflare (free), the CNAME and TLS certificate are provisioned
automatically.

### Security posture

- Static pages: no server, no sessions, no database — nothing to break into.
  `_headers` (written by the build) sets a strict same-origin
  Content-Security-Policy, `X-Frame-Options: DENY`, `nosniff`, and HSTS.
- Post/`projects.yaml` HTML is sanitized with `nh3` at build time.
- The contact Function validates and length-caps every field, drops honeypot
  submissions, rejects cross-origin posts and oversized bodies, and sends
  plain-text email through Resend's JSON API (no header/HTML injection).
  Secrets live only in the Pages project environment.
- Optional hardening: add a Cloudflare **rate-limiting rule** on
  `/api/contact` (one rule is included in the free plan), and/or Turnstile.
