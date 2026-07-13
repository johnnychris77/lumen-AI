# LumenAI — Training Guide

Objective 15 review (Technician Guide, Supervisor Guide, Quick Start Guide, Training Workbook portions — Administrator/Director guides and the FAQ/Troubleshooting content live in [CUSTOMER_SUCCESS_PLAYBOOK.md](./CUSTOMER_SUCCESS_PLAYBOOK.md)). As with the customer success playbook, this guide indexes and reconciles a large amount of real existing material rather than authoring a competing version from scratch.

## Quick Start Guide

`docs/pilot/pilot-user-training-guide.md`'s "Quick Start (All Users — 5 Minutes)" section is the real, existing canonical quick start (login, dashboard orientation, role overview) — use it directly rather than writing a new one. `docs/customer/training-matrix.md`'s own stated principle should govern how this guide is maintained going forward: *"training content should reference the live product, not a static screenshot deck that goes stale."*

## Technician Guide

Assemble from:
- `docs/pilot/pilot-user-training-guide.md`'s SPD Technician workflow section, including its "Common errors" table.
- `TrainingCenterPage.tsx`'s real Technician training track (links to live routes: `/inspection/new`, `/findings`).
- The honest three-flow caveat from `docs/ux-review/USER_JOURNEYS.md`: train technicians to use **only** `New Inspection` (`/inspection/new`) as the entry point for creating inspections. The other two nav-reachable capture/upload screens exist but have inconsistent rules about manual finding-category/risk-level entry — using them will teach a technician a workflow that contradicts what the primary flow does.
- Sage's real adaptive-learning capability (`docs/agents/sage/adaptive-learning-plans.md`, `microlearning-generator.md`) as the platform mechanism behind ongoing, personalized technician training — microlearning modules are generated only from approved education content and require human (educator/supervisor/manager) approval before assignment, never fabricated for unsupported finding types.

## Supervisor Guide

Assemble from `docs/pilot/pilot-user-training-guide.md`'s QI Reviewer/Manager sections and `TrainingCenterPage.tsx`'s Manager track. **Include the same honest caveat carried through this entire document set**: a reachable, working "approve/return" control was not located during the UX review (`docs/ux-review/USER_JOURNEYS.md`). Train supervisors on the workflow that is actually available at the time of their onboarding, and update this guide once a working control exists rather than training against a screen that isn't there.

## Training requirements matrix

`docs/customer/training-matrix.md` already provides the real, role-based training-requirements table (Technician/Supervisor/Manager/Executive Sponsor/IT Admin) with concrete "what trained means" behavioral definitions and refresher-training triggers — use this table directly as the backbone of the Training Workbook below, rather than re-deriving requirements.

## Training Workbook — assembled from real, existing session content

`docs/customer-success/first-customer-deployment-guide.md`'s 4-session training curriculum (Technician/Manager/Vendor/Executive sessions) is the most complete existing session-by-session workbook and should anchor this section. Cross-reference `docs/customer/customer-onboarding-playbook.md`'s Week 3 SPD Technician training agenda for a shorter-form alternative. Where these two documents overlap but differ in detail, prefer the newer `docs/customer-success/` version, consistent with the reconciliation approach in `docs/demo-program/CUSTOMER_SUCCESS_PLAYBOOK.md`.

**Sage as the ongoing-training backbone** (real, not aspirational): Project Sage's competency taxonomy (7 domains / 52 leaves — instrument identification, anatomy recognition, inspection technique, contamination/condition recognition, clinical decision support, documentation) is the platform's actual mechanism for detecting a knowledge gap and generating a targeted learning plan. Every `SageLearningPlan` requires human approval before assignment, and every microlearning module starts in `draft` status requiring explicit approval — this should be presented in the workbook as "the platform proposes, a human educator/supervisor approves," never as autonomous training assignment.

## What genuinely needs new authorship

The role-based training matrix, quick start, and 4-session curriculum are all real and reusable. The one gap: **no unified, single-document "Training Workbook" currently exists that sequences the matrix → quick start → 4-session curriculum → Sage's ongoing microlearning loop into one linear path for a new customer's training lead to follow.** That sequencing is this guide's actual contribution — pointing to the 4 real source documents in the right order, not recreating their content.
