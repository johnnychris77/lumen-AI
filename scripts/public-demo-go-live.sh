#!/usr/bin/env bash
set -euo pipefail

HOSTED_BASE_URL="${HOSTED_BASE_URL:-}"

if [[ -z "$HOSTED_BASE_URL" ]]; then
  echo "HOSTED_BASE_URL is required."
  echo
  echo "Example:"
  echo "HOSTED_BASE_URL=https://your-real-render-url.onrender.com scripts/public-demo-go-live.sh"
  exit 1
fi

HOSTED_BASE_URL="${HOSTED_BASE_URL%/}"

LANDING_PAGE="docs/public-demo/index.html"
LINKS_DOC="docs/public-demo/LIVE_DEMO_LINKS.md"
GO_LIVE_LOG="docs/public-demo/GO_LIVE_LINKS.md"

DASHBOARD_URL="${HOSTED_BASE_URL}/api/executive-briefing-dashboard/view"
HEALTH_URL="${HOSTED_BASE_URL}/api/health"
READINESS_URL="${HOSTED_BASE_URL}/api/production-readiness/config"

if [[ ! -f "$LANDING_PAGE" ]]; then
  echo "Missing $LANDING_PAGE"
  exit 1
fi

echo "==> Validating hosted health endpoint"

if ! curl -fsS "$HEALTH_URL" >/tmp/lumenai_hosted_health.json; then
  echo "Hosted API health check failed:"
  echo "$HEALTH_URL"
  exit 1
fi

cat /tmp/lumenai_hosted_health.json
echo

echo "==> Updating public demo landing page links"

python - <<PY
from pathlib import Path

landing_page = Path("${LANDING_PAGE}")
links_doc = Path("${LINKS_DOC}")
go_live_log = Path("${GO_LIVE_LOG}")

hosted = "${HOSTED_BASE_URL}"
dashboard = "${DASHBOARD_URL}"
health = "${HEALTH_URL}"
readiness = "${READINESS_URL}"

old_dashboard = "http://127.0.0.1:18011/api/executive-briefing-dashboard/view"
old_health = "http://127.0.0.1:18011/api/health"
old_readiness = "http://127.0.0.1:18011/api/production-readiness/config"

text = landing_page.read_text()
text = text.replace(old_dashboard, dashboard)
landing_page.write_text(text)

if links_doc.exists():
    t = links_doc.read_text()
    t = t.replace(old_dashboard, dashboard)
    t = t.replace(old_health, health)
    t = t.replace(old_readiness, readiness)
    links_doc.write_text(t)

go_live_log.write_text(f"""# LumenAI Public Demo Go-Live Links

## Hosted Backend

{hosted}

## Public Dashboard

{dashboard}

## Health

{health}

## Production Readiness

{readiness}

## Rollback

To return to local development links:

scripts/public-demo-rollback-local.sh
""")

print("Updated links:")
print(f"Dashboard: {dashboard}")
print(f"Health: {health}")
print(f"Readiness: {readiness}")
PY

echo
echo "PUBLIC DEMO LINK SWITCH COMPLETE"
