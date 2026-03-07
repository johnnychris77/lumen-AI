# Task: Fix DB imports and enforce Postgres runtime

## Owning Agent
backend

## Problem
DB imports are inconsistent and runtime has crashed due to Base being imported from session.py. Shared runtime must use explicit Postgres-backed session logic.

## Goal
Standardize Base, SessionLocal, and engine imports and ensure API/worker share one Postgres session layer.

## Scope
- db.base
- db.session
- db.__init__
- db.models
- dependent imports in API/worker code
- runtime verification

## Out of Scope
- frontend changes
- model changes
- release workflow redesign

## Acceptance Criteria
- [ ] Base imported from db.base
- [ ] SessionLocal and engine imported from db.session
- [ ] no Base import from session.py remains
- [ ] no sqlite fallback in shared runtime
- [ ] API boots
- [ ] worker boots
- [ ] engine URL is Postgres in both containers
- [ ] inspect flow can enqueue and process
