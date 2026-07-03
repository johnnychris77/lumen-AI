# Clinical Evidence Repository

The index for LumenAI's clinical and operational evidence: pilot studies,
validation reports, case studies, customer success stories, lessons
learned, and benchmark reports.

## Honesty framing (read this first)

This repository holds **real evidence as it is generated**, plus the
structure/templates for evidence not yet collected. It is not a
collection of illustrative or fabricated results. Where a category below
has no real entry yet, that's stated plainly rather than filled with a
placeholder that reads like a real result.

As of this writing:

- **Pilot studies**: framework and protocol exist and are fully built
  (Phase 18 — `docs/validation/pilot-validation-protocol.md`); a
  documented prior pilot (Bon Secours) exercised the platform with seeded
  data (`docs/pilot/pilot-findings-analysis.md`); a live, multi-site
  clinical pilot with real supervisor-adjudicated ground truth has not
  yet completed — see `docs/evidence/pilot-studies.md`.
- **Validation reports**: the regulatory validation dataset is explicitly
  mock/simulated (`docs/regulatory/clinical-evidence-summary.md`); no
  submission-grade validation report exists yet — see
  `docs/evidence/validation-reports.md`.
- **Case studies / customer success stories**: none published yet — see
  `docs/evidence/case-studies.md` and `customer-success-stories.md` for
  the template these will follow once real customers reach Day 90.
- **Lessons learned**: real internal lessons exist from prior pilot work
  — see `docs/evidence/lessons-learned.md`.
- **Benchmark reports**: network benchmarking infrastructure exists
  (Phase 15) but requires multiple contributing facilities before
  publishable benchmarks exist — see `docs/evidence/benchmark-reports.md`.

## Why this matters

LumenAI's own design principles require every clinical claim to be
traceable and non-fabricated
(`docs/architecture/design-principles.md`). An evidence repository that
overstates what's been proven would violate the same principle the
product is built on. This repository is deliberately conservative about
what it claims is "evidence" versus "framework ready to capture evidence."

## How evidence gets added here

1. **Pilot studies** — populated automatically as sites complete Phase 18
   pilot validation (`/api/pilot-validation/report`).
2. **Validation reports** — populated as real, adjudicated validation
   runs complete (`docs/validation/` protocol), superseding the current
   mock dataset.
3. **Case studies / success stories** — written by Customer Success once
   a site reaches Day 90 value realization
   (`docs/customer/90-day-value-realization-plan.md`) and consents to
   being referenced (see `docs/customer-success/reference-customer-program.md`).
4. **Lessons learned** — captured after every pilot, go-live, or incident
   review.
5. **Benchmark reports** — published once enough contributing facilities
   exist to anonymize meaningfully (Phase 15 network intelligence
   requires a minimum facility count before publishing a benchmark — see
   `app/models/instrument_registry.py::contributing_facilities`).
