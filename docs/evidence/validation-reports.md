# Validation Reports

## Status: mock/simulated dataset only — submission-grade validation pending

`docs/regulatory/clinical-evidence-summary.md` documents the current
validation dataset explicitly: **1,200 mock cases, 100 per category**,
with the document's own header stating *"All performance data at Version
1.0 is derived from mock/simulated datasets. Live multi-site clinical
study is pending. This data should not be used as the basis for
regulatory submissions without completion of the live reader study."*

This evidence repository entry does not soften that disclaimer — it is
repeated here deliberately so anyone browsing evidence-by-category (rather
than starting from the regulatory package) sees it too.

## What exists today

- The full P12 clinical validation engine (`app/services/validation_engine.py`,
  `app/models/validation.py`) — confusion-matrix analysis, kappa
  agreement, sealed test set registry, reader study simulator — is real,
  tested infrastructure. It has been exercised against the mock dataset
  described above, not yet against a sealed, adjudicated real-world
  dataset.
- The Phase 18 pilot validation ground-truth pipeline (real supervisor
  reviews → `PilotValidationCase` records) is the mechanism that will
  eventually produce a real validation dataset — see
  `docs/evidence/pilot-studies.md`.

## What a real validation report entry requires before publication here

1. A sealed test set (`app/models/validation.py::SealedTestRegistry`)
   registered and evaluated per `docs/clinical/sealed-test-set-protocol.md`.
2. Real, adjudicated ground truth — not mock data — as the basis for
   every reported accuracy/precision/recall/kappa figure.
3. The critical safety metrics (blood/tissue/organic-residue/crack/
   missing-component false-negative rates) computed from that real
   ground truth, evaluated against the thresholds in
   `docs/validation/pilot-go-no-go-criteria.md`.
4. Sign-off per `docs/regulatory/submission-readiness-review.md` before
   any validation report here is characterized as submission-ready.

## Related documents

- `docs/clinical/clinical-performance-report.md`
- `docs/clinical/human-vs-ai-study-protocol.md`
- `docs/regulatory/master-traceability-matrix.md`
