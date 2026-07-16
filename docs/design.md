# Solution Design: Personal Portfolio Website

**Author:** Manas Rai
**Version:** 1.2
**Date:** July 2026

> **Changelog — v1.2:** Moved hosting from a single-container host (Render) to AWS
> Lambda + CloudFront (§3, §7, §7.1, §8, §9); the ~1s Lambda cold start removes the
> free-tier idle-spin-down 404s. Internal links are now root-relative so navigation
> works behind CloudFront's host rewrite.
>
> **Changelog — v1.1:** Incorporated four fixes from design review: (1) contact-form
> availability, (2) Markdown rendering security policy, (3) startup-time content
> indexing, (4) error/empty-state handling. See §7.1, §4.2, §4.5, and §6.1.

---

## 1. Overview

A personal portfolio site presenting a full personal brand: home/intro, projects, blog, resume, and contact. Built on FastAPI (matching existing stack expertise) with server-rendered Jinja2 templates and a flat-file content store — no database required for v1.

## 2. Goals & Non-Goals

**Goals**
- Present projects (RegLens, Cloud Waste Hunter, CostTracker, DevFlow Kit) with clear writeups and links
- Support a blog authored in Markdown, versioned in git
- Serve an on-page resume plus a downloadable PDF
- Provide a working contact form without third-party form-builder lock-in
- Deploy cheaply, with a custom domain, and redeploy automatically on git push

**Non-goals (v1)**
- No user accounts, comments, or admin UI
- No CMS or database-backed content editing
- No analytics dashboards beyond a lightweight, privacy-respecting tracker (optional, later)

## 3. Architecture

```
Browser
   |
   v
CloudFront (CDN, TLS, caches /static/*)
   |  (Origin Access Control — SigV4-signed)
   v
Lambda Function URL (IAM auth)
   |
   v
FastAPI application (Mangum ASGI adapter)
   |-- Routing (/, /projects, /blog, /resume, /contact, /healthz)
   |-- Jinja2 templates (HTML rendering)
   |-- Content index (built once at cold start from Markdown posts + project config)
   +-- Contact handler --> Email service (SMTP / Resend), external
```

(See the architecture diagram shared above for the visual version of this.)

## 4. Component Breakdown

### 4.1 Web layer — FastAPI + Jinja2
- FastAPI serves both HTML pages (via `Jinja2Templates`) and any small JSON endpoints (e.g. project data used for a filterable grid).
- Routes are grouped with `APIRouter` per section: `routes/home.py`, `routes/projects.py`, `routes/blog.py`, `routes/contact.py`.
- Static assets (CSS, images, resume PDF) served via `StaticFiles` mount at `/static`.

### 4.2 Content layer
- **Projects**: a single `content/projects.yaml` (or `.json`) listing each project with title, summary, tech stack, GitHub link, and optional live-demo link. No database — this file is the source of truth and is easy to update via git.
- **Blog posts**: individual Markdown files in `content/posts/`, each with YAML frontmatter (`title`, `date`, `tags`, `summary`, optional `draft`). Parsed using `python-frontmatter` + `markdown`/`mistune`.
- This keeps content editing to "write a `.md` file, commit, push" — no admin panel to build or secure.

**Markdown rendering security policy (fix #2).**
Rendered Markdown produces raw HTML that is injected into templates with Jinja's
`| safe` filter, which disables autoescaping for that content. Blog posts are
**git-authored by the site owner only** — there is no user-submitted Markdown — so
the practical XSS risk is low. Regardless, the pipeline sanitizes rendered post HTML
through `nh3` (Rust `ammonia` bindings) with an allowlist of tags/attributes before it
reaches a template. This is a defense-in-depth measure: it costs almost nothing at
startup (see §4.5, rendering happens once) and guarantees a compromised or careless
commit can't inject script. Any content requiring tags outside the allowlist is an
explicit, reviewed change to the allowlist, not a silent bypass.

### 4.3 Contact form
- A plain HTML form posts to `/contact` (FastAPI endpoint).
- Server validates input (Pydantic model), sends the message via SMTP or a transactional email API (e.g. Resend, Postmark).
- Basic spam mitigation: honeypot field + simple rate limiting (`slowapi`).
- **Note:** `slowapi`'s default limiter is per-process and in-memory. On a single
  free-tier container this is fine, but the limit state resets on every cold start and
  redeploy and would not be shared across replicas if the app is ever scaled out. This
  is an accepted v1 limitation; the honeypot is the more durable line of defense.
- Failure handling for a downed email service is specified in §6.1.

### 4.4 Resume
- Resume content lives as structured data (reused for the on-page `/resume` view) plus a static PDF in `/static/resume.pdf` for direct download.
- **Canonical source:** the structured data is authoritative for the on-page view;
  the PDF is maintained separately and is authoritative for the download. These are two
  sources of truth and *will* drift if edited carelessly — updating one without the
  other is the failure mode to watch. Auto-generating the PDF from the structured data
  is deferred (see §10) as over-engineering for v1; until then, treat "update both" as
  a manual checklist item on any resume change.

### 4.5 Content index — built at startup (fix #3)
Because the container rebuilds and redeploys on every git push, all content is
**immutable for the lifetime of a running process**. The app therefore parses content
**once at application startup** (FastAPI lifespan/startup handler) into an in-memory
index, rather than re-reading and re-parsing files on each request:

- Parse `projects.yaml` and every file in `content/posts/` a single time.
- Build lookup structures: `slug -> Post`, `tag -> [Post]`, and a date-sorted list for
  the blog listing and pagination.
- Render (and sanitize, per §4.2) each post's HTML once and cache it on the index.
- **Fail fast:** malformed frontmatter or an unparseable file raises at boot, so a bad
  commit fails the deploy immediately instead of surfacing as a 500 on a live request.
- Posts with `draft: true` in frontmatter are excluded from the index in production
  (see §10 note on draft handling).

This removes per-request disk I/O and Markdown parsing, makes tag filtering and
pagination trivial in-memory operations, and turns content errors into deploy-time
failures rather than runtime ones.

## 5. Directory Structure

```
portfolio/
├── app/
│   ├── main.py
│   ├── routes/
│   │   ├── home.py
│   │   ├── projects.py
│   │   ├── blog.py
│   │   ├── resume.py
│   │   ├── contact.py
│   │   └── health.py              # /healthz for keep-alive + platform checks
│   ├── services/
│   │   ├── content_loader.py      # builds the startup content index
│   │   └── email_sender.py
│   └── templates/
│       ├── base.html
│       ├── home.html
│       ├── projects.html
│       ├── blog_list.html
│       ├── blog_post.html
│       ├── resume.html
│       ├── contact.html
│       └── errors/
│           ├── 404.html
│           └── 500.html
├── content/
│   ├── projects.yaml
│   └── posts/
│       └── 2026-07-16-example-post.md
├── static/
│   ├── css/
│   ├── images/
│   └── resume.pdf
├── pyproject.toml                 # uv-managed (see §8)
├── uv.lock
├── Dockerfile
└── README.md
```

## 6. Routing / Page Design

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Home: intro, tagline, featured projects |
| `/projects` | GET | Full project list, filterable by tag/tech |
| `/blog` | GET | Blog post list, paginated |
| `/blog/{slug}` | GET | Individual blog post |
| `/resume` | GET | On-page resume + PDF download link |
| `/contact` | GET, POST | Contact form + submission handler |
| `/healthz` | GET | Liveness check for keep-alive ping and platform health checks |

### 6.1 Error & empty states (fix #4)
Happy paths are only half the design; these states are what make the site feel
finished, and each has an explicit template/behavior:

- **`/blog/{slug}` unknown slug** → return HTTP 404 rendered with `errors/404.html`
  (branded page with a link back to the blog index), never a stack trace. Backed by a
  custom FastAPI exception handler for `HTTPException` 404.
- **Empty blog list** (`/blog` with no published posts) → render `blog_list.html` with a
  friendly "no posts yet" empty state rather than a blank page.
- **Empty/malformed project list** → `/projects` degrades to an empty-state message; a
  malformed `projects.yaml` fails at startup (§4.5), not at request time.
- **Contact POST — email service failure** → catch the send error, re-render
  `contact.html` with the user's input preserved and a graceful message ("Something
  went wrong sending your message — you can also reach me directly at <email>"),
  returning HTTP 200 (form re-render) rather than a 500. The direct-email fallback
  ensures a failed send never costs a real contact.
- **Contact POST — validation error** → re-render the form with field-level errors and
  the submitted values intact.
- **Unhandled 500** → generic branded `errors/500.html` via a global exception handler;
  no framework stack traces leak to users in production.

## 7. Deployment Architecture

- **Serverless** on **AWS Lambda** (container image, x86_64) fronted by
  **CloudFront**, defined as infrastructure-as-code in `template.yaml` (AWS SAM).
- **Origin security**: the Lambda **Function URL uses IAM auth** and is reachable only
  through CloudFront via **Origin Access Control** (SigV4-signed requests). The raw
  `*.lambda-url` host returns 403 to direct access.
- **TLS/CDN**: CloudFront terminates HTTPS and caches `/static/*` at the edge; dynamic
  pages are not cached.
- **Domain**: custom domain (e.g. `manasrai.dev`) via an ACM certificate (in
  `us-east-1`) plus a CloudFront alias, with DNS pointed at the distribution.
- **CI/deploy**: `sam build && sam deploy`; a GitHub Actions workflow can run
  linting/tests on push.

### 7.1 Availability & the contact form (fix #1)
The single most conversion-critical path on the site is the contact form — it's what a
recruiter reaches *after* reading the resume, so it must respond immediately.

The serverless design keeps it warm enough for that: **Lambda cold starts are ~1s**
(vs the 30–60s spin-up of an idle free-tier container host), and warm invocations are
single-digit milliseconds. There is no idle-spin-down "asleep" state that returns
routing errors — the earlier free-tier host surfaced idle spin-down as intermittent
`x-render-routing: no-server` 404s on navigation, which this architecture removes.

If sub-second cold starts ever need to become zero, **Provisioned Concurrency** on the
Lambda is the lever — but at portfolio traffic the ~1s cold start is not worth paying
to eliminate.

## 8. Tech Stack Summary

| Layer | Choice |
|---|---|
| Backend framework | FastAPI |
| Templating | Jinja2 (server-rendered; chosen over Next.js/React for zero build step, single-language deploy, and simplest hosting for a content site) |
| Content format | Markdown (posts) + YAML (projects) |
| HTML sanitization | `nh3` (ammonia) for rendered post HTML |
| Email | SMTP or Resend/Postmark API |
| Package manager | `uv` (`pyproject.toml` + `uv.lock`) |
| ASGI-to-Lambda | Mangum |
| Hosting | AWS Lambda (x86_64) + CloudFront, via SAM (`template.yaml`) — see §7 |
| Domain/DNS | Custom domain via ACM cert + CloudFront alias |

## 9. Security Considerations

- Sanitize/escape all user-submitted contact form fields before including them in emails.
- Sanitize rendered blog-post HTML via `nh3` before templating (see §4.2).
- Rate-limit the `/contact` endpoint to prevent spam/abuse (per-process limitation noted in §4.3).
- Serve over HTTPS (terminated at CloudFront); the Lambda origin is IAM-authed and
  reachable only via CloudFront (Origin Access Control).
- No secrets (SMTP credentials, API keys) committed to git — use environment variables.

## 10. Future Enhancements

- Move project/post content into a lightweight database if the content volume grows significantly.
- Add a minimal admin view (auth-gated) for editing content without git access.
- Add privacy-respecting analytics (e.g. Plausible) to track visits.
- Add an OG-image generator for blog posts (dynamic social preview cards).
- Auto-generate the resume PDF from the structured resume data to eliminate the two-source drift noted in §4.4.
- Optionally expose a small public API (`/api/projects`) so other tools (like your agent projects) can pull your project list programmatically.
