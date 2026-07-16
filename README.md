# manas-rai-portfolio

Personal portfolio site built with FastAPI + Jinja2 — projects, blog, resume, and
contact, all server-rendered from Markdown and YAML content. No database.

See [`docs/design.md`](docs/design.md) for the full solution design.

## Stack

FastAPI · Jinja2 · Markdown (posts) + YAML (projects) · `nh3` sanitization ·
`uv` for dependencies · AWS Lambda + CloudFront (SAM) for hosting.

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

Primary target: **AWS Lambda (container image, arm64) behind CloudFront**, defined
in [`template.yaml`](template.yaml) (AWS SAM). The Lambda Function URL uses IAM auth
and is reachable only through CloudFront via Origin Access Control, so the raw
`*.lambda-url` host returns 403 if hit directly. Cold start is ~1s; cost is ~$0/month
at portfolio traffic (Lambda always-free tier + free Function URL + CloudFront
always-free tier).

### Prerequisites

- AWS account with credentials configured (`aws configure`)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) and Docker

### Deploy

```bash
sam build              # builds the arm64 image from Dockerfile.lambda
sam deploy --guided    # first run: creates the ECR repo, stack, and distribution
# thereafter: sam build && sam deploy
```

`sam deploy` prints two outputs:

- **CloudFrontURL** — the public site (`https://xxxx.cloudfront.net`); serve this.
- **FunctionUrl** — the raw origin (403 by design; not for visitors).

A new CloudFront distribution takes ~5–15 min to finish deploying.

### Email (optional)

Pass one transport at deploy time; until then the contact form fails gracefully
(design §6.1):

```bash
sam deploy --parameter-overrides ResendApiKey=re_xxx
# or: SmtpHost=... SmtpUser=... SmtpPassword=...
```

### Custom domain (optional)

Add an ACM certificate (in `us-east-1`) and an `Aliases` entry to the CloudFront
distribution, then point DNS (CNAME) at the distribution domain.

### Local verification (no deploy)

The Lambda image runs under the bundled runtime emulator:

```bash
docker build -f Dockerfile.lambda -t portfolio-lambda .
docker run --rm -p 9000:8080 portfolio-lambda
# in another shell:
curl -s -XPOST http://localhost:9000/2015-03-31/functions/function/invocations \
  -d '{"version":"2.0","rawPath":"/healthz","requestContext":{"http":{"method":"GET","path":"/healthz"}},"isBase64Encoded":false}'
```
