"""v2.4 — Clinical Memory Engine (Project Insight, Section 1).

The central "does this instrument have a history" service. Composes:

- `instrument_condition_service.instrument_condition_history` — inspection/
  finding/repair/supervisor-comment history + condition trend (reused, not
  re-derived).
- `recurrence_detection_service.detect_recurring_issues` — repeated finding
  types, repairs, overrides (Section 3).
- `predictive_risk_engine.estimate_predictive_risk` — Low/Moderate/High/
  Critical likelihood per outcome (Section 4).
- `instrument_health_forecast_service.forecast_instrument_health` — condition/
  failure/repair trend + remaining-useful-life + confidence interval
  (Section 5).
- `similar_instrument_search_service.find_similar_instruments` — fleet-wide
  similarity search (Section 2).
- `knowledge_repository_service.list_articles` — applicable knowledge
  articles for this instrument type.
- `build_memory_timeline` — the interactive Inspection -> Finding -> Repair ->
  Supervisor Note -> ... -> Current sequence (Section 7).
- `build_memory_recommendation` — one narrative recommendation enriched by
  this instrument's own recurring history (Section 9).

Nothing here re-runs AI scoring or invents a new instrument-identity scheme —
`instrument_identity` is always `barcode:<value>` or `udi:<value>`, the same
key `instrument_condition_service`/`prioritization_engine` already use.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.inspection_finding import InspectionFinding
from app.services.instrument_condition_service import instrument_condition_history
from app.services.instrument_health_forecast_service import forecast_instrument_health
from app.services.knowledge_repository_service import list_articles
from app.services.predictive_risk_engine import estimate_predictive_risk
from app.services.recurrence_detection_service import detect_recurring_issues
from app.services.similar_instrument_search_service import find_similar_instruments

_KNOWLEDGE_ARTICLE_LIMIT = 5
_RECOMMENDATION_ELEVATE_THRESHOLD = 3


def build_memory_timeline(condition: dict) -> list[dict]:
    """Section 7 — interactive timeline: Inspection -> Finding -> Repair ->
    Supervisor Note, in the same chronological order the history already is,
    followed by a terminal "current" marker."""
    events: list[dict] = []
    for entry in condition["history"]:
        events.append({
            "type": "inspection",
            "inspection_id": entry["inspection_id"],
            "date": entry["date"],
            "disposition": entry["disposition"],
        })
        findings = entry["cleaning_findings"] + entry["damage_findings"]
        if findings:
            events.append({
                "type": "finding",
                "inspection_id": entry["inspection_id"],
                "date": entry["date"],
                "findings": findings,
            })
        if entry["repair_flag"]:
            events.append({
                "type": "repair",
                "inspection_id": entry["inspection_id"],
                "date": entry["date"],
            })
        for note in entry["supervisor_comments"]:
            events.append({
                "type": "supervisor_note",
                "inspection_id": entry["inspection_id"],
                "date": entry["date"],
                "note": note,
            })
    events.append({"type": "current", "date": None})
    return events


def build_memory_recommendation(db: Session, tenant_id: str, condition: dict, recurrence: dict) -> dict | None:
    """Section 9 — one memory-driven recommendation naming the specific
    recurring finding/zone pair, when one exists. Returns None rather than a
    generic filler when there's nothing recurring to call out."""
    repeated = {
        finding_type: count
        for finding_type, count in recurrence["finding_counts"].items()
        if count >= 2
    }
    if not repeated:
        return None

    inspection_ids = [entry["inspection_id"] for entry in condition["history"]]
    if not inspection_ids:
        return None

    rows = (
        db.query(InspectionFinding)
        .filter(
            InspectionFinding.tenant_id == tenant_id,
            InspectionFinding.inspection_id.in_(inspection_ids),
            InspectionFinding.finding_type.in_(repeated),
        )
        .all()
    )
    if not rows:
        return None

    # Prefer whichever recurring finding type shows up in the most recent
    # inspection (most clinically relevant right now); fall back to the
    # overall most-recurring type if none of them recur in the latest visit.
    latest_inspection_id = inspection_ids[-1]
    latest_types = {r.finding_type for r in rows if r.inspection_id == latest_inspection_id}
    candidate_type = max(latest_types or repeated, key=lambda ft: repeated[ft])

    type_rows = [r for r in rows if r.finding_type == candidate_type]
    zone_counts: dict[str, int] = {}
    for r in type_rows:
        zone_counts[r.zone] = zone_counts.get(r.zone, 0) + 1
    zone = max(zone_counts, key=lambda z: zone_counts[z]) if zone_counts else ""

    occurrences = repeated[candidate_type]
    zone_label = zone or "the inspected area"
    finding_label = candidate_type.replace("_", " ")
    inspection_count = condition["inspection_count"]

    message = (
        f"{finding_label.capitalize()} was identified in the {zone_label}. "
        f"This instrument has had {occurrences} similar findings in the {zone_label} "
        f"over the last {inspection_count} inspection{'s' if inspection_count != 1 else ''}. "
        f"Recommend focused manual cleaning of the {zone_label}"
        + (
            " and supervisor review."
            if occurrences >= _RECOMMENDATION_ELEVATE_THRESHOLD
            else "."
        )
    )
    return {
        "finding_type": candidate_type,
        "zone": zone,
        "occurrences": occurrences,
        "message": message,
        "human_review_required": True,
    }


def get_clinical_memory(db: Session, tenant_id: str, instrument_identity: str) -> dict | None:
    """The full Clinical Memory context for one instrument, or None when
    there's no recorded history for it (untracked, or genuinely first-seen)."""
    condition = instrument_condition_history(db, tenant_id, instrument_identity)
    if condition is None:
        return None

    recurrence = detect_recurring_issues(db, tenant_id, condition)
    predictive_risk = estimate_predictive_risk(condition, recurrence)
    health_forecast = forecast_instrument_health(db, tenant_id, instrument_identity, condition)
    similar_instruments = find_similar_instruments(db, tenant_id, instrument_identity=instrument_identity)
    knowledge_articles = list_articles(
        db, tenant_id, instrument=condition["instrument_type"]
    )[:_KNOWLEDGE_ARTICLE_LIMIT]
    timeline = build_memory_timeline(condition)
    recommendation = build_memory_recommendation(db, tenant_id, condition, recurrence)

    return {
        "instrument_identity": instrument_identity,
        "instrument_type": condition["instrument_type"],
        "condition_history": condition,
        "recurring_issues": recurrence,
        "predictive_risk": predictive_risk,
        "health_forecast": health_forecast,
        "similar_instruments": similar_instruments,
        "knowledge_articles": knowledge_articles,
        "timeline": timeline,
        "memory_recommendation": recommendation,
        "human_review_required": True,
    }
