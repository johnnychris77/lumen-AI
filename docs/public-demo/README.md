# Public Demo Landing Page

## Local Preview

python -m http.server 9094 -d docs/public-demo

Open:

http://127.0.0.1:9094

## Public Demo Go-Live

When a hosted backend URL is available, switch the dashboard links:

HOSTED_BASE_URL=https://your-real-hosted-api-url scripts/public-demo-go-live.sh

Rollback to local links:

scripts/public-demo-rollback-local.sh
