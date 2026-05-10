#!/usr/bin/env bash
set -euo pipefail

HOSTED_BASE_URL="${HOSTED_BASE_URL:-}"

if [[ -z "$HOSTED_BASE_URL" ]]; then
  echo "HOSTED_BASE_URL is required."
  echo
  echo "Example:"
  echo "HOSTED_BASE_URL=https://your-lumenai-api.onrender.com scripts/update-public-demo-links.sh"
  exit 1
fi

HOSTED_BASE_URL="${HOSTED_BASE_URL%/}"

LANDING_PAGE="docs/public-demo/index.html"
LINKS_DOC="docs/public-demo/LIVE_DEMO_LINKS.md"

if [[ ! -f "$LANDING_PAGE" ]]; then
  echo "Missing ${LANDING_PAGE}"
  exit 1
fi

python - <<PY
from pathlib import Path

hosted = "${HOSTED_BASE_URL}"
dashboard = f"{hosted}/api/executive-briefing-dashboard/view"
health = f"{hosted}/api/health"
readiness = f"{hosted}/api/production-readiness/config"

landing = Path("${LANDING_PAGE}")
text = landing.read_text()
text = text.replace("http://127.0.0.1:18011/api/executive-briefing-dashboard/view", dashboard)
landing.write_text(text)

links = Path("${LINKS_DOC}")
if links.exists():
    t = links.read_text()
    t = t.replace("http://127.0.0.1:18011/api/executive-briefing-dashboard/view", dashboard)
    t = t.replace("http://127.0.0.1:18011/api/health", health)
    t = t.replace("http://127.0.0.1:18011/api/production-readiness/config", readiness)
    links.write_text(t)

print("Updated public demo links:")
print(f"- Dashboard: {dashboard}")
print(f"- Health: {health}")
print(f"- Readiness: {readiness}")
PY
