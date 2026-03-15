from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models

router = APIRouter(tags=["vendor-analytics"])


@router.get("/analytics/vendors")
def vendor_analytics(db: Session = Depends(get_db)):
    rows = db.query(models.Inspection).all()

    vendor_summary = {}

    for r in rows:
        vendor = (r.vendor_name or "unknown").strip() or "unknown"
        if vendor not in vendor_summary:
            vendor_summary[vendor] = {
                "vendor_name": vendor,
                "total_inspections": 0,
                "escalations": 0,
                "avg_confidence": 0.0,
                "top_issues": {},
            }

        vendor_summary[vendor]["total_inspections"] += 1

        if (r.risk_score or 0) >= 50 or (r.detected_issue or "").lower() in {"debris", "stain", "corrosion"}:
            vendor_summary[vendor]["escalations"] += 1

        vendor_summary[vendor]["avg_confidence"] += float(r.confidence or 0.0)

        issue = (r.detected_issue or "unknown").strip() or "unknown"
        vendor_summary[vendor]["top_issues"][issue] = vendor_summary[vendor]["top_issues"].get(issue, 0) + 1

    items = []
    for vendor, stats in vendor_summary.items():
        total = stats["total_inspections"] or 1
        avg_confidence = round(stats["avg_confidence"] / total, 2)
        top_issues = sorted(
            [{"label": k, "count": v} for k, v in stats["top_issues"].items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        items.append({
            "vendor_name": vendor,
            "total_inspections": stats["total_inspections"],
            "escalations": stats["escalations"],
            "avg_confidence": avg_confidence,
            "top_issues": top_issues,
        })

    items.sort(key=lambda x: (x["escalations"], x["total_inspections"]), reverse=True)

    return {"items": items}
