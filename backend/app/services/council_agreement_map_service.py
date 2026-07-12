"""Project Council, Section 10: Agreement Map.

Builds the visual agreement matrix -- rows are specialists, columns are
distinct recommended actions, cells mark which specialist recommended
which option -- plus confidence/evidence strength per position. Uses the
same `_normalize_action` grouping as `council_consensus_service` (imported,
not re-implemented) and the same "abstentions never form a false shared
position" rule, so the map's `consensus_position`/`dissenting_specialists`
can never contradict the case's own `classify_consensus` result for the
same assessments.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.services.council_consensus_service import _normalize_action
from app.services.council_specialist_assessment_service import latest_assessments_for_case


def build_agreement_map(db: Session, tenant_id: str, council_case_id: int) -> dict:
    assessments = latest_assessments_for_case(db, tenant_id, council_case_id)
    if not assessments:
        return {
            "specialists": [], "positions": [], "matrix": {}, "consensus_position": "",
            "dissenting_specialists": [], "human_review_required": True,
        }

    voting = [a for a in assessments if a["recommended_action"].strip()]

    positions: dict[str, list[str]] = defaultdict(list)
    original_titles: dict[str, str] = {}
    for a in voting:
        key = _normalize_action(a["recommended_action"])
        positions[key].append(a["specialist_key"])
        original_titles.setdefault(key, a["recommended_action"])

    if positions:
        consensus_key, consensus_members = max(positions.items(), key=lambda kv: len(kv[1]))
        consensus_position = original_titles[consensus_key]
        dissenting_specialists = [a["specialist_key"] for a in voting if a["specialist_key"] not in consensus_members]
    else:
        consensus_position = ""
        dissenting_specialists = []

    matrix = {
        a["specialist_key"]: {
            "position": a["recommended_action"] or "No action recommended",
            "confidence": a["confidence"],
            "evidence_strength": a["confidence"],
        }
        for a in assessments
    }

    return {
        "specialists": [a["specialist_key"] for a in assessments],
        "positions": [original_titles[k] for k in positions],
        "matrix": matrix,
        "consensus_position": consensus_position,
        "dissenting_specialists": dissenting_specialists,
        "human_review_required": True,
    }
