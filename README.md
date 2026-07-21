# manas-rai-portfolio

Personal portfolio site — projects, blog, resume, and contact — statically
generated from Markdown and YAML content and hosted on **GitHub Pages** at
**https://manasrai.is-a.dev**. No server, no database: the Jinja2 templates
are rendered once at build time and served as plain files.

See [`docs/design.md`](docs/design.md) for the full solution design.

## Stack

Jinja2 (build-time rendering) · Markdown (posts) + YAML (projects/resume) ·
`nh3` sanitization · `uv` for dependencies · GitHub Pages (hosting) ·
is-a.dev (free custom domain).

## Local development

```bash
uv sync                        # install dependencies
uv run python -m app.build     # render the site into dist/  (--drafts to include drafts)
python -m http.server -d dist  # preview at http://127.0.0.1:8000
```

Content is parsed once per build; a malformed post fails the build rather than
a live page. Drafts (`draft: true` in frontmatter) are excluded unless you
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

The [`ci` workflow](.github/workflows/ci.yml) runs lint + tests + a build
check on every push and PR; on `main` its `deploy-pages` job builds `dist/`
and publishes it to **GitHub Pages** (workflow mode, no Jekyll).

The custom domain **manasrai.is-a.dev** is a free community subdomain from
[is-a.dev](https://is-a.dev), registered via a JSON file in
[is-a-dev/register](https://github.com/is-a-dev/register) whose CNAME points
at `manas-rai.github.io`. GitHub Pages' custom-domain setting (`cname`) is
configured on the repo, and GitHub provisions the TLS certificate
automatically.

### Contact

The contact page is a static card — direct email (`mailto:`), LinkedIn, and
GitHub links. There is deliberately no form backend; if a form is ever wanted,
a static-form service (e.g. Formspree) can be wired into the page without a
server.

### Security posture

- Static files only — no server code, no sessions, no database, nothing to
  break into.
- A strict same-origin Content-Security-Policy ships as a `<meta>` tag on
  every page (GitHub Pages cannot set response headers, so header-only
  protections like `X-Frame-Options` don't apply — an accepted trade-off of
  static-only hosting).
- Post/`projects.yaml` HTML is sanitized with `nh3` at build time.
- No secrets exist anywhere in the pipeline.
