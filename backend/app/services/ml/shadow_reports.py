"""Shadow §12 — Validation Reports.

Composes the other Phase 6 services' outputs into the seven named report
shapes §12 requires. Every report carries ``report_type``/``generated_at``/
``period`` so a re-run against the same stored rows reproduces byte-for-
byte identical content (Section 15's "reports reproducible" requirement) —
nothing here is randomly sampled or re-derived from a clock-dependent
source other than the explicit period bounds passed in.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.ml.shadow_clinical_review_board import as_dict as board_as_dict
from app.services.ml.shadow_dashboard import performance_dashboard
from app.services.ml.shadow_failure_analysis import analyze_failures
from app.services.ml.shadow_validation_metrics import validated_metrics


def _period_rows(rows: list, *, period_start: datetime | None, period_end: datetime | None) -> list:
    if period_start is None and period_end is None:
        return rows
    out = []
    for r in rows:
        ts = r.revealed_at or r.created_at
        if ts is None:
            continue
        if period_start and ts < period_start:
            continue
        if period_end and ts > period_end:
            continue
        out.append(r)
    return out


def _report_envelope(report_type: str, *, period_start, period_end) -> dict[str, Any]:
    return {
        "report_type": report_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start": period_start.isoformat() if period_start else None,
            "end": period_end.isoformat() if period_end else None,
        },
    }


def performance_summary(rows: list, *, period_start=None, period_end=None) -> dict[str, Any]:
    scoped = _period_rows(rows, period_start=period_start, period_end=period_end)
    return {**_report_envelope("performance_summary", period_start=period_start, period_end=period_end),
            **performance_dashboard(scoped)}


def error_analysis_report(samples: list[dict], *, period_start=None, period_end=None) -> dict[str, Any]:
    return {**_report_envelope("error_analysis", period_start=period_start, period_end=period_end),
            **analyze_failures(samples)}


def failure_trend_report(samples: list[dict], *, period_start=None, period_end=None) -> dict[str, Any]:
    analysis = analyze_failures(samples)
    return {
        **_report_envelope("failure_trend", period_start=period_start, period_end=period_end),
        "ranked_failure_causes": analysis["ranked_failure_causes"],
        "frequency_trend": analysis["frequency_trend"],
    }


def pilot_progress_report(pilot_status: dict | None, rows: list, *, period_start=None, period_end=None) -> dict[str, Any]:
    scoped = _period_rows(rows, period_start=period_start, period_end=period_end)
    metrics = validated_metrics(scoped)
    return {
        **_report_envelope("pilot_progress", period_start=period_start, period_end=period_end),
        "pilot_status": pilot_status,
        "sample_count": metrics["sample_count"],
        "agreement_rate": metrics["agreement_rate"],
    }


def clinical_review_summary(sessions: list, *, period_start=None, period_end=None) -> dict[str, Any]:
    return {
        **_report_envelope("clinical_review_summary", period_start=period_start, period_end=period_end),
        "sessions": [board_as_dict(s) for s in sessions],
        "latest_decision": board_as_dict(sessions[0])["approved"] if sessions else None,
    }


def weekly_report(rows: list, *, period_start: datetime, period_end: datetime) -> dict[str, Any]:
    scoped = _period_rows(rows, period_start=period_start, period_end=period_end)
    return {**_report_envelope("weekly_validation", period_start=period_start, period_end=period_end),
            **performance_dashboard(scoped)}


def monthly_report(rows: list, *, period_start: datetime, period_end: datetime) -> dict[str, Any]:
    scoped = _period_rows(rows, period_start=period_start, period_end=period_end)
    return {**_report_envelope("monthly_validation", period_start=period_start, period_end=period_end),
            **performance_dashboard(scoped)}
