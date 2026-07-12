# Project Veritas — Evidence Assurance Agent

LumenAI AI Specialist, Mission & Section 1.

## What Veritas does

Veritas evaluates whether an inspection has sufficient, reliable, and
governed evidence to support an AI recommendation. It validates instrument
identity, manufacturer and model association, anatomy-zone alignment,
baseline availability/approval status/version, image quality, inspection
coverage, evidence provenance, supervisor validation, model and dataset
versions, and audit completeness.

Veritas does **not** independently approve an instrument. It determines
whether the evidence is trustworthy enough for the inspection workflow to
proceed and identifies what additional evidence is required.

## Architecture position

```
Instrument Identification -> Anatomy Profile -> Inspection Images ->
Baseline Resolution -> Evidence Integrity Review -> AI Analysis ->
Clinical Reasoning -> Supervisor Validation -> Governed Decision Record
```

Veritas never bypasses Instrument Intelligence, Anatomy Intelligence, RBAC,
tenant isolation, or human validation.

## Deterministic, not an autonomous LLM

Veritas is a deterministic Python orchestrator
(`veritas_evidence_agent_service.run_evidence_assessment`) composing real,
already-built infrastructure. There is no LLM/embedding API call anywhere.

## What is reused vs. genuinely new

- **Baseline resolution** — `baseline_comparison_scoring_service.
  resolve_baseline` (manufacturer -> vendor -> hospital priority across
  `BaselineLibraryEntry` and `EnterpriseVendorBaselineSubscription`) is
  called directly, never re-implemented.
- **Coverage** — `inspection_coverage.compute_coverage` is called directly.
- **Image quality** — no real CV quality model exists in this codebase;
  Veritas reports this honestly (see `docs/agents/veritas/
  image-quality-assessment.md`) rather than fabricating a score.
- **Model/dataset versions** — read from `ModelRegistryEntry`
  (`app/models/model_registry.py`), never duplicated.
- **Image provenance** — `RetainedImage`/`ImageLabel` referenced by ID,
  never copied.

Genuinely new: seven tables (`VeritasBaselineResolution`,
`VeritasBaselineGovernanceAction`, `VeritasEvidenceProvenanceRecord`,
`VeritasEvidenceReadinessAssessment`, `VeritasEvidenceConflict`,
`VeritasTrainingDatasetEntry`, `VeritasFeedback`) and sixteen service
modules.

## Responsibilities (Section 1)

- resolve the correct baseline
- verify baseline approval and version
- validate image-to-instrument association
- assess image quality
- assess required-zone coverage
- detect missing or conflicting evidence
- identify stale or superseded baselines
- verify evidence provenance
- calculate Evidence Readiness Score
- recommend additional evidence capture
- prevent unsupported final AI conclusions

Every result is explainable (`reasoning_narrative`) and auditable
(`score_breakdown_json`, `limitations_json`, full governance-action log).

## API

```
POST /api/veritas/assess/{inspection_id}
GET  /api/veritas/assessments/{id}
```
