# Task: db-startup-readiness

## Owning Agent
devops

## Problem
The API container tries to connect to Postgres before the DB is ready, causing startup failure with connection refused.

## Goal
Make API startup resilient so the container waits for Postgres readiness before running app initialization.

## Scope
- docker-compose.prod.yml
- API startup/readiness behavior
- optional DB wait script or retry loop
- container dependency health strategy

## Out of Scope
- frontend changes
- model logic
- auth changes

## Acceptance Criteria
- [ ] API does not fail permanently if Postgres is still starting
- [ ] DB service has a readiness strategy
- [ ] API starts successfully after DB becomes available
- [ ] worker still starts successfully
- [ ] docker compose up -d --build results in a usable API
- [ ] login endpoint responds
- [ ] inspect flow can be tested after boot

## Validation Plan
- docker compose -f docker-compose.prod.yml down -v
- docker compose -f docker-compose.prod.yml up -d --build
- docker compose -f docker-compose.prod.yml ps
- docker logs --tail=120 lumen-ai-db-1
- docker logs --tail=120 lumen-ai-api-1
- curl -i http://localhost:8000/docs

## Release Impact
runtime-sensitive
