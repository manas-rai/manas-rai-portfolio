#!/usr/bin/env bash
# Regenerate static/resume.pdf from content/resume.yaml.
# The printable resume is rendered by the site build to dist/resume/print/;
# this prints that page to PDF with headless Chrome. Run after editing the
# resume, then commit the updated static/resume.pdf.
set -euo pipefail
cd "$(dirname "$0")/.."

uv run python -m app.build >/dev/null

CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
PAGE="file://$PWD/dist/resume/print/index.html"

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$PWD/static/resume.pdf" "$PAGE" >/dev/null 2>&1

echo "Wrote static/resume.pdf"
