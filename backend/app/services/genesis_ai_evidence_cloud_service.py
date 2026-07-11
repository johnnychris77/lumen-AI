"""v5.3 — Project Genesis AI, Section 3: Clinical Evidence Cloud.

Zero new tables. Horizon's `horizon_evidence_service.py` (v3.4) already
implements everything this section names: peer-reviewed literature,
manufacturer guidance (IFUs), AAMI, AORN, organization-approved SOPs,
internal validation studies -- via `ClinicalEvidenceReference`'s
`EVIDENCE_TYPES` -- and already links evidence directly to any
recommendation-producing row via `RecommendationEvidenceLink`
(`add_evidence`/`list_evidence`/`link_evidence_to_recommendation`/
`list_evidence_for_recommendation`). This module only adds the one
thing Horizon's service didn't need: a coverage summary grouped by
evidence type.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.federated_horizon import EVIDENCE_TYPES, ClinicalEvidenceReference


def evidence_cloud_summary(db: Session) -> dict:
    rows = db.query(ClinicalEvidenceReference).all()
    by_type: dict[str, int] = {t: 0 for t in EVIDENCE_TYPES}
    for r in rows:
        by_type[r.evidence_type] = by_type.get(r.evidence_type, 0) + 1
    return {"evidence_types": EVIDENCE_TYPES, "total_evidence_references": len(rows), "by_evidence_type": by_type}
