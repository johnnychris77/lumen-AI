"""Project Council, Section 10: Agreement Map.

Builds the visual agreement matrix -- rows are specialists, columns are
distinct recommended actions, cells mark which specialist recommended
which option -- plus confidence/evidence strength per position.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.services.council_specialist_assessment_service import latest_assessments_for_case


def _normalize_action(text: str) -> str:
    return " ".join((text or "").strip().lower().split()) or "no_action_recommended"


def build_agreement_map(db: Session, tenant_id: str, council_case_id: int) -> dict:
    assessments = latest_assessments_for_case(db, tenant_id, council_case_id)
    if not assessments:
        return {"specialists": [], "positions": [], "matrix": {}, "consensus_position": "", "dissenting_specialists": []}

    positions: dict[str, list[str]] = defaultdict(list)
    original_titles: dict[str, str] = {}
    for a in assessments:
        key = _normalize_action(a["recommended_action"])
        positions[key].append(a["specialist_key"])
        original_titles.setdefault(key, a["recommended_action"] or "No action recommended")

    consensus_key, consensus_members = max(positions.items(), key=lambda kv: len(kv[1]))
    dissenting_specialists = [
        a["specialist_key"] for a in assessments if a["specialist_key"] not in consensus_members
    ]

    matrix = {
        a["specialist_key"]: {
            "position": original_titles[_normalize_action(a["recommended_action"])],
            "confidence": a["confidence"],
            "evidence_strength": "high" if a["confidence"] == "high" else "moderate" if a["confidence"] == "moderate" else "low",
        }
        for a in assessments
    }

    return {
        "specialists": [a["specialist_key"] for a in assessments],
        "positions": [original_titles[k] for k in positions],
        "matrix": matrix,
        "consensus_position": original_titles[consensus_key],
        "dissenting_specialists": dissenting_specialists,
    }
