"""v1.5 — Instrument Family Performance (Deliverable 4).

Ranks instrument families by inspection frequency, pass/fail/repair rate, and
supervisor intervention rate — derived from real Inspection rows, grouped by
the same anatomy-family resolution the rest of the platform already uses
(instrument_anatomy.resolve_family), not a re-typed instrument list.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.services.instrument_anatomy import resolve_family

_REPAIRABLE_ISSUES = {"crack", "corrosion", "insulation_damage"}


def _rate(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


def instrument_family_performance(db: Session, tenant_id: str, days: int = 180) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.created_at >= since)
        .all()
    )

    by_family: dict[str, list] = defaultdict(list)
    for r in rows:
        by_family[resolve_family(r.instrument_type)].append(r)

    families = []
    for family, family_rows in by_family.items():
        scored = [r for r in family_rows if r.has_image and r.disposition]
        total = len(scored)
        pass_ct = sum(1 for r in scored if r.disposition == "PASS")
        fail_ct = sum(1 for r in scored if r.disposition in ("REPROCESS", "REMOVE FROM SERVICE"))
        repair_ct = sum(
            1 for r in scored
            if r.disposition == "REMOVE FROM SERVICE" and (r.detected_issue or "") in _REPAIRABLE_ISSUES
        )
        override_ct = sum(1 for r in family_rows if (r.override_by or "").strip())

        families.append({
            "family": family,
            "inspection_count": len(family_rows),
            "pass_rate_pct": _rate(pass_ct, total),
            "failure_rate_pct": _rate(fail_ct, total),
            "repair_rate_pct": _rate(repair_ct, total),
            "supervisor_intervention_rate_pct": _rate(override_ct, len(family_rows)),
        })

    families.sort(key=lambda f: f["inspection_count"], reverse=True)

    return {"families": families, "human_review_required": True}
