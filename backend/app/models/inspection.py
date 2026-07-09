from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), default="Default Tenant", nullable=False)

    stain_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    material_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)

    model_name: Mapped[str] = mapped_column(String(100), default="lumenai-baseline", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="0.1.0", nullable=False)
    inference_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    instrument_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    detected_issue: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    inference_mode: Mapped[str] = mapped_column(String(50), default="deterministic-fallback", nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    vendor_name: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    site_name: Mapped[str] = mapped_column(String(100), default="default-site", nullable=False)

    # Pilot Sprint 7 additions — facility/department/tray and instrument identity
    facility_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tray_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instrument_barcode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instrument_udi: Mapped[str | None] = mapped_column(String(255), nullable=True)

    alert_status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    alert_owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    alert_notes: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    alert_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    alert_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    qa_review_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    qa_reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    qa_review_notes: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    qa_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    qa_override_stain_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    qa_override_material_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    qa_override_instrument_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    qa_override_detected_issue: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    qa_override_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Phase 14 — baseline governance
    has_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    baseline_status: Mapped[str] = mapped_column(String(50), default="not_checked", nullable=False)
    baseline_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    supervisor_review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    override_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    override_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # SPD risk-weighted verdict — persisted so dashboard/history reflect the SPD
    # disposition, not just the live analysis panel.
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overall_cleaning_assessment: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # v1.4 — the technician who submitted the inspection (request actor at
    # creation time), so the SPD Mentor Engine's competency service can
    # attribute findings-reviewed/supervisor-corrections to a real person
    # instead of fabricating attribution. Nullable/blank for older rows.
    technician: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # v1.5 — Quality Intelligence. `disposition` is the one of
    # PASS/MONITOR/SUPERVISOR REVIEW/REPROCESS/REMOVE FROM SERVICE computed at
    # analysis time (clinical_decision.overall_result) — persisted so pass
    # rate/reclean rate/remove-from-service rate can be reported later without
    # re-deriving analysis. `coverage_pct`/`coverage_quality` are the
    # Inspection Coverage Engine's result at submission time, persisted for
    # the same reason (coverage compliance reporting). All nullable/blank for
    # older rows or inspections with no image.
    disposition: Mapped[str | None] = mapped_column(String(30), nullable=True)
    coverage_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coverage_quality: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # v1.5 — the AI-computed analysis confidence (0-1), distinct from the
    # pre-existing `confidence` column above (a client-supplied manual-entry
    # field for the no-image path). Persisted so "AI Confidence Trend" can be
    # reported without re-deriving analysis.
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Zones the technician tagged as inspected (anatomy-aware coverage engine).
    # JSON-encoded: "null" means not tagged (coverage not_assessed), "[...]" is
    # an explicit (possibly empty) list — see app/services/inspection_coverage.py.
    inspected_zones_json: Mapped[str] = mapped_column(String(2000), default="null", nullable=False)

    # v1.2 — Guided Capture & Coverage Gate. coverage_status/coverage_score are
    # a snapshot of compute_coverage() at creation time (so history/dashboards
    # don't need to recompute it); coverage_gate_status governs whether the
    # inspection can proceed to a final AI decision without a supervisor
    # override, when org policy requires full coverage. NOTE: overlaps in
    # purpose with v1.5's coverage_pct/coverage_quality above (independently
    # added by a parallel phase) — a future cleanup should consolidate these;
    # both are kept for now since each phase's dashboards already read from
    # its own field.
    coverage_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    coverage_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # ready | draft | blocked_pending_override
    coverage_gate_status: Mapped[str] = mapped_column(String(30), default="ready", nullable=False)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    coverage_override_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    coverage_override_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    coverage_override_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # v1.7 — Workflow Intelligence. Real OR-urgency/loaner signal declared at
    # intake time, used by the prioritization engine. Nullable/blank for older
    # rows and for inspections where no procedure context was declared — never
    # fabricated as "routine" when actually unknown.
    # emergency | trauma | first_case | routine | None
    procedure_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_loaner_instrument: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # v2.8 — OR Connect / Project Symphony. Links this inspection to a
    # SurgicalCase (app.models.or_connect) so case-level readiness can be
    # derived from real linked inspections instead of duplicating their state.
    # Nullable — most inspections are not tied to a scheduled OR case.
    case_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
