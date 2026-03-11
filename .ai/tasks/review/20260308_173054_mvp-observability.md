# Task: mvp-observability

## Owning Agent
devops

## Problem
LumenAI now has a working async inspection MVP, but it lacks basic observability for API health, queue activity, and processing confidence. That makes debugging, demos, and investor readiness weaker than they should be.

## Goal
Add lightweight MVP observability so operators can verify system health, worker activity, and queue-backed processing status quickly.

## Scope
- API health verification
- Redis/worker visibility
- queue depth visibility
- basic runtime diagnostics endpoint or script
- Docker-based validation workflow
- minimal developer/operator runbook updates if needed

## Out of Scope
- full Prometheus/Grafana stack
- distributed tracing
- production cloud alerting
- frontend redesign

## Acceptance Criteria
- [ ] API health can be checked quickly and consistently
- [ ] worker activity can be verified quickly
- [ ] queue depth can be inspected with a repeatable command or script
- [ ] observability workflow works with current Docker MVP setup
- [ ] documentation or script exists for repeatable operator checks

## Validation Plan
- docker compose -f docker-compose.prod.yml ps
- curl -i http://localhost:8000/docs
- curl -i http://localhost:8080/api/health
- docker logs --tail=120 lumen-ai-api-1
- docker logs --tail=120 lumen-ai-worker-1
- docker exec -i lumen-ai-redis-1 sh -lc 'redis-cli -n 0 LLEN rq:queue:lumenai'
- submit one inspection and verify queue/worker behavior

## Release Impact
minor
