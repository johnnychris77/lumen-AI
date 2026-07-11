"""v5.2 — LumenAI Network: Project GuardianX — AI Assurance Framework
(Trust, Compliance, Governance & AI Assurance).

## Naming disambiguation (read this first)

GuardianX is the 21st additive sprint. Its mission is entirely
cross-cutting -- assurance, explainability, auditability, and governance
*over* AI capabilities that already exist across the platform -- so
almost nothing here is a new engine; it composes what's already real:

  * **Model Governance (Section 2)** -- Olympus's `AIModelRegistryEntry`
    (v5.1) already has `validation_status`/`clinical_scope`/
    `evidence_json`/`performance_metrics_json`/certification fields.
    GuardianX extends it directly (see `olympus_network.py`) with
    `model_owner`/`clinical_owner`/`technical_owner`/
    `approval_committee`/`validation_date`/`retirement_date`/
    `training_dataset_metadata_json`/`known_limitations`/
    `approved_use_cases_json`/`out_of_scope_uses_json` and a second,
    distinct governance-approval chain linkage
    (`governance_status`/`governance_chain_id`/`governance_instance_id`)
    -- never a second model table.
  * **Governance Workflow (Section 6)** -- reuses Forge's
    `WorkflowApprovalChain`/`WorkflowApprovalInstance`
    (`forge_approval_service.py`) for the **fifth** time (after Athena,
    Phoenix, Infinity, Olympus), instantiated with the five named gates
    (Clinical Review Board, AI Governance Committee, Quality Leadership,
    Security, Compliance) -- distinct from Infinity/Olympus's
    certification gates, since certification and governance sign-off are
    different approval questions answered by different bodies.
  * **Trust Score (Section 9)** -- Knowledge/Workflow/Digital Twin Trust
    Score reuse Phoenix's `compute_knowledge_health_score`/
    `compute_workflow_health_score`/`compute_digital_twin_health_score`
    (`phoenix_platform_health_service.py`, v4.9) directly, never a third
    scoring engine for the same signal. Model Trust Score is genuinely
    new (nothing scores an individual AI model's trustworthiness).
    Platform Trust Score is a new, assurance-specific composite --
    distinct from Phoenix's Platform Maturity Index (which measures
    platform *improvement*, not governance/compliance trust) and
    Phoenix's Platform Health (operational health, not assurance).
  * **Evidence Ledger (Section 8)** -- "Digital Signature" is not a
    fabricated concept: every `EvidenceLedgerEntry` is paired with a real
    call to `enterprise_audit_service.record_enterprise_audit_event`
    (the same hash-chained, tamper-evident writer used platform-wide),
    and the entry's `digital_signature` column stores that event's real
    SHA-256 `event_hash`, verifiable via
    `audit_chain_verification_service.verify_audit_chain`. No service
    function ever updates or deletes a ledger row.
  * **Audit Replay (Section 4)** -- no new table. Replays compose
    `WorkflowExecution`'s already-captured `decision_path_json`/
    `execution_log_json` (Forge), the linked `WorkflowDefinition`/
    `WorkflowRule` version rows, and the resource's real audit trail via
    `verify_audit_chain`.
  * **Compliance Mapping (Section 7)** -- `regulatory_standards_catalogue.py`
    (Apollo, v4.7) already catalogues AAMI/AORN standard references.
    `ComplianceCapabilityMapping` is genuinely new: it maps a *platform
    capability* (not a clinical finding, which is what Apollo's
    `MappingDef` does) to an organizational requirement reference,
    explicitly for traceability -- never a regulatory-certification claim.

## What is genuinely new in this file

Five tables: `AIModelRiskEntry` (Risk Registry), `ComplianceCapabilityMapping`,
`EvidenceLedgerEntry`, `AIAssuranceTrustSnapshot`, `AIExplainabilityRecord`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── AI Risk Registry (Section 5) ─────────────────────────────────────────────
RISK_BIAS = "bias"
RISK_FAILURE_MODE = "failure_mode"
RISK_CLINICAL_BOUNDARY = "clinical_boundary"
RISK_GENERAL = "general_risk"
RISK_TYPES = [RISK_BIAS, RISK_FAILURE_MODE, RISK_CLINICAL_BOUNDARY, RISK_GENERAL]

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"
RISK_SEVERITIES = [SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL]

RISK_OPEN = "open"
RISK_MITIGATED = "mitigated"
RISK_ACCEPTED = "accepted"
RISK_STATUSES = [RISK_OPEN, RISK_MITIGATED, RISK_ACCEPTED]

# ── Governance Workflow gates (Section 6) — driven through Forge's
# WorkflowApprovalChain, reused for the fifth time. ──────────────────────────
GATE_CLINICAL_REVIEW_BOARD = "clinical_review_board"
GATE_AI_GOVERNANCE_COMMITTEE = "ai_governance_committee"
GATE_QUALITY_LEADERSHIP = "quality_leadership"
GATE_SECURITY = "security"
GATE_COMPLIANCE = "compliance"
GOVERNANCE_GATES = [
    GATE_CLINICAL_REVIEW_BOARD, GATE_AI_GOVERNANCE_COMMITTEE, GATE_QUALITY_LEADERSHIP,
    GATE_SECURITY, GATE_COMPLIANCE,
]

GOVERNANCE_NOT_STARTED = "not_started"
GOVERNANCE_IN_PROGRESS = "in_progress"
GOVERNANCE_APPROVED = "approved"
GOVERNANCE_REJECTED = "rejected"
GOVERNANCE_STATUSES = [GOVERNANCE_NOT_STARTED, GOVERNANCE_IN_PROGRESS, GOVERNANCE_APPROVED, GOVERNANCE_REJECTED]

# ── Compliance Mapping (Section 7) ───────────────────────────────────────────
REQ_INTERNAL_SOP = "internal_sop"
REQ_AAMI = "aami"
REQ_AORN = "aorn"
REQ_MANUFACTURER_IFU = "manufacturer_ifu"
REQ_ORGANIZATIONAL_POLICY = "organizational_policy"
REQUIREMENT_TYPES = [REQ_INTERNAL_SOP, REQ_AAMI, REQ_AORN, REQ_MANUFACTURER_IFU, REQ_ORGANIZATIONAL_POLICY]

# ── Trust Score (Section 9) ──────────────────────────────────────────────────
TRUST_SCOPE_PLATFORM = "platform"
TRUST_SCOPE_MODEL = "model"
TRUST_SCOPE_KNOWLEDGE = "knowledge"
TRUST_SCOPE_WORKFLOW = "workflow"
TRUST_SCOPE_DIGITAL_TWIN = "digital_twin"
TRUST_SCOPES = [
    TRUST_SCOPE_PLATFORM, TRUST_SCOPE_MODEL, TRUST_SCOPE_KNOWLEDGE, TRUST_SCOPE_WORKFLOW, TRUST_SCOPE_DIGITAL_TWIN,
]

DISCLAIMER = (
    "LumenAI GuardianX provides AI assurance -- governance, explainability, auditability, "
    "and validation traceability -- for AI capabilities built into this platform. It stores "
    "references and supports traceability to organizational requirements; it does not claim "
    "regulatory certification or clearance. Every score, explanation, and risk entry describes "
    "a potential association or documented limitation only, requires human review, and is "
    "never a substitute for clinical judgment."
)


class AIModelRiskEntry(Base):
    """One entry in the AI Risk Registry (Section 5) for a given
    `AIModelRegistryEntry` (Olympus, v5.1) -- many rows per model, since a
    model typically has several distinct risks/biases/failure modes."""

    __tablename__ = "guardianx_ai_model_risk_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    model_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    risk_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    mitigation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default=SEVERITY_MEDIUM, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=RISK_OPEN, nullable=False, index=True)
    identified_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class ComplianceCapabilityMapping(Base):
    """Maps one platform capability to an organizational requirement
    reference (Section 7) -- a traceability record, never a certification
    claim. `requirement_reference` is a free-text citation (an internal
    SOP number, an AAMI/AORN standard id from
    `regulatory_standards_catalogue.py`, a manufacturer IFU document,
    or an organizational policy name)."""

    __tablename__ = "guardianx_compliance_capability_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    capability_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    capability_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requirement_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    requirement_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    traceability_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    mapped_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class EvidenceLedgerEntry(Base):
    """One append-only evidence record for an AI recommendation (Section 8).

    Nothing is deleted: no service function in
    `guardianx_evidence_ledger_service.py` updates or removes a row.
    `digital_signature` is the real SHA-256 `event_hash` returned by a
    paired `enterprise_audit_service.record_enterprise_audit_event` call
    -- never a fabricated signature.
    """

    __tablename__ = "guardianx_evidence_ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    knowledge_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)

    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    digital_signature: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class AIAssuranceTrustSnapshot(Base):
    """A point-in-time trust score for one of the five named scopes
    (Section 9) -- one generic snapshot table with a `scope`
    discriminator rather than five separate tables, following the same
    pattern as `NetworkGovernanceCase` (Olympus)."""

    __tablename__ = "guardianx_trust_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    scope: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_ref_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    components_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AIExplainabilityRecord(Base):
    """A structured explanation for one AI output (Section 3), referenced
    by `source_type`/`source_id` rather than copying the underlying
    recommendation. Every named field in Section 3 is a real column:
    input summary, evidence used, knowledge sources, Digital Twin
    context, clinical rules applied, confidence, alternative
    explanations, and human overrides.
    """

    __tablename__ = "guardianx_explainability_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    input_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_used_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    knowledge_sources_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    digital_twin_context_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    clinical_rules_applied_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    alternative_explanations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    human_overrides_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
