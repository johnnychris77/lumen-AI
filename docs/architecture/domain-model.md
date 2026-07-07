# LumenAI Domain Model

Core entities of the platform, each mapped to its purpose in the clinical
ontology, its required fields, its relationships, and how it's used
downstream. Field lists are the conceptually required fields, not an
exhaustive column dump — see the cited model file for the full schema.

## Instrument

- **Purpose:** the physical object under inspection; the root of the
  ontology chain.
- **Required fields:** `instrument_type`, tenant, image reference
  (`has_image`, `image_sha256`).
- **Relationships:** resolves to an Instrument Family (via
  `resolve_family`); has zero-or-more Inspection Images; has a Baseline
  where one exists; is the subject of one or more Clinical Decisions.
- **Downstream use:** every AI Finding, Clinical Decision, and Supervisor
  Review is scoped to an inspection of one instrument.
- **Owning model:** `app/models/inspection.py` (`Inspection`).

## Manufacturer

- **Purpose:** who made the instrument — needed to resolve the correct
  Baseline and Instrument Knowledge entry.
- **Required fields:** manufacturer name, registration/reference IDs.
- **Relationships:** has many Models; has many Baselines.
- **Downstream use:** baseline matching, vendor intelligence, recall
  correlation.
- **Owning model:** `app/models/manufacturer_reg.py`,
  `app/models/instrument_registry.py` (`manufacturer_name`).

## Model

- **Purpose:** the specific instrument model/UDI — the finest-grained
  identity below manufacturer.
- **Required fields:** `model_name`, `udi`, `instrument_category`.
- **Relationships:** belongs to a Manufacturer; has a Baseline; has an
  Instrument Knowledge entry (anatomy zones, failure modes, maintenance
  interval).
- **Downstream use:** baseline comparison scoring, instrument knowledge
  lookups, network benchmarking.
- **Owning model:** `app/models/baseline_library.py`
  (`BaselineLibraryEntry`), `app/models/instrument_knowledge.py`.

## Baseline

- **Purpose:** the reference condition (manufacturer or site-submitted) an
  inspection is compared against.
- **Required fields:** `instrument_category`, `manufacturer_name`,
  `model_name`, `baseline_type` (manufacturer/site), `approval_status`.
- **Relationships:** belongs to a Manufacturer/Model; referenced by every
  Clinical Decision that performs a baseline comparison; audited by
  `app/models/vendor_baseline_audit.py`.
- **Downstream use:** `baseline_comparison_scoring_service.py`'s
  `baseline_difference` and `evidence_strength` outputs; Phase 18's
  `baseline_source` / `has_baseline` cohort tracking.
- **Owning model:** `app/models/baseline_library.py`.

## Anatomy Profile

- **Purpose:** the resolved instrument family's zone map — its zones,
  high-risk zones, required inspection views, and manual-check guidance.
- **Required fields:** `instrument_family`, `anatomy_zones`,
  `high_risk_zones`, `recommended_image_views`.
- **Relationships:** derived from Instrument Family; feeds Inspection
  Zone resolution and Inspection Coverage scoring.
- **Downstream use:** zone-aware scoring, coverage checks, mentor
  explanations.
- **Owning service:** `app/services/instrument_anatomy.py`
  (`anatomy_profile`, `get_anatomy`).

## Inspection Zone

- **Purpose:** the specific high-risk (or low-risk) location on the
  instrument a finding is attributed to.
- **Required fields:** `instrument_zone`, `zone_risk`, `zone_confidence`,
  `assignment_method`.
- **Relationships:** belongs to an Anatomy Profile; attached to every AI
  Finding; correctable by a Supervisor Review
  (`supervisor_zone_correction` / `corrected_zone`).
- **Downstream use:** Phase 18 zone performance metrics (miss rate,
  override rate, mean confidence per zone).
- **Owning service:** `app/services/instrument_zones.py`.

## Inspection Image

- **Purpose:** the captured image evidence for an inspection (and,
  separately, an opt-in retained training image).
- **Required fields:** `sha256`, `content_type`, `exif_stripped`,
  `consent_recorded` (for retained images), no PHI.
- **Relationships:** belongs to an Instrument/Inspection; may be promoted
  to a `RetainedImage` for training with consent.
- **Downstream use:** CV inference input; training dataset construction.
- **Owning models:** `app/models/inspection.py` (`image_sha256`,
  `has_image`), `app/models/retained_image.py` (`RetainedImage`).

## AI Finding

- **Purpose:** a detected clinical characteristic (blood, crack, missing
  component, …) with its zone and severity attached.
- **Required fields:** `type`/`finding_type`, `severity_index`/`severity`,
  `instrument_zone`, confidence.
- **Relationships:** belongs to an inspection; located in an Inspection
  Zone; interpreted by the Clinical Reasoning Engine; may become a Training
  Label.
- **Downstream use:** clinical decision input; safety metrics (Phase 18
  critical false-negative rates by finding type).
- **Owning service:** `app/services/baseline_comparison_scoring_service.py`
  (`predicted_findings`).

## Clinical Decision

- **Purpose:** the AI's interpreted recommendation for what should happen
  to the instrument (Architecture Layer 7).
- **Required fields:** `outcome`/`recommended_action`, `reasoning`,
  `interpretation`, `evidence_strength`, `baseline_difference`.
- **Relationships:** produced from one or more AI Findings plus baseline
  comparison; reviewed and potentially overridden by a Supervisor Review.
- **Downstream use:** operational disposition; audit trail; supervisor
  review comparison (`ai_recommendation` snapshot).
- **Owning service:** `app/services/baseline_comparison_scoring_service.py`
  (`ai_clinical_review`), `app/services/clinical_mentor.py`.

## Supervisor Review

- **Purpose:** the human validation record — agreement, correction, final
  disposition, and rationale.
- **Required fields:** `agreement`, `rationale` (required on
  disagreement/override), `finding_correct`, `zone_correct`,
  `corrected_zone`, `final_disposition`.
- **Relationships:** references an Inspection and its Clinical Decision;
  is the direct source of a Training Label (Phase 18
  `PilotValidationCase`).
- **Downstream use:** model-performance aggregation, ground-truth
  labeling, audit trail.
- **Owning model:** `app/models/supervisor_review.py`.

## Training Label

- **Purpose:** the confusion-matrix ground truth (TP/TN/FP/FN/
  inconclusive) derived from comparing an AI prediction to a supervisor's
  confirmed finding.
- **Required fields:** `ai_prediction`, `supervisor_finding`,
  `ground_truth_label` (always server-derived, never client-supplied),
  `is_critical_finding`.
- **Relationships:** derived from a Supervisor Review + its Inspection;
  feeds Model Version evaluation and Dataset Version composition.
- **Downstream use:** clinical performance metrics, zone performance,
  safety review queue, go/no-go readiness gate (Phase 18).
- **Owning model:** `app/models/pilot_validation.py`
  (`PilotValidationCase`); also `app/models/retained_image.py`
  (`ImageLabel`) for image-level training labels and
  `app/models/shadow_prediction.py` for pre-deployment shadow evaluation.

## Digital Twin

- **Purpose:** a simulated/forecast quality state for a tenant or
  instrument population, used for scenario planning rather than live
  inspection.
- **Required fields:** current state snapshot, forecast horizon,
  intervention model reference.
- **Relationships:** aggregates across many Inspections/Clinical
  Decisions; independent of any single instrument.
- **Downstream use:** executive decision briefs, scenario simulation.
- **Owning models:** `app/models/digital_quality_twin.py`
  (`QualityTwinState`, `ScenarioSimulation`, `QualityForecast`,
  `InterventionModel`, `ExecutiveDecisionBrief`, `ForecastOutcome`),
  `app/models/digital_twin.py`.

## Knowledge Graph Node

- **Purpose:** a network-level entity (instrument risk signal, recall
  early-warning, participant) used for cross-hospital intelligence.
- **Required fields:** node type, anonymized facility reference (never a
  raw hospital identity — see CLAUDE.md security constraints), signal
  payload.
- **Relationships:** connects Instrument/Model entities across tenants
  without exposing tenant-identifying data.
- **Downstream use:** global recall early warning, network benchmarking.
- **Owning models:** `app/models/global_intelligence.py`
  (`GlobalIntelligenceSignal`, `InstrumentRiskRegistryEntry`,
  `GlobalRecallEarlyWarning`, `GSINParticipant`),
  `app/models/quality_intelligence.py` (`EnterpriseRiskNode`,
  `EnterpriseRiskEdge`).

## Model Version

- **Purpose:** one row per trained model, its evaluation metrics, known
  limitations, and approval stage.
- **Required fields:** `model_id`, `model_version`, `model_type`,
  `dataset_version`, `evaluation_metrics`, `approval_status`
  (experimental/pilot/validated/deprecated), `approved_by`.
- **Relationships:** trained from a Dataset Version; evaluated against
  Training Labels; gated by the deployment-gate checklist before
  promotion.
- **Downstream use:** deployment gate (`app/services/ml/deployment_gates.py`),
  shadow-mode reconciliation.
- **Owning model:** `app/models/model_registry.py`
  (`ModelRegistryEntry`).

## Dataset Version

- **Purpose:** a labeled, versioned, leakage-free training/eval/test split.
- **Required fields:** version label, split ratios, stratification keys
  (family/zone/finding/severity/manufacturer/image-quality), leakage
  guarantees (an inspection's images never straddle splits).
- **Relationships:** composed of Training Labels; referenced by a Model
  Version's `dataset_version`; referenced by a Phase 18
  `PilotValidationCase.dataset_version`.
- **Downstream use:** reproducible evaluation, validation report
  provenance.
- **Owning service:** `app/services/ml/dataset_split.py`.

## Audit Event

- **Purpose:** the immutable compliance record of every consequential
  action — supervisor review, ground-truth submission, intelligence
  sharing, data export.
- **Required fields:** `tenant_id`, `actor_email`, `actor_role`,
  `action_type`, `resource_type`, `resource_id`, `compliance_flag`,
  `event_hash` / `previous_event_hash` (tamper-evident chain).
- **Relationships:** references whatever resource triggered it
  (Inspection, Supervisor Review, PilotValidationCase, …); never itself
  referenced by anything else — it is the terminal record.
- **Downstream use:** compliance exports, trust center, governance
  reconciliation.
- **Owning model:** `app/models/audit_log.py` (`AuditLog`),
  `app/audit.py` (`log_audit_event`).
