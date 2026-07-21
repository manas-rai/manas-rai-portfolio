# Solution Design: Personal Portfolio Website

**Author:** Manas Rai
**Version:** 2.1
**Date:** July 2026

> **Changelog — v2.1:** Hosting moved from Cloudflare Pages to **GitHub Pages**
> at the free custom domain **manasrai.is-a.dev**. Cloudflare cannot attach a
> subdomain whose parent zone lives in another Cloudflare account (error 1014
> "CNAME Cross-User Banned"); GitHub Pages attaches it cleanly. The contact
> form (and its Pages Function) is replaced by a static contact card — direct
> email/LinkedIn/GitHub links, no backend at all. The CSP now ships as a
> `<meta>` tag since GitHub Pages cannot set response headers.
>
> **Changelog — v2.0:** Replaced the server architecture entirely. The site is now
> **statically generated at build time** (Jinja2 → HTML) and hosted on **Cloudflare
> Pages**; the FastAPI/Lambda/CloudFront stack is removed (§3, §7, §8). The contact
> form — the one dynamic piece — moved to a Cloudflare Pages Function (§4.3).
> Motivation: the AWS OAC/IAM origin wiring caused repeated 403 incidents (PRs
> #8–#13) for no benefit at this traffic level; static hosting has zero cold start,
> unlimited free bandwidth, native custom-domain TLS, and a far smaller attack
> surface (§9).
>
> **Changelog — v1.2:** Moved hosting from Render to AWS Lambda + CloudFront.
>
> **Changelog — v1.1:** Incorporated four fixes from design review: (1) contact-form
> availability, (2) Markdown rendering security policy, (3) content indexing,
> (4) error/empty-state handling.

---

## 1. Overview

A personal portfolio site presenting a full personal brand: home/intro, projects,
blog, resume, and contact. Content is flat files (Markdown + YAML) versioned in git;
a small Python build script renders it through Jinja2 templates into a fully static
site served by GitHub Pages. No database, no application server, no server-side
code of any kind.

## 2. Goals & Non-Goals

**Goals**
- Present projects (RegLens, Cloud Waste Hunter, CostTracker, DevFlow Kit) with clear writeups and links
- Support a blog authored in Markdown, versioned in git
- Serve an on-page resume plus a downloadable PDF
- Provide a working contact form without third-party form-builder lock-in
- Deploy free, with a custom domain, and redeploy automatically on git push
- No cold starts — every page is a static file served from a CDN edge

**Non-goals (v2)**
- No user accounts, comments, or admin UI
- No CMS or database-backed content editing
- No analytics dashboards beyond a lightweight, privacy-respecting tracker (optional, later)

## 3. Architecture

```
git push to main
   |
   v
GitHub Actions (ci.yml): ruff + pytest, then `python -m app.build`
   |            (Jinja2 templates + content/ --> dist/ static HTML)
   v
actions/deploy-pages  -->  GitHub Pages
                              serving https://manasrai.is-a.dev
                              (is-a.dev CNAME -> manas-rai.github.io, auto-TLS)
```

Everything a visitor sees is a pre-rendered file. There is no server-side code
at all — contact happens over direct email/LinkedIn links.

## 4. Component Breakdown

### 4.1 Build layer — Jinja2 static generation (`app/build.py`)
- `python -m app.build` renders every page into `dist/`: home, project list plus one
  page per tech filter, blog list plus per-tag and per-page variants, each post,
  resume, contact, and `404.html`.
- Filter/tag pages are **pre-rendered as real paths** (`/projects/tech/python/`,
  `/blog/tag/meta/`) because a static host cannot vary on query strings. Slugs are
  generated with a collision check that fails the build.
- Templates receive a `path_for()` helper mirroring the old route names, so the
  templates stayed almost unchanged through the migration.
- Static assets are copied to `dist/static/`; a `_headers` file (security headers,
  §9) is written alongside.

### 4.2 Content layer
- **Projects**: a single `content/projects.yaml` listing each project with title,
  summary, tech stack, GitHub link, and optional live-demo link.
- **Blog posts**: individual Markdown files in `content/posts/`, each with YAML
  frontmatter (`title`, `date`, `tags`, `summary`, optional `draft`). Parsed using
  `python-frontmatter` + `markdown`.
- Content editing remains "write a `.md` file, commit, push".

**Markdown rendering security policy (fix #2).**
Rendered Markdown is injected with Jinja's `| safe` filter. Posts are git-authored
by the site owner only, but as defense-in-depth the pipeline still sanitizes
rendered HTML through `nh3` with a tag/attribute allowlist before it reaches a
template. Widening the allowlist is an explicit, reviewed change. Sanitization now
happens **once at build time**, so a compromised or careless commit can't ship
script to visitors.

### 4.3 Contact — static contact card (no backend)
- `/contact/` is a pre-rendered page offering direct channels: a `mailto:`
  button, LinkedIn, and GitHub links.
- There is deliberately **no form**: GitHub Pages runs no server code, and a
  form would require either a third-party form service or a serverless
  endpoint elsewhere. Email delivery, credentials, spam mitigation, and
  failure handling are all eliminated as concerns rather than solved.
- If a form is ever wanted, a static-form service (e.g. Formspree) can be
  wired into the page without changing hosts.

### 4.4 Resume
- Structured data in `content/resume.yaml` drives the on-page `/resume/` view; the
  downloadable PDF at `/static/resume.pdf` is maintained separately. Two sources of
  truth — "update both" remains a manual checklist item on any resume change
  (auto-generation deferred, §10).

### 4.5 Content index — built at build time (fix #3)
The v1.1 startup-time index survives intact as the build-time index: one parse of
all content into lookup structures (`slug -> Post`, `tag -> [Post]`, date-sorted
lists), post HTML rendered and sanitized once. **Fail fast** got stronger: a
malformed file now fails the *build* in CI, so a bad commit can never even deploy,
let alone 500. Drafts (`draft: true`) are excluded unless `--drafts` is passed
locally.

## 5. Directory Structure

```
portfolio/
├── app/
│   ├── build.py                   # static site generator (python -m app.build)
│   ├── config.py                  # paths + site constants
│   ├── services/
│   │   └── content_loader.py      # builds the content index at build time
│   └── templates/
│       ├── base.html
│       ├── home.html
│       ├── projects.html
│       ├── blog_list.html
│       ├── blog_post.html
│       ├── resume.html
│       ├── contact.html
│       └── errors/404.html
├── content/
│   ├── projects.yaml
│   ├── resume.yaml
│   ├── posts/
│   │   └── 2026-07-16-hello-world.md
│   └── case-studies/                  # rich per-project write-ups (Markdown
│       └── devflow-kit.md             # + an inline build-time SVG diagram)
├── static/
│   ├── css/  fonts/  images/  resume.pdf
├── dist/                          # build output (gitignored, deployed)
├── pyproject.toml                 # uv-managed
└── README.md
```

## 6. Routing / Page Design

| Path | Kind | Purpose |
|---|---|---|
| `/` | static | Home: intro, tagline, featured projects |
| `/projects/`, `/projects/tech/<slug>/` | static | Project list, per-tech filter pages |
| `/blog/`, `/blog/tag/<slug>/`, `.../page/N/` | static | Blog list, per-tag + pagination pages |
| `/blog/<slug>/` | static | Individual blog post |
| `/resume/` | static | On-page resume + PDF download link |
| `/contact/` | static | Contact card — email, LinkedIn, GitHub |

(`/healthz` is gone — there is no server to health-check; availability is
GitHub Pages' problem.)

### 6.1 Error & empty states (fix #4)
- **Unknown path** → GitHub Pages serves the branded `404.html` automatically.
- **Empty blog/project lists** → friendly empty-state copy, rendered at build time.
- **Malformed content** → fails the CI build; a broken page can never go live.
- **Contact** → direct channels only; there is no submission flow to fail. A
  down email provider is the visitor's mail client's problem, not the site's.
- **500s** — no server-rendered pages exist, so the class of unhandled template/app
  exceptions at request time is gone by construction.

## 7. Deployment Architecture

- **GitHub Pages** (free for public repos): static hosting with a global CDN,
  custom domain + automatic Let's Encrypt TLS, soft 100 GB/month bandwidth —
  far beyond portfolio traffic.
- **CI/deploy**: the `ci` workflow runs ruff + pytest + build on every push/PR;
  on `main` the `deploy-pages` job publishes `dist/` via
  `actions/upload-pages-artifact` + `actions/deploy-pages` (workflow mode — no
  Jekyll, the artifact is served as-is). No deploy credentials exist anywhere:
  the workflow's own OIDC token is the auth.
- **Domain**: `manasrai.is-a.dev` — a free community subdomain from
  [is-a.dev](https://is-a.dev), defined as a JSON file in the public
  `is-a-dev/register` repo with `CNAME manas-rai.github.io`; the repo's Pages
  config sets it as the custom domain. Constraint that forced this design: the
  subdomain cannot attach to Cloudflare Pages because its parent zone lives in
  a different Cloudflare account (error 1014, "CNAME Cross-User Banned").
- **Availability:** static files from a CDN — zero cold start on the
  conversion-critical path (recruiter → resume → contact).

## 8. Tech Stack Summary

| Layer | Choice |
|---|---|
| Site generation | Python + Jinja2 (`app/build.py`), run in CI |
| Content format | Markdown (posts) + YAML (projects/resume) |
| HTML sanitization | `nh3` (ammonia) at build time |
| Contact | Static card — mailto / LinkedIn / GitHub links, no backend |
| Package manager | `uv` (`pyproject.toml` + `uv.lock`) |
| Hosting | GitHub Pages (workflow deploys) — see §7 |
| Domain/DNS | manasrai.is-a.dev (is-a.dev registry, CNAME → github.io, auto-TLS) |

## 9. Security Considerations

The static architecture shrinks the attack surface to the CDN itself, which is
GitHub's responsibility:

- **CSP as a `<meta>` tag on every page:** strict same-origin policy (no inline
  script/style, no third-party loads), so an injected tag has nothing it is
  allowed to load or execute. GitHub Pages cannot set response headers, so
  header-only protections (`X-Frame-Options`/`frame-ancestors`, HSTS,
  `nosniff`) do not apply — an accepted trade-off of static-only hosting;
  github.io itself is HSTS-preloaded and Pages enforces HTTPS.
- **No server, no sessions, no database, no endpoints** — SQLi, session
  hijacking, dependency RCE-at-request-time, injection via form input, and
  stack-trace leakage are eliminated by construction.
- Blog HTML sanitized via `nh3` at build time (§4.2).
- **No secrets exist anywhere** — not in the repo, not in CI, not in any host.

## 10. Future Enhancements

- Visual redesign (typography system, dark mode, responsive card grid, OG/social
  meta tags) — reviewed and queued separately.
- Add privacy-respecting analytics (e.g. Plausible, or Cloudflare Web Analytics,
  which is free and cookieless).
- Add an OG-image generator for blog posts (dynamic social preview cards).
- Auto-generate the resume PDF from the structured resume data to eliminate the
  two-source drift noted in §4.4.
- Turnstile on the contact form if honeypot + rate limiting ever proves
  insufficient.
