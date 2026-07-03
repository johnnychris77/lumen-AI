"""Phase 23 §5 — Clinical Decision Ledger.

A permanent, append-only record of every decision made about an
inspection: who made it (AI or a named supervisor), why, what evidence
supported it, how confident it was, and which platform versions were
active at the time. Entries are never edited or deleted — a correction is
a new entry, not a rewrite (the same append-only pattern as AuditLog and
PilotValidationCase).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClinicalDecisionLedgerEntry(Base):
    __tablename__ = "clinical_decision_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # ai_recommendation | supervisor_approval | supervisor_override
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    made_by: Mapped[str] = mapped_column(String(255), nullable=False)  # "ai" or a reviewer's email
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Governance version snapshot at the moment this decision was recorded —
    # never recomputed from current constants after the fact.
    model_version: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    knowledge_graph_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    ontology_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    architecture_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    inspection_pipeline_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
