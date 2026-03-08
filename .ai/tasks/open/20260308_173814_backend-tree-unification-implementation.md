# Task: backend-tree-unification-implementation

## Owning Agent
backend

## Problem
LumenAI currently has duplicate backend trees under backend/app and backend/app/app. This has caused repeated runtime import failures and Docker working_dir confusion.

## Goal
Standardize the backend so backend/app is the only canonical runtime tree and backend/app/app is removed or deprecated safely.

## Scope
- move or merge needed files from backend/app/app into backend/app
- align imports to one package model
- update Docker working_dir and command if needed
- ensure API and worker both run from backend/app
- preserve current working endpoints and async inspection flow

## Out of Scope
- frontend redesign
- auth redesign beyond import/path fixes
- model behavior changes

## Acceptance Criteria
- [ ] backend/app is the canonical runtime tree
- [ ] backend/app/app is removed or no longer used at runtime
- [ ] API boots from one stable import path
- [ ] worker boots from one stable import path
- [ ] docker-compose.prod.yml matches canonical backend tree
- [ ] auth works
- [ ] inspect works
- [ ] poll endpoint works
- [ ] report endpoint still works

## Validation Plan
- docker compose -f docker-compose.prod.yml down -v
- docker compose -f docker-compose.prod.yml up -d --build
- docker compose -f docker-compose.prod.yml ps
- docker logs --tail=120 lumen-ai-api-1
- docker logs --tail=120 lumen-ai-worker-1
- curl -i http://localhost:8000/docs
- curl -i http://localhost:8080/api/health
- login + inspect + poll flow
- report endpoint smoke test

## Release Impact
runtime-sensitive
