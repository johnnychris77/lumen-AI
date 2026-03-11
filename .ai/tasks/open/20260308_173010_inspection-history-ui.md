# Task: inspection-history-ui

## Owning Agent
frontend

## Problem
LumenAI has a working async inspection backend, but users cannot view prior inspections in a usable frontend history screen.

## Goal
Build a frontend inspection history page that lists inspections, shows status/results, and links users to report downloads.

## Scope
- frontend history page
- fetch inspection history from backend
- display status, confidence, material type, timestamp, file name
- link each completed inspection to /api/reports/{id}.pdf
- handle loading, empty, and error states

## Out of Scope
- backend API redesign
- auth redesign
- model behavior changes

## Acceptance Criteria
- [ ] frontend can call the history endpoint successfully
- [ ] history page renders a list of inspections
- [ ] each row shows key inspection fields
- [ ] completed inspections include report download link
- [ ] loading and error states are handled
- [ ] page works with the current backend/API flow

## Validation Plan
- start frontend and backend
- upload at least one sample inspection
- open history page
- verify records render correctly
- verify report link opens PDF for completed inspection

## Release Impact
minor
