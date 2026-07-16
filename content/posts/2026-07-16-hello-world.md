---
title: "Building this site"
date: 2026-07-16
summary: "Why I built my portfolio on FastAPI and flat files instead of a CMS."
tags: [meta, python]
---

Welcome to the first post. This site runs on **FastAPI** with server-rendered
Jinja2 templates and a flat-file content store — no database.

## Why flat files

Every post is a Markdown file with YAML frontmatter, committed to git. Editing
content is just:

```bash
git add content/posts/my-post.md
git commit -m "New post"
git push
```

No admin panel to build or secure, and full version history for free.

## What's next

More writing on the projects I'm working on — RegLens, DevFlow Kit, and the
agent experiments.
