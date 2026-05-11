# Render Deployment Readiness Guard

## Purpose

This readiness guard confirms LumenAI has the required files and local checks before attempting Render deployment.

## Run

scripts/render-readiness-check.sh

Expected result:

RENDER READINESS CHECK PASSED

## What It Checks

- render.yaml exists
- hosted backend quickstart docs exist
- hosted demo validation docs exist
- hosted validation scripts exist
- public demo go-live script exists
- Render blueprint contains expected variables
- local API health endpoint is reachable
- local production readiness endpoint is reachable

## Before Render Deployment

Confirm:

- render.yaml is committed
- no real secrets are committed
- local API health works
- production readiness endpoint works
- demo seed works
- public demo link switch works
- hosted demo validation scripts exist

## After Render Deployment

Set the real hosted backend URL:

export HOSTED_BASE_URL=https://your-real-render-url.onrender.com
export TOKEN=your-demo-token

Validate hosted demo:

scripts/check-hosted-demo.sh

Seed hosted demo:

scripts/seed-hosted-demo.sh

Switch public landing page links:

scripts/public-demo-go-live.sh

## Local Dry Run

Use local backend:

HOSTED_BASE_URL=http://127.0.0.1:18011 scripts/public-demo-go-live.sh
