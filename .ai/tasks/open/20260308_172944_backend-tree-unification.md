# Task: backend-tree-unification

## Owning Agent
architect

## Problem
LumenAI currently has duplicate backend trees under backend/app and backend/app/app. The system is working, but the package structure is fragile and has already caused repeated import-path failures.

## Goal
Unify the backend package structure so API and worker run from one canonical app tree with one import model.

## Scope
- backend package structure
- Docker working_dir and command alignment
- import path cleanup
- removal plan for duplicate tree
- runtime validation for API and worker

## Out of Scope
- frontend redesign
- model behavior changes
- auth redesign

## Acceptance Criteria
- [ ] one canonical runtime app tree is defined
- [ ] duplicate backend path is removed or deprecated safely
- [ ] API runs from one stable import path
- [ ] worker runs from one stable import path
- [ ] docker compose config matches canonical structure
- [ ] auth, inspect, poll, and report endpoints still work

## Validation Plan
- docker compose -f docker-compose.prod.yml down -v
- docker compose -f docker-compose.prod.yml up -d --build
- docker compose -f docker-compose.prod.yml ps
- curl -i http://localhost:8000/docs
- curl -i http://localhost:8080/api/health
- login + inspect + poll flow

## Release Impact
runtime-sensitive
