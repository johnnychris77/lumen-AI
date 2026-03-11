# LumenAI Deployment Baseline

## Purpose
This document defines the minimum deployment baseline for running LumenAI in a repeatable staging or investor-demo environment.

## Current Architecture
LumenAI runs as a Docker Compose stack with:

- FastAPI API
- PostgreSQL database
- Redis
- RQ worker
- Nginx edge proxy

## Required Environment Variables
Create `backend/.env` from `backend/.env.example`.

Required values:

- `DATABASE_URL`
- `REDIS_URL`
- `QUEUE_BACKEND`
- `RESULT_MODE`
- `LUMENAI_JWT_SECRET`
- `LUMENAI_DATA_DIR`

Optional:

- `LUMENAI_MODEL_PATH`

## Startup Procedure
```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
cd ~/lumen-AI

cat > backend/.env.example <<'EOF'
# LumenAI environment example

# Database
DATABASE_URL=postgresql+psycopg2://lumen:lumen@db:5432/lumenai

# Queue / Redis
REDIS_URL=redis://redis:6379/0
QUEUE_BACKEND=rq

# Result handling
RESULT_MODE=advanced

# Security
LUMENAI_JWT_SECRET=replace-with-strong-secret

# Data paths
LUMENAI_DATA_DIR=/data

# Optional model path
LUMENAI_MODEL_PATH=
