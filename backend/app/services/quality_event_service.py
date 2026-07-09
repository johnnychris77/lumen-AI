"""v2.9 — LumenAI Quality (Project Guardian), Sections 1-2: Quality Event
Intake Engine + Clinical NLP Classification Engine.

Classification is a deterministic keyword classifier, not a statistical NLP
model — consistent with the rest of this codebase's rule-based agents
(`contamination_agent.py`, `damage_agent.py`), which never fabricate a
confidence score from an opaque model. The original narrative is never
overwritten by classification; classification fields are separate, nullable
columns populated alongside it.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.quality_guardian import DISCLAIMER, SOURCE_MANUAL, SOURCE_SYSTEMS, QualityEvent
from app.services.quality_taxonomy_service import category_for_term

# Explicit priority order (first match wins) — deliberately NOT sorted by
# raw keyword length. Compound phrases come first so "missing instrument"
# wins over a bare "instrument"; specific findings (blood/bone/tissue/...)
# come before generic catch-all words (debris/residue/wear/worn) so a
# narrative like "blood residue" classifies as the more specific "blood"
# rather than the generic "debris".
_KEYWORD_TO_FINDING: dict[str, str] = {
    "missing instrument": "missing_instrument",
    "wrong instrument": "wrong_instrument",
    "missing component": "missing_component",
    "missing piece": "missing_component",
    "wet tray": "wet_tray",
    "wet pack": "wet_tray",
    "wrapper tear": "wrapper_tear",
    "torn wrapper": "wrapper_tear",
    "wrapper torn": "wrapper_tear",
    "filter failure": "filter_failure",
    "filter failed": "filter_failure",
    "missing lock": "missing_lock",
    "lock missing": "missing_lock",
    "failed indicator": "failed_indicator",
    "indicator failed": "failed_indicator",
    "missing indicator": "missing_indicator",
    "bone fragment": "bone",
    "bloody": "blood",
    "blood": "blood",
    "bone": "bone",
    "tissue": "tissue",
    "proteinaceous": "protein",
    "protein": "protein",
    "rust": "rust",
    "corroded": "corrosion",
    "corrosion": "corrosion",
    "pitted": "pitting",
    "pitting": "pitting",
    "cracked": "crack",
    "crack": "crack",
    "worn": "wear",
    "wear": "wear",
    "debris": "debris",
    "residue": "debris",
}

_INSTRUMENT_KEYWORDS: dict[str, str] = {
    "yankauer": "yankauer_suction",
    "suction": "yankauer_suction",
    "kerrison": "kerrison_rongeur",
    "rongeur": "kerrison_rongeur",
    "needle holder": "needle_holder",
    "scissors": "scissors",
    "forceps": "forceps",
    "drill": "drill_bit",
    "endoscope": "flexible_endoscope",
    "scope": "rigid_scope",
}

_RISK_BY_CATEGORY = {
    "organic_residue": "high",
    "instrument_condition": "medium",
    "assembly": "high",
    "packaging": "high",
    "sterilization_indicators": "critical",
    "unknown": "medium",
}


class QualityEventNotFoundError(Exception):
    pass


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def classify_narrative(narrative: str) -> dict:
    """Section 2 — translate a free-text narrative into structured SPD
    terminology. Always deterministic; the same narrative always classifies
    the same way."""
    text = (narrative or "").lower()

    matched_finding: str | None = None
    for keyword, finding in _KEYWORD_TO_FINDING.items():
        if keyword in text:
            matched_finding = finding
            break

    matched_instrument: str | None = None
    for keyword in sorted(_INSTRUMENT_KEYWORDS, key=len, reverse=True):
        if keyword in text:
            matched_instrument = _INSTRUMENT_KEYWORDS[keyword]
            break

    if matched_finding is None:
        return {
            "instrument_type_guess": matched_instrument, "finding_type": "unknown",
            "spd_category": "unknown", "risk_level": "medium", "confidence": 0.35,
            "requires_supervisor_classification": True,
        }

    category = category_for_term(matched_finding)
    confidence = 0.98 if matched_instrument else 0.75
    return {
        "instrument_type_guess": matched_instrument, "finding_type": matched_finding,
        "spd_category": category, "risk_level": _RISK_BY_CATEGORY.get(category, "medium"),
        "confidence": confidence, "requires_supervisor_classification": False,
    }


def create_event(
    db: Session, tenant_id: str, *, event_date: datetime, narrative: str, source_system: str = SOURCE_MANUAL,
    external_event_id: str = "", facility_name: str = "", procedure: str = "", service_line: str = "",
    case_id: int | None = None, reporter_role: str = "", severity: str = "medium",
    attachments: list[str] | None = None, auto_classify: bool = True,
) -> dict:
    if source_system not in SOURCE_SYSTEMS:
        raise ValueError(f"source_system must be one of {SOURCE_SYSTEMS}")

    event_ref = f"QE-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
    event = QualityEvent(
        tenant_id=tenant_id, event_ref=event_ref, source_system=source_system,
        external_event_id=external_event_id, event_date=event_date, facility_name=facility_name,
        procedure=procedure, service_line=service_line, case_id=case_id, narrative=narrative,
        reporter_role=reporter_role, severity=severity, attachments_json=json.dumps(attachments or []),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    if auto_classify:
        return classify_event(db, tenant_id, event.id)
    return _row_to_dict(event)


def classify_event(db: Session, tenant_id: str, event_id: int) -> dict:
    event = _get_event(db, tenant_id, event_id)
    classification = classify_narrative(event.narrative)

    event.instrument_type_guess = classification["instrument_type_guess"]
    event.finding_type = classification["finding_type"]
    event.spd_category = classification["spd_category"]
    event.classification_risk_level = classification["risk_level"]
    event.classification_confidence = classification["confidence"]
    event.requires_supervisor_classification = classification["requires_supervisor_classification"]
    event.classified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return _row_to_dict(event)


def import_events_csv(db: Session, tenant_id: str, rows: list[dict], *, source_system: str) -> dict:
    """Section 1 — bulk CSV import (SafeCare/RLDatix/MIDAS/occurrence-report
    exports all reduce to the same normalized row shape)."""
    created = []
    errors = []
    for i, row in enumerate(rows):
        try:
            event_date = row.get("event_date")
            if isinstance(event_date, str):
                event_date = datetime.fromisoformat(event_date)
            result = create_event(
                db, tenant_id, event_date=event_date, narrative=row.get("narrative", ""),
                source_system=source_system, external_event_id=row.get("external_event_id", ""),
                facility_name=row.get("facility_name", ""), procedure=row.get("procedure", ""),
                service_line=row.get("service_line", ""), case_id=row.get("case_id"),
                reporter_role=row.get("reporter_role", ""), severity=row.get("severity", "medium"),
            )
            created.append(result)
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": i, "error": str(exc)})
    return {"created_count": len(created), "error_count": len(errors), "events": created, "errors": errors}


def _get_event(db: Session, tenant_id: str, event_id: int) -> QualityEvent:
    event = (
        db.query(QualityEvent)
        .filter(QualityEvent.id == event_id, QualityEvent.tenant_id == tenant_id)
        .first()
    )
    if event is None:
        raise QualityEventNotFoundError(f"Quality event {event_id} not found for tenant {tenant_id}.")
    return event


def get_event(db: Session, tenant_id: str, event_id: int) -> dict:
    return _row_to_dict(_get_event(db, tenant_id, event_id))


def list_events(db: Session, tenant_id: str, *, severity: str = "", finding_type: str = "", limit: int = 100) -> list[dict]:
    q = db.query(QualityEvent).filter(QualityEvent.tenant_id == tenant_id)
    if severity:
        q = q.filter(QualityEvent.severity == severity)
    if finding_type:
        q = q.filter(QualityEvent.finding_type == finding_type)
    rows = q.order_by(QualityEvent.id.desc()).limit(limit).all()
    return [_row_to_dict(r) for r in rows]


def confirm_event(db: Session, tenant_id: str, event_id: int, *, confirmed_by: str) -> dict:
    """Section 10 trigger point — marks an event confirmed, which the
    Quality Learning Loop (`quality_command_center_service.apply_learning_loop`)
    treats as the signal to update Clinical Memory."""
    event = _get_event(db, tenant_id, event_id)
    event.confirmed = True
    event.confirmed_by = confirmed_by
    event.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    result = _row_to_dict(event)
    result["disclaimer"] = DISCLAIMER
    return result
