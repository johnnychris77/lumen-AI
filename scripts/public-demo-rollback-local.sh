#!/usr/bin/env bash
set -euo pipefail

LANDING_PAGE="docs/public-demo/index.html"
LINKS_DOC="docs/public-demo/LIVE_DEMO_LINKS.md"

LOCAL_BASE_URL="http://127.0.0.1:18011"
LOCAL_DASHBOARD="${LOCAL_BASE_URL}/api/executive-briefing-dashboard/view"
LOCAL_HEALTH="${LOCAL_BASE_URL}/api/health"
LOCAL_READINESS="${LOCAL_BASE_URL}/api/production-readiness/config"

if [[ ! -f "$LANDING_PAGE" ]]; then
  echo "Missing $LANDING_PAGE"
  exit 1
fi

python - <<PY
from pathlib import Path

landing_page = Path("${LANDING_PAGE}")
links_doc = Path("${LINKS_DOC}")

local_dashboard = "${LOCAL_DASHBOARD}"
local_health = "${LOCAL_HEALTH}"
local_readiness = "${LOCAL_READINESS}"

text = landing_page.read_text()

# Replace any known local or hosted dashboard link back to local.
for marker in [
    "http://127.0.0.1:18011/api/executive-briefing-dashboard/view",
    "http://localhost:18011/api/executive-briefing-dashboard/view",
]:
    text = text.replace(marker, local_dashboard)

landing_page.write_text(text)

if links_doc.exists():
    t = links_doc.read_text()
    for old in [
        "http://127.0.0.1:18011/api/executive-briefing-dashboard/view",
        "http://localhost:18011/api/executive-briefing-dashboard/view",
    ]:
        t = t.replace(old, local_dashboard)

    t = t.replace("http://127.0.0.1:18011/api/health", local_health)
    t = t.replace("http://127.0.0.1:18011/api/production-readiness/config", local_readiness)
    links_doc.write_text(t)

print("Rolled public demo links back to local development.")
print(local_dashboard)
PY
