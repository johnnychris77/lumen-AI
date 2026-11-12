# Stage 4 — Project Canvas Integration & Data Provenance Enforcement

## Purpose

Establish an authoritative, **structured, fail-closed** data-provenance contract so
external research photographs and controlled laboratory specimens can never be
promoted as real clinical evidence. This stage adds **no new defect detectors, no
new severity algorithms, and no new marketplace features**, and does not change
baseline comparison or image-detection behavior.

## Confirmed fail-opens removed

1. `training_eligibility_service.compute_training_eligibility()` classified a
   cohort as `"real"` whenever **no facility name contained the string
   `"Synthetic Experimental Lab"`**. A facility string is not provenance.
2. `lens_model_registration.register_lens_model()` advanced a trained model to
   **Candidate** whenever `data_provenance == "real"` (a string produced by (1)).
3. `candidate_training.run_full_candidate_pipeline()` advanced **any trained
   model to Candidate on trained status alone** — no provenance check at all.

All three are replaced by a verified, authority-gated provenance record.

## Provenance contract

Structured class on the governed `DatasetRegistryEntry` (no second registry):

| class | clinical? | notes |
|---|---|---|
| `synthetic_experimental` | never | generated images |
| `external_nonclinical` | never | external research datasets (WPI, DefectAtlas-20, …) |
| `laboratory_controlled` | never | controlled lab specimens |
| `real_clinical` | **only when approved** | real governed hospital clinical images |
| `unknown` | never | provenance not established |
| `legacy_unverified` | never | pre-Stage-4 rows (conservative default) |

New columns (migration `c3e7a9b14d20`): `data_provenance_class`,
`provenance_source_id`, `provenance_source_version`, `provenance_source_institution`,
`provenance_rights_evidence_ref`, `provenance_specimen_id`,
`provenance_approval_status`, `provenance_approved_by`, `provenance_approved_at`.

### Fail-closed rules (`provenance_governance.py`)
- Any missing/blank/unrecognised class normalises to `legacy_unverified` — never
  clinical or research.
- `is_clinical_evidence(entry)` is true **only** for `real_clinical` **and**
  `provenance_approval_status == approved`.
- A client cannot self-certify: ingestion may *declare* a class but
  `real_clinical` is stored `pending` and only an authorized governance role
  (`admin` / `spd_manager`) can approve it, via
  `set_provenance_classification(..., approve=True)`. Every classification/approval
  is written to the existing immutable, hash-chained enterprise audit chain.
- Tenant isolation: a provenance change is refused when `tenant_id` does not match
  the entry.

## Project Lens eligibility (`compute_training_eligibility`)

Provenance now comes from the verified structured records, not string matching.
The report additionally exposes `provenance_breakdown`,
`provenance_excluded_from_clinical`, `clinical_sample_count`,
`research_experiment_eligible`, and `clinical_promotion_eligible`. The cohort is
**clinically promotable only when every sample is verified `real_clinical` +
approved**; mixed, unknown, legacy, unapproved, or empty cohorts are rejected
(`data_provenance` reports the honest aggregate — `mixed` / a research class /
`unknown` / `none`). Existing rights/PHI/quality/archival/duplicate gates are
unchanged and still enforced.

## Model promotion

Both mechanisms are gated on the explicit `clinical_promotion_eligible` flag:
- `register_lens_model`: Candidate requires `clinical_promotion_eligible is True`
  **and** `data_provenance == "real_clinical"`.
- `run_full_candidate_pipeline` (Genesis): Candidate requires
  `summarize_cohort_provenance(samples)["clinical_promotion_eligible"]`.

A model built only from synthetic / external / laboratory / unknown / unapproved /
mixed data stays **Experimental**. The human-led Candidate → Validated Candidate →
Pilot → Production ladder and `live_inference_adapter` selection are unchanged —
this only makes the Experimental→Candidate assignment harder (fail-closed), so a
non-clinical model is never auto-eligible for serving.

## Split & leakage

Reuses the existing leakage-safe splitter (`lens_training_pipeline` →
`dataset_split.split_dataset(..., group_by_serial=True)` + `has_no_group_leakage`),
which groups by physical-instrument identity and raises on leakage. No new split
logic was added.

## Migration / backfill (`c3e7a9b14d20`)

Additive columns with conservative server-defaults: every existing row backfills
to `data_provenance_class='legacy_unverified'`, `provenance_approval_status='pending'`
— **no historical row is relabelled clinical**. Reclassifying legitimately-sourced
clinical data requires an explicit authorized review. `downgrade()` drops the
columns only (no data destroyed on upgrade). The runtime also bootstraps these
columns via `column_migrator.ensure_all_columns` at startup, so SQLite/Postgres and
the create_all path all converge.

## Rights vs release

Rights to *use* a dataset for research/training (`usage_rights`, licence evidence
`provenance_rights_evidence_ref`) remain distinct from rights to *release*
hospital/research-derived information to manufacturers. **No OEM data export is
enabled by this stage.**

## Tests

`tests/test_stage4_provenance_enforcement.py` (15): fail-closed normalisation; each
category; clinical requires approved real_clinical; legacy default; ingestion
cannot self-certify; unauthorized-role approval refused; approval audited;
cross-tenant denied; mixed/research cohort summaries; eligibility from records not
facility strings; both promotion gates (no Candidate from non-clinical); rights/PHI
exclusion. Updated `tests/test_candidate_model_training.py` so Candidate cohorts
carry legitimate approved `real_clinical` provenance.

## Deviations from frozen architecture

None structural. Changes are additive columns + a new governance service that reads
the existing registry and writes the existing audit chain. No new ML, governance, or
audit engine; no change to inference, baseline comparison, production env, secrets,
or deployed models.
