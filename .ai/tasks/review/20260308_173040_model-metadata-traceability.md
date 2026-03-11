# Task: model-metadata-traceability

## Owning Agent
ml

## Problem
LumenAI returns inspection results, but the system does not yet expose model traceability fields needed for operational trust, QA review, and future healthcare compliance workflows.

## Goal
Add model metadata to inspection results so each inference can be traced to a model name, model version, and inference timestamp.

## Scope
- inference output schema
- inspection persistence model
- inspect response
- inspection polling response
- history response if applicable
- backward-compatible defaults for existing rows

## Out of Scope
- frontend redesign beyond consuming existing fields later
- auth redesign
- PDF redesign unless needed for metadata display

## Acceptance Criteria
- [ ] inspection records store model_name
- [ ] inspection records store model_version
- [ ] inspection records store inference_timestamp
- [ ] inspect completion flow persists metadata
- [ ] polling endpoint returns metadata fields
- [ ] history endpoint returns metadata fields or safe defaults
- [ ] existing records do not break API responses

## Validation Plan
- rebuild API and worker
- submit sample inspection
- poll completed inspection
- verify model_name, model_version, inference_timestamp are present
- verify history still loads

## Release Impact
minor
