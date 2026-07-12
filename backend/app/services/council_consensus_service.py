"""Project Council, Section 5: Consensus Engine.

Classifies Council outcomes from the latest independent assessment per
required specialist. A simple majority never overrides unresolved safety
dissent (Section 16): if any safety/evidence specialist
(`SAFETY_VETO_SPECIALISTS` -- Sentinel-X, Veritas) dissents from the
majority position with urgent significance, the outcome is always
SAFETY_DISSENT regardless of how large the majority is. Consensus itself
is never treated as evidence -- classification only ever describes
agreement, not correctness.
"""
from __future__ import annotations

from collections import defaultdict

from app.models.council_leadership import (
    CONSENSUS_CONDITIONAL,
    CONSENSUS_INSUFFICIENT_EVIDENCE,
    CONSENSUS_SAFETY_DISSENT,
    CONSENSUS_SPLIT,
    CONSENSUS_STRONG,
    CONSENSUS_UNANIMOUS,
    SAFETY_VETO_SPECIALISTS,
)


def _normalize_action(text: str) -> str:
    return " ".join((text or "").strip().lower().split()) or "no_action_recommended"


def classify_consensus(assessments: list[dict], required_specialists: list[str]) -> dict:
    """Returns `{"status", "reason", "majority_position", "dissenting_specialists"}`.

    `assessments` must be the latest (post-revision) assessment per
    specialist -- see `council_specialist_assessment_service.
    latest_assessments_for_case`.
    """
    submitted = {a["specialist_key"] for a in assessments}
    missing_required = sorted(set(required_specialists) - submitted)
    if missing_required:
        return {
            "status": CONSENSUS_INSUFFICIENT_EVIDENCE,
            "reason": f"Missing required specialist assessment(s): {', '.join(missing_required)}.",
            "majority_position": "",
            "dissenting_specialists": [],
        }

    blocking = [
        a for a in assessments
        if a["confidence"] == "low" and not a["recommended_action"].strip() and a["evidence_limitations"].strip()
    ]
    if blocking:
        return {
            "status": CONSENSUS_INSUFFICIENT_EVIDENCE,
            "reason": "One or more specialists could not reach a supported conclusion due to evidence limitations.",
            "majority_position": "",
            "dissenting_specialists": [b["specialist_key"] for b in blocking],
        }

    positions: dict[str, list[str]] = defaultdict(list)
    for a in assessments:
        positions[_normalize_action(a["recommended_action"])].append(a["specialist_key"])

    if len(positions) == 1:
        return {
            "status": CONSENSUS_UNANIMOUS,
            "reason": "All required specialists recommend the same action.",
            "majority_position": next(iter(positions)),
            "dissenting_specialists": [],
        }

    majority_position, majority_members = max(positions.items(), key=lambda kv: len(kv[1]))
    majority_pct = len(majority_members) / len(assessments)
    dissenters = [a for a in assessments if a["specialist_key"] not in majority_members]

    safety_dissenters = [
        d for d in dissenters if d["specialist_key"] in SAFETY_VETO_SPECIALISTS and d["urgency"] == "urgent"
    ]
    if safety_dissenters:
        return {
            "status": CONSENSUS_SAFETY_DISSENT,
            "reason": "A safety or evidence specialist identifies an unresolved high-risk concern; a simple majority cannot override it.",
            "majority_position": majority_position,
            "dissenting_specialists": [d["specialist_key"] for d in safety_dissenters],
        }

    if majority_pct >= 0.8:
        return {
            "status": CONSENSUS_STRONG,
            "reason": "Most specialists agree and no safety-critical dissent exists.",
            "majority_position": majority_position,
            "dissenting_specialists": [d["specialist_key"] for d in dissenters],
        }

    if majority_pct < 0.6:
        return {
            "status": CONSENSUS_SPLIT,
            "reason": "Material disagreement remains among specialists.",
            "majority_position": majority_position,
            "dissenting_specialists": [d["specialist_key"] for d in dissenters],
        }

    return {
        "status": CONSENSUS_CONDITIONAL,
        "reason": "Agreement exists only if stated conditions are met.",
        "majority_position": majority_position,
        "dissenting_specialists": [d["specialist_key"] for d in dissenters],
    }
