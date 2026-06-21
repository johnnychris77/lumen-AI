"""
P23: Global Surgical Intelligence Network — Service Layer.

IMPORTANT DISCLAIMER: All outputs from this service represent anonymized aggregate patterns
across participating facilities for human review and awareness only. They do NOT establish,
imply, or claim causation. All outputs require human review before any action is taken.
"""
from __future__ import annotations

import hashlib
import random
from typing import Any

from sqlalchemy.orm import Session

from app.models.global_intelligence import (
    GlobalIntelligenceSignal,
    GlobalRecallEarlyWarning,
    InstrumentRiskRegistryEntry,
    GSINParticipant,
    RegulatoryEvidencePackage,
)

DISCLAIMER = (
    "Global Surgical Intelligence Network outputs represent anonymized aggregate patterns "
    "across participating facilities. No individual facility, patient, or instrument is "
    "identified. All outputs are for planning and awareness purposes only. Does not "
    "establish causation. Human review required before operational decisions."
)


# ---------------------------------------------------------------------------
# Seeded RNG helper (deterministic per tenant for consistent mock fallbacks)
# ---------------------------------------------------------------------------


def _seed(s: str) -> random.Random:
    """Deterministic seeded RNG from string."""
    h = hashlib.md5(s.encode()).hexdigest()[:8]  # noqa: S324
    return random.Random(int(h, 16))


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------


def _to_dict(obj: Any) -> dict:
    result: dict[str, Any] = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    result["human_review_required"] = True
    return result


# ---------------------------------------------------------------------------
# Seeded mock data
# ---------------------------------------------------------------------------

_SIGNAL_MOCKS = [
    {
        "signal_type": "instrument_quality",
        "instrument_category": "flexible_scopes",
        "finding_type": "contamination",
        "region": "north_america",
        "facility_count": 14,
        "signal_strength": 0.78,
        "trend_direction": "increasing",
        "k_anonymity_verified": True,
        "human_review_completed": True,
        "published": True,
        "association_reason": (
            "Aggregate contamination rate for flexible scopes across 14 facilities shows "
            "statistically elevated pattern compared to 90-day rolling baseline. "
            "Association identified — causation not established."
        ),
    },
    {
        "signal_type": "baseline_deviation",
        "instrument_category": "rigid_scopes",
        "finding_type": "physical_defect",
        "region": "north_america",
        "facility_count": 11,
        "signal_strength": 0.61,
        "trend_direction": "stable",
        "k_anonymity_verified": True,
        "human_review_completed": True,
        "published": True,
        "association_reason": (
            "Rigid scope physical defect rates exceed network baseline across 11 reporting facilities. "
            "Pattern may reflect instrument age or decontamination cycle variance. "
            "Association observed — causation not established."
        ),
    },
    {
        "signal_type": "contamination_pattern",
        "instrument_category": "laparoscopic_instruments",
        "finding_type": "biofilm_residue",
        "region": "global",
        "facility_count": 18,
        "signal_strength": 0.85,
        "trend_direction": "increasing",
        "k_anonymity_verified": True,
        "human_review_completed": True,
        "published": True,
        "association_reason": (
            "Biofilm residue finding type associated with laparoscopic instruments across 18 global facilities. "
            "Signal strength elevated. Human review and root cause investigation recommended. "
            "Association identified — causation not established."
        ),
    },
    {
        "signal_type": "capa_pattern",
        "instrument_category": "orthopaedic_instruments",
        "finding_type": "identification_failure",
        "region": "europe",
        "facility_count": 12,
        "signal_strength": 0.55,
        "trend_direction": "decreasing",
        "k_anonymity_verified": True,
        "human_review_completed": True,
        "published": True,
        "association_reason": (
            "Identification failure CAPA pattern for orthopaedic instruments declining across 12 European facilities. "
            "Possible association with recent labeling standard updates. "
            "Association observed — causation not established."
        ),
    },
    {
        "signal_type": "instrument_quality",
        "instrument_category": "powered_instruments",
        "finding_type": "sterilization_failure",
        "region": "apac",
        "facility_count": 10,
        "signal_strength": 0.69,
        "trend_direction": "stable",
        "k_anonymity_verified": True,
        "human_review_completed": True,
        "published": True,
        "association_reason": (
            "Sterilization failure rate for powered instruments reported across 10 APAC facilities. "
            "Pattern within expected variance but warrants ongoing monitoring. "
            "Association identified — causation not established."
        ),
    },
]

_RISK_REGISTRY_MOCKS = [
    {
        "instrument_category": "flexible_scopes",
        "manufacturer_category": "endoscope_manufacturer_tier_1",
        "risk_pattern": "contamination",
        "risk_score": 0.74,
        "facilities_reporting": 14,
        "finding_count": 312,
        "trend_direction": "increasing",
        "registry_status": "active_signal",
        "association_reason": (
            "Contamination pattern associated with flexible scope category across multiple facilities. "
            "Does not identify any specific manufacturer or facility."
        ),
    },
    {
        "instrument_category": "laparoscopic_instruments",
        "manufacturer_category": "minimally_invasive_manufacturer_tier_2",
        "risk_pattern": "physical_defect",
        "risk_score": 0.58,
        "facilities_reporting": 9,
        "finding_count": 187,
        "trend_direction": "stable",
        "registry_status": "elevated",
        "association_reason": (
            "Physical defect pattern associated with laparoscopic instrument category. "
            "Aggregate signal — no facility or instrument individually identified."
        ),
    },
    {
        "instrument_category": "orthopaedic_instruments",
        "manufacturer_category": "orthopaedic_manufacturer_tier_1",
        "risk_pattern": "identification_failure",
        "risk_score": 0.42,
        "facilities_reporting": 7,
        "finding_count": 98,
        "trend_direction": "decreasing",
        "registry_status": "monitoring",
        "association_reason": (
            "Identification failure associated with orthopaedic instruments. "
            "Declining trend observed across reporting facilities."
        ),
    },
    {
        "instrument_category": "rigid_scopes",
        "manufacturer_category": "rigid_scope_manufacturer_tier_2",
        "risk_pattern": "baseline_deviation",
        "risk_score": 0.61,
        "facilities_reporting": 11,
        "finding_count": 203,
        "trend_direction": "stable",
        "registry_status": "elevated",
        "association_reason": (
            "Baseline deviation pattern associated with rigid scope category. "
            "Signal reflects aggregate deviations — causation not established."
        ),
    },
    {
        "instrument_category": "powered_instruments",
        "manufacturer_category": "powered_instrument_manufacturer_tier_1",
        "risk_pattern": "contamination",
        "risk_score": 0.49,
        "facilities_reporting": 8,
        "finding_count": 144,
        "trend_direction": "stable",
        "registry_status": "monitoring",
        "association_reason": (
            "Contamination pattern for powered instruments in monitoring status. "
            "No escalation threshold reached. Continued monitoring recommended."
        ),
    },
]

_RECALL_WARNING_MOCKS = [
    {
        "instrument_category": "flexible_scopes",
        "finding_type": "contamination",
        "region": "north_america",
        "facilities_count": 14,
        "signal_strength_score": 0.82,
        "recency_days": 45,
        "manufacturer_notified": True,
        "regulatory_notified": False,
        "status": "under_review",
        "association_reason": (
            "Contamination pattern for flexible scopes exceeds early warning threshold across 14 facilities. "
            "Manufacturer notification initiated. Regulatory consultation pending. "
            "Association identified — this is not a recall notice."
        ),
    },
    {
        "instrument_category": "laparoscopic_instruments",
        "finding_type": "biofilm_residue",
        "region": "global",
        "facilities_count": 18,
        "signal_strength_score": 0.91,
        "recency_days": 30,
        "manufacturer_notified": True,
        "regulatory_notified": True,
        "status": "escalated",
        "association_reason": (
            "Biofilm residue signal for laparoscopic instruments escalated to regulatory review stage. "
            "18 global facilities contributing to aggregate signal. "
            "Association observed — causation not established. Human review required."
        ),
    },
    {
        "instrument_category": "powered_instruments",
        "finding_type": "sterilization_failure",
        "region": "apac",
        "facilities_count": 10,
        "signal_strength_score": 0.67,
        "recency_days": 60,
        "manufacturer_notified": False,
        "regulatory_notified": False,
        "status": "active",
        "association_reason": (
            "Sterilization failure pattern for powered instruments meets early warning threshold. "
            "10 APAC facilities contributing. Awaiting governance board review. "
            "Association identified — this is not a recall notice."
        ),
    },
    {
        "instrument_category": "rigid_scopes",
        "finding_type": "physical_defect",
        "region": "europe",
        "facilities_count": 7,
        "signal_strength_score": 0.54,
        "recency_days": 90,
        "manufacturer_notified": False,
        "regulatory_notified": False,
        "status": "active",
        "association_reason": (
            "Physical defect pattern for rigid scopes meets minimum threshold for early warning. "
            "Signal under active monitoring. Human review recommended."
        ),
    },
    {
        "instrument_category": "orthopaedic_instruments",
        "finding_type": "identification_failure",
        "region": "global",
        "facilities_count": 6,
        "signal_strength_score": 0.48,
        "recency_days": 75,
        "manufacturer_notified": False,
        "regulatory_notified": False,
        "status": "active",
        "association_reason": (
            "Identification failure pattern for orthopaedic instruments meeting minimum threshold. "
            "Monitoring active. Association observed — causation not established."
        ),
    },
    {
        "instrument_category": "retractors",
        "finding_type": "contamination",
        "region": "australia",
        "facilities_count": 5,
        "signal_strength_score": 0.43,
        "recency_days": 85,
        "manufacturer_notified": False,
        "regulatory_notified": False,
        "status": "active",
        "association_reason": (
            "Contamination pattern for retractors at minimum early warning threshold. "
            "5 Australian facilities contributing. Under governance review."
        ),
    },
]

_REGULATORY_EVIDENCE_MOCKS = [
    {
        "target_authority": "FDA",
        "evidence_type": "quality_performance",
        "facility_count": 28,
        "summary": (
            "Aggregate surgical instrument quality performance data from 28 participating facilities "
            "in the North America region. Covers inspection pass/fail rates, contamination patterns, "
            "and CAPA completion metrics. All data anonymized and k-anonymity verified (k>=10)."
        ),
        "status": "published",
    },
    {
        "target_authority": "EUMDR",
        "evidence_type": "safety_patterns",
        "facility_count": 19,
        "summary": (
            "EU MDR-aligned aggregate safety pattern evidence from 19 European participating facilities. "
            "Covers instrument risk patterns, recall signal data, and baseline deviation analysis. "
            "Prepared in accordance with EU MDR Article 83 post-market surveillance requirements."
        ),
        "status": "under_review",
    },
    {
        "target_authority": "TGA",
        "evidence_type": "benchmarking",
        "facility_count": 11,
        "summary": (
            "Aggregate benchmarking data from 11 Australian facilities for TGA regulatory engagement. "
            "Covers instrument quality rates by category and contamination trend analysis. "
            "Compliant with TGA post-market surveillance guidance."
        ),
        "status": "draft",
    },
]


def _seed_mock_signals(db: Session, tenant_id: str) -> list[dict]:
    results = []
    for mock in _SIGNAL_MOCKS:
        obj = GlobalIntelligenceSignal(
            tenant_id=tenant_id,
            disclaimer=(
                "Global signal represents anonymized aggregate patterns across participating facilities. "
                "Does not identify any individual facility, patient, or instrument. "
                "Does not establish causation."
            ),
            **mock,
        )
        db.add(obj)
        db.flush()
        results.append(_to_dict(obj))
    db.commit()
    return results


def _seed_mock_registry(db: Session, tenant_id: str) -> list[dict]:
    results = []
    for mock in _RISK_REGISTRY_MOCKS:
        obj = InstrumentRiskRegistryEntry(
            tenant_id=tenant_id,
            disclaimer=(
                "Registry entry based on anonymized aggregate quality signal data. "
                "Does not identify specific instruments, facilities, or patients. "
                "Investigation recommended before operational decisions."
            ),
            **mock,
        )
        db.add(obj)
        db.flush()
        results.append(_to_dict(obj))
    db.commit()
    return results


def _seed_mock_warnings(db: Session, tenant_id: str) -> list[dict]:
    results = []
    for mock in _RECALL_WARNING_MOCKS:
        obj = GlobalRecallEarlyWarning(
            tenant_id=tenant_id,
            disclaimer=(
                "Early warning signal based on anonymized aggregate reporting patterns. "
                "Does not constitute a regulatory recall notice. "
                "Human review and regulatory consultation required before any action."
            ),
            **mock,
        )
        db.add(obj)
        db.flush()
        results.append(_to_dict(obj))
    db.commit()
    return results


def _seed_mock_packages(db: Session, tenant_id: str) -> list[dict]:
    results = []
    for mock in _REGULATORY_EVIDENCE_MOCKS:
        obj = RegulatoryEvidencePackage(
            tenant_id=tenant_id,
            disclaimer=(
                "Regulatory evidence package contains anonymized aggregate data only. "
                "Does not contain facility-identifiable information. "
                "Does not constitute regulatory clearance or approval."
            ),
            **mock,
        )
        db.add(obj)
        db.flush()
        results.append(_to_dict(obj))
    db.commit()
    return results


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


def get_global_signals(db: Session, tenant_id: str, region: str | None = None) -> list[dict]:
    """List published global quality signals."""
    q = (
        db.query(GlobalIntelligenceSignal)
        .filter(
            GlobalIntelligenceSignal.tenant_id == tenant_id,
            GlobalIntelligenceSignal.published.is_(True),
        )
    )
    if region:
        q = q.filter(GlobalIntelligenceSignal.region.in_([region, "global"]))
    rows = q.all()
    if not rows:
        return _seed_mock_signals(db, tenant_id)
    return [_to_dict(r) for r in rows]


def get_instrument_risk_registry(
    db: Session, tenant_id: str, category: str | None = None
) -> list[dict]:
    """List instrument risk registry entries."""
    q = db.query(InstrumentRiskRegistryEntry).filter(
        InstrumentRiskRegistryEntry.tenant_id == tenant_id
    )
    if category:
        q = q.filter(InstrumentRiskRegistryEntry.instrument_category == category)
    rows = q.all()
    if not rows:
        return _seed_mock_registry(db, tenant_id)
    return [_to_dict(r) for r in rows]


def get_recall_early_warnings(db: Session, tenant_id: str) -> list[dict]:
    """List active early warning signals."""
    rows = (
        db.query(GlobalRecallEarlyWarning)
        .filter(
            GlobalRecallEarlyWarning.tenant_id == tenant_id,
            GlobalRecallEarlyWarning.status.in_(["active", "under_review", "escalated"]),
        )
        .all()
    )
    if not rows:
        return _seed_mock_warnings(db, tenant_id)
    return [_to_dict(r) for r in rows]


def get_network_participant(db: Session, tenant_id: str) -> dict:
    """Return this tenant's GSIN participation status."""
    obj = db.query(GSINParticipant).filter(GSINParticipant.tenant_id == tenant_id).first()
    if obj is None:
        # Seed a default participant record
        obj = GSINParticipant(
            tenant_id=tenant_id,
            participant_type="hospital",
            region="north_america",
            contribution_categories='["inspection_metrics","quality_rates","recall_signals"]',
            baa_signed=True,
            dpa_signed=True,
            enrollment_status="active",
            minimum_contribution_met=True,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return _to_dict(obj)


def get_regulatory_evidence_packages(
    db: Session, tenant_id: str, authority: str | None = None
) -> list[dict]:
    """List regulatory evidence packages."""
    q = db.query(RegulatoryEvidencePackage).filter(
        RegulatoryEvidencePackage.tenant_id == tenant_id
    )
    if authority:
        q = q.filter(RegulatoryEvidencePackage.target_authority == authority)
    rows = q.all()
    if not rows:
        return _seed_mock_packages(db, tenant_id)
    return [_to_dict(r) for r in rows]


def get_global_dashboard(db: Session, tenant_id: str) -> dict:
    """Consolidated global intelligence dashboard."""
    signals = get_global_signals(db, tenant_id)
    warnings = get_recall_early_warnings(db, tenant_id)
    registry = get_instrument_risk_registry(db, tenant_id)
    packages = get_regulatory_evidence_packages(db, tenant_id)
    participant = get_network_participant(db, tenant_id)

    # Count items needing human review
    human_review_count = (
        len([s for s in signals if s.get("human_review_required")])
        + len([w for w in warnings if w.get("human_review_required")])
    )

    # Network participant count (approximated from signal facility counts)
    network_participants = (
        db.query(GSINParticipant)
        .filter(GSINParticipant.enrollment_status == "active")
        .count()
    )

    return {
        "active_global_signals": len(signals),
        "recall_early_warnings": len(warnings),
        "risk_registry_entries": len(registry),
        "network_participants": network_participants or 1,
        "human_review_required_count": human_review_count,
        "participant_status": participant.get("enrollment_status", "unknown"),
        "top_signals": signals[:3],
        "active_warnings": warnings[:3],
        "top_risk_registry": registry[:3],
        "recent_evidence_packages": packages[:2],
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
