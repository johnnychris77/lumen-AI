# Task: report-download-ui

## Owning Agent
frontend

## Problem
LumenAI can generate PDF inspection reports, but the frontend does not yet provide a polished, explicit report access experience for completed inspections.

## Goal
Improve the frontend so completed inspections clearly expose report download/open actions in the UI.

## Scope
- enhance history UI report actions
- improve report link visibility and wording
- handle unavailable reports gracefully
- keep links aligned to /api/reports/{id}.pdf

## Out of Scope
- backend report redesign
- auth redesign
- model behavior changes

## Acceptance Criteria
- [ ] completed inspections clearly show report action
- [ ] report link opens the PDF successfully
- [ ] non-completed inspections do not show broken actions
- [ ] UI remains readable and clean
- [ ] behavior works with current backend

## Validation Plan
- build frontend
- run backend
- create completed inspection
- open history page
- click report action
- verify PDF opens

## Release Impact
minor
