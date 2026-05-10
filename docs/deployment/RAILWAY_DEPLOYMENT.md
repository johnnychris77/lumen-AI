# Railway Deployment Guide

## Recommended Services

- API service
- Worker service
- PostgreSQL service
- Redis service

## Deploy

railway login
railway link
railway up

## API Start Command

uvicorn run_reset_app:app --host 0.0.0.0 --port ${PORT:-8000}

## Health Check

/api/health

## Required Variables

APP_ENV=production
API_PREFIX=/api
PUBLIC_BASE_URL=https://your-railway-service-url
DATABASE_URL=<Railway Postgres URL>
REDIS_URL=<Railway Redis URL>
ENABLE_DEV_AUTH=false
LUMENAI_JWT_SECRET=<strong-secret>
ENABLE_ENTERPRISE_AUDIT=true
ENABLE_ENTERPRISE_RBAC=true
ALLOWED_ORIGINS=https://your-github-pages-site-url
