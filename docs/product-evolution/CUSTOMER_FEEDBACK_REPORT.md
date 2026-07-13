# LumenAI — Customer Feedback Report

The Customer Feedback Review objective asks for feedback aggregated by frequency, severity, business value, clinical impact, operational impact, requested role, customer segment, facility, and organization. **This report states plainly that no real customer, facility, or organization has generated this feedback yet** — the same finding already established in `docs/release-management/CUSTOMER_FEEDBACK_LOG.md` and `docs/commercial-readiness/FINAL_READINESS_REPORT.md`. Fabricating aggregated customer-segment/facility breakdowns here would violate this program's own evidentiary standard. This report instead documents precisely what evidence *does* exist and how it should be read.

## A specific, important finding: `docs/pilot/pilot-lessons-learned.md` is internal dogfooding, not real pilot data

This document (dated 2026-06-23, titled "Pilot Lessons Learned," covering "Pilot Week 1 deployment") is real and contains specific, code-consistent, genuinely useful findings. However, its own "Pilot Success Metrics — Week 1" table reports exactly **10 instruments registered, 25 baseline records, 50 inspection records** — precisely matching `backend/scripts/seed_pilot_data.py`'s synthetic generator output (confirmed in `docs/demo-program/SYNTHETIC_DATA_GUIDE.md`), and its own "Review turnaround (avg)" row is explicitly labeled **"~2h (simulated)."** Combined with `docs/evidence/case-studies.md` and `docs/commercial/launch-readiness-checklist.md`'s independent, unambiguous statements that no real customer pilot has occurred, this document should be understood as **an internal dogfooding/QA exercise run against the synthetic seed dataset**, not validated feedback from a real hospital deployment — regardless of its "Pilot" framing.

**This is not a reason to discard its findings.** Its technical observations (a two-step inspection/image-upload flow, missing `facility_name`/`tray_id`/`instrument_barcode` columns on the `Inspection` model, no priority sort on the baseline review queue, several missing report types) are independently verifiable against the real codebase — several were confirmed again, independently, in this review program's own UX and performance work (e.g., the two-step image-upload friction matches `docs/ux-review/USER_JOURNEYS.md`'s finding of three competing inspection-creation flows). They should be treated as legitimate **"operational observations"** and **"usability studies"** evidence — two of this program's own explicitly acceptable input sources — but never cited as "Pilot Hospital" or validated customer feedback in any external-facing material.

## The "User Feedback Summary" quotes — treat as illustrative user-research personas, not real quotes

The document's Section 6 ("SPD Technicians (n=2)," "SPD Manager (n=1)," etc.) reads as simulated or hypothetical persona-based usability testing, consistent with the same document's simulated-metrics framing above. **No individual named customer or facility should be inferred from this section**, and it must not be cited as real customer testimony in any sales, marketing, or investor material (this constraint is the same one already established in `docs/commercial-readiness/MARKETING_LAUNCH_PLAN.md` and `SALES_PLAYBOOK.md` regarding fabricated case studies).

## What legitimate evidence does exist for Version 1.1 (per this program's own acceptable-source list)

| Acceptable input source | Real evidence available today |
|---|---|
| Pilot Hospitals | **None yet** |
| SPD Technicians / Supervisors / Managers | **None yet** (real feedback) — see `pilot-lessons-learned.md` caveat above for the internal-dogfooding analog |
| Market Directors, Quality Departments, Infection Prevention, OR Leadership, Manufacturers, Biomedical Engineering | **None yet** |
| Customer Success | **None yet** — no live customer to report on (`docs/commercial-readiness/CUSTOMER_SUCCESS_PLAYBOOK.md`'s framework is ready but unpopulated) |
| Support Tickets | **None yet** — no ticketing-system integration exists (`docs/commercial-readiness/SUPPORT_OPERATIONS_MANUAL.md`) |
| Usage Analytics | **None yet** at real-customer scale; real, working analytics infrastructure exists (`pilot_analytics.py`) and is ready to populate once a pilot begins |
| Council Decisions | Real — Council's specialist-review mechanism is live and could generate real governance-relevant signal once cases are opened |
| Clinical Validation Reviews | **Real and available** — `docs/clinical-validation/` (11 documents) |
| Security Reviews | **Real and available** — `docs/commercial-readiness/LEGAL_GOVERNANCE_PACKAGE.md`, `docs/release-management/SECURITY_UPDATE_LOG.md` |
| Performance Metrics | **Real and available** — `docs/release-management/PERFORMANCE_LOG.md` |
| Research Findings | **Real and available** — the internal dogfooding findings in `pilot-lessons-learned.md`, appropriately caveated |

## Recommendation

Version 1.1's initial backlog (`docs/product-evolution/PRODUCT_BACKLOG.md`) should draw exclusively from the "Real and available" rows above — clinical validation reviews, security reviews, performance metrics, and appropriately-caveated internal dogfooding findings — while the "Pilot Requested" backlog category remains genuinely empty until real customer feedback exists. This report should be re-issued with real aggregated customer data (by frequency, severity, facility, etc.) as soon as the first real pilot produces it.
