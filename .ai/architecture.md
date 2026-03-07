# LumenAI Architecture

## Runtime Components
- API
- Worker
- Redis
- Postgres
- Object storage
- Nginx edge
- Prometheus
- Grafana

## Core Flow
1. User uploads an image.
2. API creates an inspection row with queued status.
3. Worker consumes queued job.
4. Inference runs.
5. DB row updated with outputs.
6. History/report endpoints expose results.
7. Artifacts stored and linked.

## Rules
- No silent sqlite fallback.
- API and worker must use the same DB and queue.
- No container-only code may exist outside the repo source of truth.
- All runtime config must be explicit.
