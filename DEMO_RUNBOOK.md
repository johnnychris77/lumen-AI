# LumenAI One-Command Demo Control Center

## Purpose

This runbook standardizes the local demo workflow so LumenAI can be started, seeded, checked, stopped, and reset with simple commands.

## Commands

Start demo:

scripts/demo-start.sh

Seed demo data:

scripts/demo-seed.sh

Check demo status:

scripts/demo-status.sh

Stop demo:

scripts/demo-stop.sh

Reset local demo database:

scripts/demo-reset.sh

## Default Links

Landing page:

http://127.0.0.1:9092

Executive dashboard:

http://127.0.0.1:18011/api/executive-briefing-dashboard/view

## Notes

If a landing page port is already in use, run:

LANDING_PORT=9093 scripts/demo-start.sh

If the dashboard shows zeros, run:

scripts/demo-seed.sh

Do not run placeholder URLs such as your-render-api-url, PUBLIC_URL, or token placeholders until they are replaced with real values.
