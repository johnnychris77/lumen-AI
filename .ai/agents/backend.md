# Backend Agent

## Purpose
Implement backend changes safely across API, worker, DB, queue, and services.

## Responsibilities
- FastAPI routes
- worker jobs
- DB models and session handling
- queue flow
- service logic
- report generation interfaces

## Must Preserve
- one DB session source
- one engine source
- API/worker parity
- Docker bootability

## Required Validation
- API boots
- worker boots
- routes load
- queue flow works
- no import/runtime regressions

## Rules
- Base comes from db.base
- SessionLocal and engine come from db.session
- no sqlite fallback in shared runtime
