# Solution Design: Personal Portfolio Website

**Author:** Manas Rai
**Version:** 2.0
**Date:** July 2026

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
site. The only server-side code is a ~100-line Cloudflare Pages Function backing the
contact form. No database, no application server.

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
GitHub Actions: ruff + pytest, then `python -m app.build`
   |            (Jinja2 templates + content/ --> dist/ static HTML)
   v
wrangler pages deploy dist  -->  Cloudflare Pages
                                    |-- static pages + assets (edge-cached, free bandwidth)
                                    +-- /api/contact  (Pages Function, JS)
                                           |
                                           v
                                        Resend API --> owner's inbox
```

Everything a visitor sees is a pre-rendered file; the Function is invoked only on
contact-form submission.

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

### 4.3 Contact form — Cloudflare Pages Function (`functions/api/contact.js`)
- The static `/contact/` page posts to `/api/contact`.
- **Progressive enhancement:** with JS (`static/js/contact.js`) the form submits via
  `fetch` and shows inline success/error; without JS the browser posts the form and
  the Function 303-redirects to the pre-rendered `/contact/sent/` page.
- The Function validates and length-caps every field, checks the honeypot
  (accept-and-drop so bots get no signal), rejects cross-origin posts and oversized
  bodies, and delivers via **Resend's JSON API as plain text** — user input can
  neither inject email headers nor render as HTML in the inbox.
- Credentials (`RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_TO`) live in the Pages project
  environment, never in the repo.
- Rate limiting: a Cloudflare rate-limiting rule on `/api/contact` (one rule free)
  is the durable option; the honeypot plus validation is the baseline. (Replaces the
  old in-process `slowapi` limiter, which reset on every cold start anyway.)
- Email-service failure handling is specified in §6.1.

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
├── functions/
│   └── api/contact.js             # Cloudflare Pages Function (contact form)
├── content/
│   ├── projects.yaml
│   ├── resume.yaml
│   └── posts/
│       └── 2026-07-16-hello-world.md
├── static/
│   ├── css/  images/  js/contact.js  resume.pdf
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
| `/contact/`, `/contact/sent/` | static | Contact form, no-JS success page |
| `/api/contact` | Function | POST-only submission handler |

(`/healthz` is gone — there is no server to health-check; Pages availability is
Cloudflare's problem.)

### 6.1 Error & empty states (fix #4)
- **Unknown path** → Cloudflare Pages serves the branded `404.html` automatically.
- **Empty blog/project lists** → friendly empty-state copy, rendered at build time.
- **Malformed content** → fails the CI build; a broken page can never go live.
- **Contact POST — email service down/unconfigured** → the Function returns a
  graceful error ("…you can also reach me directly at <email>") shown inline by the
  JS; never a blank 500. The direct-email fallback ensures a failed send never
  costs a real contact.
- **Contact POST — validation error** → per-field messages returned as JSON and
  shown inline; browser-level `required`/`maxlength` catches most before submit.
- **500s** — no server-rendered pages exist, so the class of unhandled template/app
  exceptions at request time is gone by construction.

## 7. Deployment Architecture

- **Cloudflare Pages** (free plan): unlimited static bandwidth/requests, 500
  builds/month (we build in GitHub Actions, so this is irrelevant), custom domains
  with automatic TLS.
- **CI/deploy**: Cloudflare Pages Git integration builds and publishes on every
  push to `main` (build command `python -m app.build`, deps from
  `requirements.txt`, the build image's preinstalled Python — unpinned so no
  toolchain download runs per build) and gives each PR a preview URL. GitHub Actions runs ruff + pytest + build as the merge gate — no
  Cloudflare credentials in GitHub at all.
- **Domain**: add the domain in Pages → Custom domains; with DNS on Cloudflare the
  CNAME + certificate are automatic.
- **Availability (supersedes v1.2 §7.1):** static files from the edge have **zero
  cold start** — the conversion-critical path (recruiter → resume → contact) never
  waits on a container spin-up or Lambda init. Pages Functions run on Workers
  isolates (~0 ms cold start) for the form itself.

## 8. Tech Stack Summary

| Layer | Choice |
|---|---|
| Site generation | Python + Jinja2 (`app/build.py`), run in CI |
| Content format | Markdown (posts) + YAML (projects/resume) |
| HTML sanitization | `nh3` (ammonia) at build time |
| Contact endpoint | Cloudflare Pages Function (JS) |
| Email | Resend HTTP API |
| Package manager | `uv` (`pyproject.toml` + `uv.lock`) |
| Hosting | Cloudflare Pages (free plan) — see §7 |
| Domain/DNS | Cloudflare DNS + Pages custom domain (auto-TLS) |

## 9. Security Considerations

The static architecture shrinks the attack surface to (a) the CDN, which is
Cloudflare's responsibility, and (b) one POST endpoint:

- **`_headers` on every response:** strict same-origin Content-Security-Policy (no
  inline script/style, no third-party loads), `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, HSTS.
- **No server, no sessions, no database** — SQLi, session hijacking, dependency
  RCE-at-request-time, and stack-trace leakage are eliminated by construction.
- Blog HTML sanitized via `nh3` at build time (§4.2).
- Contact Function: field validation + length caps, honeypot, same-origin check,
  body-size limit, plain-text email via JSON API (no header/HTML injection),
  secrets only in the Pages environment. Optional: Cloudflare rate-limiting rule
  and/or Turnstile on `/api/contact`.
- No secrets committed to git; `.dev.vars` (local Function secrets) is gitignored.

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
