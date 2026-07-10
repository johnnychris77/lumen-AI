"""v2.5 — Supervisor Rule Builder (Project Cortex, Section 7).

Governed, versioned clinical decision rules a supervisor authors — organization
rules, local best practices, escalation thresholds, education rules. Distinct
from the built-in `SPD_RULE_LIBRARY` (curated, code-shipped, immutable) and
from `AutomationRule` (workflow/notification automation, unrelated to clinical
reasoning) — this is the only persisted, supervisor-editable clinical rule
table. Editing a rule never mutates history in place: `update_rule` creates a
new row at `version + 1` and deactivates the prior version, so a rule's
effective state at any point in time is always reconstructable.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

RULE_TYPES = ("organization_rule", "local_best_practice", "escalation_threshold", "education_rule")


class ClinicalDecisionRule(Base):
    __tablename__ = "clinical_decision_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    rule_type: Mapped[str] = mapped_column(String(30), default="local_best_practice", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Evidence conditions — same shape as SPDRule, kept flat (not JSON) so
    # they're queryable/filterable, since supervisors author one condition
    # set per rule rather than the compound OR-of-keywords the static
    # library uses.
    finding_type: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    zone_keyword: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    requires_high_risk_zone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_repeat_finding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_repeat_occurrences: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    severity: Mapped[str] = mapped_column(String(20), default="Moderate", nullable=False)
    spd_risk: Mapped[str] = mapped_column(String(20), default="Moderate", nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list[str]

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    superseded_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
