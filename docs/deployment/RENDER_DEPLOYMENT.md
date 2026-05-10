# Render Deployment Guide

## Recommended Services

- API Web Service
- Worker Background Service
- Managed PostgreSQL
- Redis-compatible service

## API Start Command

uvicorn run_reset_app:app --host 0.0.0.0 --port ${PORT:-8000}

## Health Check

/api/health

## Required Variables

APP_ENV=production
PUBLIC_BASE_URL=https://your-render-service.onrender.com
API_PREFIX=/api
DATABASE_URL=<Render Postgres URL>
REDIS_URL=<Render Redis URL>
ENABLE_DEV_AUTH=false
LUMENAI_JWT_SECRET=<strong-secret>
ENABLE_ENTERPRISE_AUDIT=true
ENABLE_ENTERPRISE_RBAC=true
ALLOWED_ORIGINS=https://your-github-pages-site-url
