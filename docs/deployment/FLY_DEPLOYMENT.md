# Fly.io Deployment Guide

## Setup

Install flyctl, authenticate, then run:

fly launch --no-deploy
fly deploy

## Required Secrets

APP_ENV=production
ENABLE_DEV_AUTH=false
LUMENAI_JWT_SECRET=<strong-secret>
DATABASE_URL=<postgres-url>
REDIS_URL=<redis-url>
PUBLIC_BASE_URL=https://your-fly-app.fly.dev
ALLOWED_ORIGINS=https://your-github-pages-site-url

## Health Check

/api/health

## Artifact Persistence

For persistent packet exports, mount a volume or use object storage.
