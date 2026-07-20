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

Deploys run through **Cloudflare Pages' Git integration**: Cloudflare clones
the repo, installs `requirements.txt`, runs the build, and publishes `dist/`
(plus the `functions/` directory) on every push to `main` — with a preview URL
for every PR. The [`ci` workflow](.github/workflows/ci.yml) runs lint, tests,
and a build check on GitHub as the merge gate.

### Pages project settings

- **Production branch**: `main`
- **Framework preset**: None
- **Build command**: `python -m app.build`
- **Build output directory**: `dist`

Dependencies are auto-installed from `requirements.txt` (generated from
`uv.lock` — regenerate with
`uv export --no-dev --no-hashes --no-annotate -o requirements.txt` whenever
deps change; CI fails if it drifts). Python version is pinned by
`.python-version`.

### Contact-form env vars

Pages project → Settings → Environment variables (Production):
`RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_TO`. Until they're set the form fails
gracefully with a mailto fallback.

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
