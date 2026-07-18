# LPZ-DIR-010 — Pilot Zero Acceptance Test Plan

**Purpose:** define the end-to-end acceptance tests that must pass before Pilot
Alpha *execution*. Each test states preconditions, steps, and the **expected
outcome**. Tests marked **(blocked)** require the physical lab (LRR-1) and/or code
enforcement (ERR-2) first. Run the backend suite from `backend/` on a fresh DB.

## Acceptance tests

| ID | Validates | Steps | Expected outcome | Gating |
|---|---|---|---|---|
| AT-01 | Image acquisition | Acquire a governed image of a known instrument in the qualified lab | Image stored, integrity-hashed, identity-bound, no PHI | (blocked: LRR-1) |
| AT-02 | Metadata | Inspect the acquired image's metadata | All required acquisition fields present + consistent | (blocked: LRR-1) |
| AT-03 | Annotation | Annotate the image with a controlled-taxonomy finding + evidence | Annotation stored, versioned, evidence-linked; Unknown allowed | Ready (schema/code) |
| AT-04 | Ground Truth | Primary + independent secondary review → approve | GT `DRAFT→ACTIVE`, immutable, reviewer≠annotator | Ready; SoD gate (ERR-2) |
| AT-05 | Digital Twin | Resolve the instrument's Digital Twin | Twin identity resolves; links image/annotation/GT | Ready |
| AT-06 | Baseline | Build + approve a baseline from ACTIVE GT | Baseline requires ACTIVE GT; approver≠author; lifecycle ACTIVE | Ready; GT-gate (ERR-2) |
| AT-07 | Dataset generation | Build a dataset from approved evidence; partition | Approved-evidence-only; leakage-free instrument-grouped split; manifest+checksum | Ready; immutability (ERR-2) |
| AT-08 | Experiment registration | Register a governed experiment (no training) | Experiment record with pinned dataset/GT/baseline versions, seed, env | (blocked: enforcement AGR-2) |
| AT-09 | Model registry | Register a candidate model entry | Entry with checksum + lineage + model card; no deployment | Ready (schema) |
| AT-10 | Audit logging | Perform each lifecycle transition above | Every transition emits an attributable audit event (100% completeness) | Ready |
| AT-11 | Evidence retrieval | Assemble an evidence package for an instrument/time | Full chain reconstructable: image→…→dataset/model, verifiable | Ready |

## Execution rules

* Run from `backend/` (`cd backend && python -m pytest tests/ -q`) on a fresh DB
  (`rm -f test.db`) to avoid order-dependent artifacts.
* A test is **PASS** only when its expected outcome is met with evidence recorded.
* **(blocked)** tests are prerequisites-gated, not failures; they become executable
  once LRR-1 (lab) and ERR-2/AGR-2 (enforcement) conditions close.

## Coverage summary

* **Executable now (schema/code):** AT-03, AT-05, AT-09, AT-10, AT-11 (and AT-04/
  06/07 once the shared enforcement condition closes).
* **Blocked on physical lab:** AT-01, AT-02 (and downstream data-dependent runs).
* **Blocked on enforcement:** AT-08 (first-class experiment record).

Passing the executable subset demonstrates the governed pipeline end-to-end on
seeded evidence; passing the full set (post-lab, post-enforcement) is the gate for a
data-acquiring Pilot Alpha.
