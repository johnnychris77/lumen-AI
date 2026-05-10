# LumenAI Cloud Deployment Plan

## Purpose

Prepare LumenAI for a public or semi-public hosted demo.

## Recommended Path

1. Host the static landing page with GitHub Pages.
2. Deploy the API to Render, Railway, or Fly.io.
3. Use managed PostgreSQL.
4. Use managed Redis.
5. Configure environment variables.
6. Run demo data seeding.
7. Verify the executive dashboard.
8. Capture screenshots.
9. Update public landing page links.

## Current Local Stack

- FastAPI API
- PostgreSQL
- Redis
- Worker service
- Nginx edge service
- Static public demo landing page

## Production Notes

Before public hosting:

- Remove or rotate exposed Slack webhook URLs.
- Remove real SMTP credentials from compose files.
- Set APP_ENV=production.
- Set ENABLE_DEV_AUTH=false or replace with real auth.
- Set PUBLIC_BASE_URL to the public HTTPS URL.
- Restrict ALLOWED_ORIGINS.
- Use managed Postgres and Redis.
- Run the enterprise quality gate before deployment.
