---
title: "Building this site: a static portfolio with zero servers"
date: 2026-07-16
summary: "Why this portfolio is a statically generated site on a free host — no database, no server, no monthly bill."
tags: [meta, python]
---

This site has no server. Every page you're reading was rendered once, at build
time, from Jinja2 templates and flat Markdown/YAML files — then published as
plain static HTML. No database, no application runtime, no monthly hosting bill.

## Why static

A portfolio is read far more than it's written. The content changes when I ship
a project or write a post — not on every request. So paying for an always-on
server to re-render the same pages over and over is the wrong trade. A build
step that runs once per change, producing files a CDN can serve instantly, fits
the problem better: zero cold starts, nothing to break into, and it's free.

The content lives as flat files in git:

```bash
git add content/posts/my-post.md
git commit -m "New post"
git push
```

Pushing to `main` runs the build in CI and publishes the result. No admin panel
to secure, and full version history for free.

## How it's built

A small Python script walks the content, renders each page through the same
Jinja2 templates, and writes a `dist/` folder:

- **Projects** come from a single YAML file.
- **Posts** are Markdown with YAML frontmatter, rendered to HTML and sanitized
  at build time.
- **Filter and tag pages** are pre-generated as real paths, because a static
  host can't run query-string logic.

A malformed file fails the build rather than a live page — content errors become
deploy-time errors, which is exactly where you want them.

## What's next

More writing on the projects behind this site — RegLens, DevFlow Kit, and the
multi-agent systems I work on day to day.
