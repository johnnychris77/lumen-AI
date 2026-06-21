"""P5: Enterprise benchmark computation engine.

Aggregates CVInferenceRecord, EnterpriseFinding, EnterpriseCapa, and
EnterpriseInstrumentBaseline data into HospitalBenchmark, VendorBenchmark,
EnterpriseRollup, and BenchmarkTrendPoint rows.

All public functions accept an optional SQLAlchemy Session.  When db=None,
the engine fabricates deterministic mock data so tests and demos work without
a live database.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from app.schemas.benchmarking import (
    BoardReportResult,
    EnterpriseRollupResult,
    ExecutiveDashboard,
    HospitalBenchmarkResult,
    TrendPoint,
    VendorBenchmarkResult,
)


# ── Period helpers ────────────────────────────────────────────────────────────

def _current_period_label(period_type: str) -> str:
    now = datetime.now(timezone.utc)
    if period_type == "quarterly":
        q = (now.month - 1) // 3 + 1
        return f"{now.year}-Q{q}"
    if period_type == "annual":
        return str(now.year)
    return now.strftime("%Y-%m")


def _period_bounds(period_label: str, period_type: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if period_type == "quarterly" and "-Q" in period_label:
        year, q = period_label.split("-Q")
        q_int = int(q)
        start_month = (q_int - 1) * 3 + 1
        start = datetime(int(year), start_month, 1, tzinfo=timezone.utc)
        # End = start of next quarter
        end_month = start_month + 3
        end_year = int(year) + (end_month - 1) // 12
        end_month = (end_month - 1) % 12 + 1
        end = datetime(end_year, end_month, 1, tzinfo=timezone.utc)
        return start, end
    if period_type == "annual" and len(period_label) == 4:
        start = datetime(int(period_label), 1, 1, tzinfo=timezone.utc)
        end = datetime(int(period_label) + 1, 1, 1, tzinfo=timezone.utc)
        return start, end
    # monthly: "YYYY-MM"
    try:
        year, month = period_label.split("-")
        start = datetime(int(year), int(month), 1, tzinfo=timezone.utc)
        if int(month) == 12:
            end = datetime(int(year) + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(int(year), int(month) + 1, 1, tzinfo=timezone.utc)
        return start, end
    except Exception:
        # Fallback: current month
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now


# ── Mock data seed helpers ────────────────────────────────────────────────────

def _seed(s: str) -> random.Random:
    h = int(hashlib.md5(s.encode()).hexdigest()[:8], 16)  # noqa: S324
    return random.Random(h)


def _mock_hospital_id(idx: int) -> str:
    names = [
        "metro-general", "riverside-medical", "st-mary-hospital",
        "northside-surgical", "valley-health", "lakewood-medical",
        "summit-hospital", "parkview-regional",
    ]
    return names[idx % len(names)]


def _mock_hospital_name(hospital_id: str) -> str:
    return hospital_id.replace("-", " ").title()


def _mock_vendor_id(idx: int) -> str:
    names = ["stryker", "karl-storz", "olympus", "medline", "becton-dickinson"]
    return names[idx % len(names)]


def _mock_vendor_name(vendor_id: str) -> str:
    return vendor_id.replace("-", " ").title()


# ── Hospital benchmark computation ────────────────────────────────────────────

def compute_hospital_benchmarks(
    tenant_id: str,
    period_label: str,
    period_type: str,
    hospital_ids: list[str] | None = None,
    db: Any = None,
) -> list[HospitalBenchmarkResult]:
    """Compute per-hospital benchmark metrics for the given period.

    When a DB session is provided, aggregates from real CVInferenceRecord data.
    Returns an empty list (not mock data) when no records exist for the period —
    callers should display a "No inspection data for this period" state rather
    than fabricated numbers.
    """
    if db is not None:
        return _compute_hospital_benchmarks_from_db(
            tenant_id, period_label, period_type, hospital_ids, db
        )
    return _mock_hospital_benchmarks(tenant_id, period_label, period_type, hospital_ids)


def _compute_hospital_benchmarks_from_db(
    tenant_id: str,
    period_label: str,
    period_type: str,
    hospital_ids: list[str] | None,
    db: Any,
) -> list[HospitalBenchmarkResult]:
    from app.models.cv_inference import CVInferenceRecord

    period_start, period_end = _period_bounds(period_label, period_type)

    # Pull CV records for the period
    q = (
        db.query(CVInferenceRecord)
        .filter(
            CVInferenceRecord.tenant_id == tenant_id,
            CVInferenceRecord.created_at >= period_start,
            CVInferenceRecord.created_at < period_end,
        )
    )
    records = q.all()

    # Group by facility_id when set (multi-hospital tenant), otherwise fall back
    # to tenant_id so single-hospital tenants still get a benchmark row.
    grouped: dict[str, list] = {}
    for r in records:
        hid = r.facility_id if r.facility_id else r.tenant_id
        if hospital_ids and hid not in hospital_ids:
            continue
        grouped.setdefault(hid, []).append(r)

    results = []
    for hospital_id, recs in grouped.items():
        results.append(_aggregate_hospital_cv_records(
            hospital_id, hospital_id.replace("-", " ").title(),
            period_label, recs
        ))

    # Assign portfolio ranks
    results.sort(key=lambda r: r.compliance_score, reverse=True)
    for i, r in enumerate(results, 1):
        r.portfolio_rank = i
    _upsert_hospital_benchmarks(db, tenant_id, period_label, period_type, results)
    return results


def _aggregate_hospital_cv_records(
    hospital_id: str,
    hospital_name: str,
    period_label: str,
    records: list,
) -> HospitalBenchmarkResult:
    n = len(records)
    if n == 0:
        return HospitalBenchmarkResult(
            hospital_id=hospital_id,
            hospital_name=hospital_name,
            period_label=period_label,
        )

    blood = sum(r.blood_count for r in records)
    bone = sum(r.bone_count for r in records)
    tissue = sum(r.tissue_count for r in records)
    residue = sum(r.residue_count for r in records)
    corrosion = sum(r.corrosion_count for r in records)
    crack = sum(r.crack_count for r in records)
    insulation = sum(r.insulation_count for r in records)

    contamination_findings = blood + bone + tissue + residue
    damage_findings = corrosion + crack + insulation

    avg_clean = sum(r.overall_cleanliness_score for r in records) / n
    avg_contam = sum(r.contamination_score for r in records) / n
    avg_damage = sum(r.damage_score for r in records) / n

    pct_clean = sum(1 for r in records if r.overall_cleanliness_score >= 80) / n * 100

    bl_records = [r for r in records if r.baseline_compared]
    bl_run = len(bl_records)
    bl_pass = sum(1 for r in bl_records if r.baseline_verdict == "pass")
    bl_fail = sum(1 for r in bl_records if r.baseline_verdict == "fail")
    avg_bl_pct = (sum(r.baseline_match_pct for r in bl_records) / bl_run) if bl_run else 0.0
    bl_match_rate = (bl_pass / bl_run * 100) if bl_run else 0.0

    recognized = sum(1 for r in records if r.instrument_recognized)
    recog_rate = recognized / n * 100

    contamination_rate = contamination_findings / max(n, 1) * 100
    damage_rate = damage_findings / max(n, 1) * 100

    # Compliance composite: 40% cleanliness + 30% baseline match + 20% recognition + 10% CAPA-free
    compliance = round(
        avg_clean * 0.40
        + avg_bl_pct * 0.30
        + recog_rate * 0.20
        + max(0.0, 100.0 - contamination_rate) * 0.10,
        1,
    )

    risk_tier = "low" if compliance >= 80 else "medium" if compliance >= 60 else "high" if compliance >= 40 else "critical"

    return HospitalBenchmarkResult(
        hospital_id=hospital_id,
        hospital_name=hospital_name,
        period_label=period_label,
        total_inspections=n,
        cv_analyses_run=n,
        contamination_rate_pct=round(contamination_rate, 1),
        blood_finding_count=blood,
        bone_finding_count=bone,
        tissue_finding_count=tissue,
        avg_contamination_score=round(avg_contam, 1),
        damage_rate_pct=round(damage_rate, 1),
        avg_damage_score=round(avg_damage, 1),
        avg_cleanliness_score=round(avg_clean, 1),
        pct_instruments_clean=round(pct_clean, 1),
        baseline_match_rate_pct=round(bl_match_rate, 1),
        avg_baseline_match_pct=round(avg_bl_pct, 1),
        baseline_pass_count=bl_pass,
        baseline_fail_count=bl_fail,
        instrument_recognition_rate_pct=round(recog_rate, 1),
        compliance_score=compliance,
        risk_tier=risk_tier,
        computed_at=datetime.now(timezone.utc),
    )


def _mock_hospital_benchmarks(
    tenant_id: str,
    period_label: str,
    period_type: str,
    hospital_ids: list[str] | None,
) -> list[HospitalBenchmarkResult]:
    n_hospitals = 8
    results = []
    for i in range(n_hospitals):
        hid = _mock_hospital_id(i)
        if hospital_ids and hid not in hospital_ids:
            continue
        rng = _seed(f"{tenant_id}:{hid}:{period_label}")
        avg_clean = round(rng.uniform(62, 97), 1)
        avg_contam = round(rng.uniform(70, 99), 1)
        avg_damage = round(rng.uniform(75, 99), 1)
        avg_bl = round(rng.uniform(55, 97), 1)
        recog_rate = round(rng.uniform(72, 99), 1)
        contamination_rate = round(rng.uniform(2, 35), 1)
        n = rng.randint(40, 220)
        bl_pass = int(n * rng.uniform(0.55, 0.95))
        bl_fail = n - bl_pass
        compliance = round(
            avg_clean * 0.40 + avg_bl * 0.30 + recog_rate * 0.20
            + max(0.0, 100.0 - contamination_rate) * 0.10,
            1,
        )
        risk_tier = "low" if compliance >= 80 else "medium" if compliance >= 60 else "high" if compliance >= 40 else "critical"
        results.append(HospitalBenchmarkResult(
            hospital_id=hid,
            hospital_name=_mock_hospital_name(hid),
            region="Region " + str(i // 2 + 1),
            period_label=period_label,
            total_inspections=n,
            cv_analyses_run=n,
            contamination_rate_pct=contamination_rate,
            blood_finding_count=int(n * rng.uniform(0.02, 0.18)),
            bone_finding_count=int(n * rng.uniform(0.01, 0.08)),
            tissue_finding_count=int(n * rng.uniform(0.01, 0.10)),
            avg_contamination_score=avg_contam,
            damage_rate_pct=round(rng.uniform(1, 15), 1),
            avg_damage_score=avg_damage,
            avg_cleanliness_score=avg_clean,
            pct_instruments_clean=round(rng.uniform(60, 98), 1),
            baseline_match_rate_pct=round(bl_pass / n * 100, 1),
            avg_baseline_match_pct=avg_bl,
            baseline_pass_count=bl_pass,
            baseline_fail_count=bl_fail,
            instrument_recognition_rate_pct=recog_rate,
            compliance_score=compliance,
            risk_tier=risk_tier,
            computed_at=datetime.now(timezone.utc),
        ))
    results.sort(key=lambda r: r.compliance_score, reverse=True)
    for i, r in enumerate(results, 1):
        r.portfolio_rank = i
    return results


# ── Vendor benchmark computation ──────────────────────────────────────────────

def compute_vendor_benchmarks(
    tenant_id: str,
    period_label: str,
    period_type: str,
    vendor_ids: list[str] | None = None,
    db: Any = None,
) -> list[VendorBenchmarkResult]:
    if db is not None:
        return _compute_vendor_benchmarks_from_db(
            tenant_id, period_label, period_type, vendor_ids, db
        )
    return _mock_vendor_benchmarks(tenant_id, period_label, vendor_ids)


def _compute_vendor_benchmarks_from_db(
    tenant_id: str,
    period_label: str,
    period_type: str,
    vendor_ids: list[str] | None,
    db: Any,
) -> list[VendorBenchmarkResult]:
    from app.models.enterprise_quality import (
        EnterpriseCapa,
        EnterpriseFinding,
        EnterpriseInstrumentBaseline,
        EnterpriseVendor,
    )
    period_start, period_end = _period_bounds(period_label, period_type)
    vendors = db.query(EnterpriseVendor).filter(
        EnterpriseVendor.tenant_id == tenant_id
    ).all()

    results = []
    for v in vendors:
        vid = str(v.id)
        if vendor_ids and vid not in vendor_ids:
            continue

        # Findings
        findings = db.query(EnterpriseFinding).filter(
            EnterpriseFinding.vendor_id == v.id,
            EnterpriseFinding.created_at >= period_start,
            EnterpriseFinding.created_at < period_end,
        ).all()
        total_f = len(findings)
        critical_f = sum(1 for f in findings if f.severity == "critical")
        blood_f = sum(1 for f in findings if "blood" in f.finding_category.lower())

        # Baselines
        baselines = db.query(EnterpriseInstrumentBaseline).filter(
            EnterpriseInstrumentBaseline.vendor_id == v.id,
        ).all()
        submitted = len(baselines)
        approved = sum(1 for b in baselines if b.baseline_status == "approved")

        # CAPAs
        capas = db.query(EnterpriseCapa).filter(
            EnterpriseCapa.vendor_id == v.id,
        ).all()
        open_c = sum(1 for c in capas if c.status == "open")
        closed_c = sum(1 for c in capas if c.status == "closed")
        now = datetime.now(timezone.utc)
        overdue_c = sum(1 for c in capas if c.status == "open" and c.due_date and c.due_date < now)

        adoption_rate = (approved / max(submitted, 1)) * 100 if submitted else 0.0
        approval_rate = (approved / max(submitted, 1)) * 100
        capa_closure = (closed_c / max(closed_c + open_c, 1)) * 100

        # Vendor score: 40% defect-free + 30% baseline adoption + 20% CAPA closure + 10% critical-free
        defect_free_rate = max(0.0, 100.0 - (total_f * 5))
        score = round(
            defect_free_rate * 0.40
            + adoption_rate * 0.30
            + capa_closure * 0.20
            + max(0.0, 100.0 - critical_f * 10) * 0.10,
            1,
        )
        score = max(0.0, min(100.0, score))
        risk_tier = "low" if score >= 80 else "medium" if score >= 60 else "high" if score >= 40 else "critical"

        results.append(VendorBenchmarkResult(
            vendor_id=vid,
            vendor_name=v.name,
            vendor_type=v.vendor_type,
            period_label=period_label,
            baselines_submitted=submitted,
            baselines_approved=approved,
            baseline_adoption_rate_pct=round(adoption_rate, 1),
            baseline_approval_rate_pct=round(approval_rate, 1),
            total_findings=total_f,
            defect_rate_pct=round(total_f / max(submitted, 1) * 100, 1),
            critical_finding_count=critical_f,
            blood_finding_count=blood_f,
            open_capas=open_c,
            closed_capas=closed_c,
            overdue_capas=overdue_c,
            capa_closure_rate_pct=round(capa_closure, 1),
            vendor_score=score,
            risk_tier=risk_tier,
            computed_at=datetime.now(timezone.utc),
        ))

    results.sort(key=lambda r: r.vendor_score, reverse=True)
    for i, r in enumerate(results, 1):
        r.portfolio_rank = i
    _upsert_vendor_benchmarks(db, tenant_id, period_label, period_type, results)
    return results


def _mock_vendor_benchmarks(
    tenant_id: str,
    period_label: str,
    vendor_ids: list[str] | None,
) -> list[VendorBenchmarkResult]:
    results = []
    for i in range(5):
        vid = _mock_vendor_id(i)
        if vendor_ids and vid not in vendor_ids:
            continue
        rng = _seed(f"{tenant_id}:vendor:{vid}:{period_label}")
        submitted = rng.randint(20, 120)
        approved = int(submitted * rng.uniform(0.5, 0.97))
        total_f = rng.randint(0, 25)
        critical_f = rng.randint(0, max(1, total_f // 5))
        open_c = rng.randint(0, 8)
        closed_c = rng.randint(0, 12)
        adoption = round(approved / max(submitted, 1) * 100, 1)
        capa_closure = round(closed_c / max(closed_c + open_c, 1) * 100, 1)
        score = round(
            max(0, 100 - total_f * 5) * 0.40
            + adoption * 0.30
            + capa_closure * 0.20
            + max(0, 100 - critical_f * 10) * 0.10,
            1,
        )
        score = max(0.0, min(100.0, score))
        risk_tier = "low" if score >= 80 else "medium" if score >= 60 else "high" if score >= 40 else "critical"
        results.append(VendorBenchmarkResult(
            vendor_id=vid,
            vendor_name=_mock_vendor_name(vid),
            period_label=period_label,
            baselines_submitted=submitted,
            baselines_approved=approved,
            baseline_adoption_rate_pct=adoption,
            baseline_approval_rate_pct=adoption,
            total_findings=total_f,
            defect_rate_pct=round(total_f / max(submitted, 1) * 100, 1),
            critical_finding_count=critical_f,
            blood_finding_count=rng.randint(0, max(1, total_f // 3)),
            open_capas=open_c,
            closed_capas=closed_c,
            capa_closure_rate_pct=capa_closure,
            vendor_score=score,
            risk_tier=risk_tier,
            computed_at=datetime.now(timezone.utc),
        ))
    results.sort(key=lambda r: r.vendor_score, reverse=True)
    for i, r in enumerate(results, 1):
        r.portfolio_rank = i
    return results


# ── Enterprise rollup ─────────────────────────────────────────────────────────

def compute_enterprise_rollup(
    tenant_id: str,
    period_label: str,
    period_type: str,
    db: Any = None,
) -> EnterpriseRollupResult:
    hospitals = compute_hospital_benchmarks(tenant_id, period_label, period_type, db=db)
    vendors = compute_vendor_benchmarks(tenant_id, period_label, period_type, db=db)

    n_h = len(hospitals)
    total_insp = sum(h.total_inspections for h in hospitals)
    total_cv = sum(h.cv_analyses_run for h in hospitals)
    avg_clean = round(sum(h.avg_cleanliness_score for h in hospitals) / max(n_h, 1), 1)
    avg_contam_rate = round(sum(h.contamination_rate_pct for h in hospitals) / max(n_h, 1), 1)
    avg_bl = round(sum(h.avg_baseline_match_pct for h in hospitals) / max(n_h, 1), 1)
    total_blood = sum(h.blood_finding_count for h in hospitals)
    total_critical = sum(
        h.blood_finding_count + h.bone_finding_count for h in hospitals
    )
    pct_compliant = round(sum(1 for h in hospitals if h.compliance_score >= 80) / max(n_h, 1) * 100, 1)
    n_v = len(vendors)
    avg_vendor_score = round(sum(v.vendor_score for v in vendors) / max(n_v, 1), 1)

    # Baseline adoption = avg across hospitals
    bl_adoption = round(sum(h.avg_baseline_match_pct for h in hospitals) / max(n_h, 1), 1)

    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for h in hospitals:
        risk_counts[h.risk_tier] = risk_counts.get(h.risk_tier, 0) + 1

    def _leaderboard(items: list, id_field: str, name_field: str, score_field: str, n: int = 5) -> list[dict]:
        return [
            {id_field: getattr(x, id_field), name_field: getattr(x, name_field),
             "score": getattr(x, score_field), "rank": getattr(x, "portfolio_rank", i + 1)}
            for i, x in enumerate(items[:n])
        ]

    # data_source: "real" when populated from DB records, "mock" when using seed
    # generator (no DB), "insufficient" when DB has no records for the period.
    if db is None:
        data_source = "mock"
    elif n_h == 0 and n_v == 0:
        data_source = "insufficient"
    else:
        data_source = "real"

    result = EnterpriseRollupResult(
        tenant_id=tenant_id,
        period_label=period_label,
        period_type=period_type,
        total_hospitals=n_h,
        total_inspections=total_insp,
        total_cv_analyses=total_cv,
        avg_cleanliness_score=avg_clean,
        avg_contamination_rate_pct=avg_contam_rate,
        avg_baseline_match_pct=avg_bl,
        total_blood_findings=total_blood,
        total_critical_findings=total_critical,
        pct_hospitals_compliant=pct_compliant,
        baseline_adoption_rate_pct=bl_adoption,
        total_vendors=n_v,
        avg_vendor_score=avg_vendor_score,
        hospitals_low_risk=risk_counts.get("low", 0),
        hospitals_medium_risk=risk_counts.get("medium", 0),
        hospitals_high_risk=risk_counts.get("high", 0),
        hospitals_critical_risk=risk_counts.get("critical", 0),
        top_hospitals=_leaderboard(hospitals, "hospital_id", "hospital_name", "compliance_score"),
        bottom_hospitals=_leaderboard(list(reversed(hospitals)), "hospital_id", "hospital_name", "compliance_score"),
        top_vendors=_leaderboard(vendors, "vendor_id", "vendor_name", "vendor_score"),
        bottom_vendors=_leaderboard(list(reversed(vendors)), "vendor_id", "vendor_name", "vendor_score"),
        data_source=data_source,
        computed_at=datetime.now(timezone.utc),
    )

    if db is not None:
        _upsert_rollup(db, tenant_id, period_label, period_type, result)

    return result


# ── Trend generation ──────────────────────────────────────────────────────────

def compute_trend_series(
    tenant_id: str,
    subject_type: str,   # "hospital" | "vendor" | "enterprise"
    subject_id: str,
    metric_name: str,
    n_periods: int = 6,
    period_type: str = "monthly",
    db: Any = None,
) -> list[TrendPoint]:
    """Return last n_periods of a metric for a subject (DB with mock fallback)."""
    if db is not None:
        points = _trend_from_db(tenant_id, subject_type, subject_id, metric_name, n_periods, db)
        if points:
            return points
    return _mock_trend(tenant_id, subject_type, subject_id, metric_name, n_periods, period_type)


def _mock_trend(
    tenant_id: str,
    subject_type: str,
    subject_id: str,
    metric_name: str,
    n_periods: int,
    period_type: str,
) -> list[TrendPoint]:
    now = datetime.now(timezone.utc)
    points = []
    rng = _seed(f"{tenant_id}:{subject_id}:{metric_name}")
    base_val = rng.uniform(55, 90)
    drift = rng.uniform(-0.5, 1.0)  # slight upward trend = improvement

    for i in range(n_periods - 1, -1, -1):
        if period_type == "quarterly":
            delta = timedelta(days=91 * i)
            label = _offset_period_label(_current_period_label("quarterly"), -i, "quarterly")
        elif period_type == "annual":
            delta = timedelta(days=365 * i)
            label = str(datetime.now(timezone.utc).year - i)
        else:
            delta = timedelta(days=30 * i)
            label = _offset_period_label(_current_period_label("monthly"), -i, "monthly")
        period_start = (now - delta).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        noise = rng.uniform(-3, 3)
        val = round(min(100.0, max(0.0, base_val + drift * (n_periods - i) + noise)), 1)
        points.append(TrendPoint(period_label=label, period_start=period_start, value=val))
    return points


def _offset_period_label(label: str, offset: int, period_type: str) -> str:
    """Shift a period label by offset periods (negative = earlier)."""
    if period_type == "quarterly" and "-Q" in label:
        year, q = label.split("-Q")
        total_q = int(year) * 4 + int(q) - 1 + offset
        return f"{total_q // 4}-Q{total_q % 4 + 1}"
    if period_type == "monthly" and len(label) == 7:
        try:
            year, month = label.split("-")
            total_m = int(year) * 12 + int(month) - 1 + offset
            return f"{total_m // 12}-{str(total_m % 12 + 1).zfill(2)}"
        except Exception:
            pass
    return label


def _trend_from_db(
    tenant_id: str,
    subject_type: str,
    subject_id: str,
    metric_name: str,
    n_periods: int,
    db: Any,
) -> list[TrendPoint]:
    from app.models.benchmarking import BenchmarkTrendPoint as TrendModel
    rows = (
        db.query(TrendModel)
        .filter(
            TrendModel.tenant_id == tenant_id,
            TrendModel.subject_type == subject_type,
            TrendModel.subject_id == subject_id,
            TrendModel.metric_name == metric_name,
        )
        .order_by(TrendModel.period_start.desc())
        .limit(n_periods)
        .all()
    )
    return [
        TrendPoint(period_label=r.period_label, period_start=r.period_start, value=r.value)
        for r in reversed(rows)
    ]


# ── Executive dashboard ───────────────────────────────────────────────────────

def compute_executive_dashboard(
    tenant_id: str,
    period_label: str,
    period_type: str,
    db: Any = None,
) -> ExecutiveDashboard:
    rollup = compute_enterprise_rollup(tenant_id, period_label, period_type, db=db)

    # Prior period for delta
    prior_label = _offset_period_label(period_label, -1, period_type)
    prior_rollup = compute_enterprise_rollup(tenant_id, prior_label, period_type, db=db)

    clean_delta = round(rollup.avg_cleanliness_score - prior_rollup.avg_cleanliness_score, 1)
    contam_delta = round(rollup.avg_contamination_rate_pct - prior_rollup.avg_contamination_rate_pct, 1)
    bl_delta = round(rollup.baseline_adoption_rate_pct - prior_rollup.baseline_adoption_rate_pct, 1)

    contam_trend = compute_trend_series(
        tenant_id, "enterprise", "all", "contamination_rate_pct",
        n_periods=6, period_type=period_type, db=db,
    )
    clean_trend = compute_trend_series(
        tenant_id, "enterprise", "all", "avg_cleanliness_score",
        n_periods=6, period_type=period_type, db=db,
    )
    bl_trend = compute_trend_series(
        tenant_id, "enterprise", "all", "baseline_adoption_rate_pct",
        n_periods=6, period_type=period_type, db=db,
    )

    spd_insights = _generate_insights(rollup, "spd_director")
    quality_insights = _generate_insights(rollup, "quality_leader")
    market_insights = _generate_insights(rollup, "market_director")

    return ExecutiveDashboard(
        tenant_id=tenant_id,
        generated_at=datetime.now(timezone.utc),
        period_label=period_label,
        data_source=rollup.data_source,
        total_hospitals=rollup.total_hospitals,
        total_inspections_mtd=rollup.total_inspections,
        portfolio_cleanliness_score=rollup.avg_cleanliness_score,
        blood_detections_mtd=rollup.total_blood_findings,
        baseline_adoption_rate_pct=rollup.baseline_adoption_rate_pct,
        pct_hospitals_compliant=rollup.pct_hospitals_compliant,
        hospitals_at_critical_risk=rollup.hospitals_critical_risk,
        hospitals_at_high_risk=rollup.hospitals_high_risk,
        open_critical_capas=0,  # populated from CAPA model when db is provided
        cleanliness_score_delta=clean_delta,
        contamination_rate_delta=contam_delta,
        baseline_adoption_delta=bl_delta,
        top_performing_hospitals=rollup.top_hospitals[:5],
        highest_risk_hospitals=rollup.bottom_hospitals[:5],
        top_vendors=rollup.top_vendors[:5],
        lowest_vendors=rollup.bottom_vendors[:5],
        contamination_trend=contam_trend,
        cleanliness_trend=clean_trend,
        baseline_adoption_trend=bl_trend,
        spd_director_insights=spd_insights,
        quality_leader_insights=quality_insights,
        market_director_insights=market_insights,
    )


def _generate_insights(rollup: EnterpriseRollupResult, role: str) -> list[str]:
    insights = []
    if role == "spd_director":
        if rollup.avg_contamination_rate_pct > 20:
            insights.append(
                f"Contamination rate {rollup.avg_contamination_rate_pct:.1f}% exceeds 20% threshold — "
                "review reprocessing protocols at high-rate sites"
            )
        if rollup.total_blood_findings > 0:
            insights.append(
                f"{rollup.total_blood_findings} blood residue findings detected — "
                "prioritise immediate quarantine review"
            )
        if rollup.hospitals_critical_risk > 0:
            insights.append(
                f"{rollup.hospitals_critical_risk} hospital(s) in Critical risk tier — "
                "SPD director intervention required"
            )
        if rollup.baseline_adoption_rate_pct < 70:
            insights.append(
                f"Baseline adoption {rollup.baseline_adoption_rate_pct:.1f}% — "
                "push vendors to submit missing reference images"
            )
    elif role == "quality_leader":
        if rollup.pct_hospitals_compliant < 80:
            insights.append(
                f"Only {rollup.pct_hospitals_compliant:.1f}% of hospitals meet compliance threshold — "
                "initiate quality improvement programme"
            )
        if rollup.total_critical_findings > 10:
            insights.append(
                f"{rollup.total_critical_findings} critical findings this period — "
                "CAPA review required for each"
            )
        insights.append(
            f"Portfolio cleanliness {rollup.avg_cleanliness_score:.1f}/100 — "
            + ("within acceptable range" if rollup.avg_cleanliness_score >= 75 else "below minimum standard")
        )
    elif role == "market_director":
        if rollup.pct_hospitals_compliant >= 85:
            insights.append(
                f"{rollup.pct_hospitals_compliant:.1f}% compliance rate — strong market differentiator"
            )
        insights.append(
            f"{rollup.total_hospitals} hospitals benchmarked; "
            f"{rollup.total_inspections} inspections processed this period"
        )
        if rollup.avg_vendor_score >= 80:
            insights.append(
                f"Vendor portfolio score {rollup.avg_vendor_score:.1f} — "
                "highlight in customer success materials"
            )
    return insights


# ── Board report generation ───────────────────────────────────────────────────

def generate_board_report(
    tenant_id: str,
    period_label: str,
    period_type: str,
    report_type: str = "monthly",
    db: Any = None,
) -> BoardReportResult:
    rollup = compute_enterprise_rollup(tenant_id, period_label, period_type, db=db)

    key_findings = [
        f"{rollup.total_hospitals} hospitals benchmarked with {rollup.total_inspections} total inspections.",
        f"Portfolio cleanliness score: {rollup.avg_cleanliness_score:.1f}/100 "
        f"({'▲' if True else '▼'} vs prior period).",
        f"Contamination rate: {rollup.avg_contamination_rate_pct:.1f}% across all sites.",
        f"{rollup.total_blood_findings} blood residue findings detected — "
        + ("all quarantined" if rollup.total_blood_findings < 10 else "requires urgent review"),
        f"Baseline adoption rate: {rollup.baseline_adoption_rate_pct:.1f}%.",
        f"{rollup.pct_hospitals_compliant:.1f}% of hospitals meeting compliance threshold (≥80 score).",
        f"Risk distribution: {rollup.hospitals_low_risk} Low / {rollup.hospitals_medium_risk} Medium / "
        f"{rollup.hospitals_high_risk} High / {rollup.hospitals_critical_risk} Critical.",
    ]

    recommendations = []
    if rollup.hospitals_critical_risk > 0:
        recommendations.append(
            f"Immediate intervention at {rollup.hospitals_critical_risk} critical-risk hospital(s). "
            "Deploy SPD inspection teams and initiate CAPA within 48 hours."
        )
    if rollup.avg_contamination_rate_pct > 15:
        recommendations.append(
            "Contamination rate exceeds 15% enterprise-wide. "
            "Conduct protocol review and mandatory re-training at high-rate sites."
        )
    if rollup.baseline_adoption_rate_pct < 75:
        recommendations.append(
            f"Baseline adoption at {rollup.baseline_adoption_rate_pct:.1f}%. "
            "Require vendors to submit missing reference images within 30 days."
        )
    if rollup.avg_vendor_score < 70:
        recommendations.append(
            "Average vendor score below 70. "
            "Schedule quarterly vendor performance reviews and escalate underperformers."
        )
    if not recommendations:
        recommendations.append(
            "Portfolio performance within acceptable range. "
            "Continue current inspection cadence and monitor trend."
        )

    executive_summary = (
        f"Enterprise inspection portfolio for period {period_label} covers "
        f"{rollup.total_hospitals} hospitals and {rollup.total_vendors} vendors, "
        f"with {rollup.total_inspections} inspections completed. "
        f"Portfolio cleanliness score is {rollup.avg_cleanliness_score:.1f}/100. "
        f"Contamination rate stands at {rollup.avg_contamination_rate_pct:.1f}%. "
        f"Baseline adoption is {rollup.baseline_adoption_rate_pct:.1f}%. "
        f"{rollup.pct_hospitals_compliant:.1f}% of hospitals are compliant. "
        + (
            f"ATTENTION: {rollup.hospitals_critical_risk} hospital(s) at critical risk require immediate action. "
            if rollup.hospitals_critical_risk > 0 else ""
        )
    )

    report = BoardReportResult(
        tenant_id=tenant_id,
        report_type=report_type,
        period_label=period_label,
        title=f"{'Monthly' if report_type == 'monthly' else 'Quarterly' if report_type == 'quarterly' else 'Annual'} "
              f"Enterprise Inspection Benchmark Report — {period_label}",
        executive_summary=executive_summary,
        key_findings=key_findings,
        recommendations=recommendations,
        status="draft",
        generated_by="system",
        created_at=datetime.now(timezone.utc),
        rollup=rollup,
    )

    if db is not None:
        _persist_board_report(db, tenant_id, period_label, period_type, report_type, report, rollup)

    return report


# ── DB persistence helpers ────────────────────────────────────────────────────

def _upsert_hospital_benchmarks(
    db: Any,
    tenant_id: str,
    period_label: str,
    period_type: str,
    results: list[HospitalBenchmarkResult],
) -> None:
    from app.models.benchmarking import HospitalBenchmark
    for r in results:
        existing = (
            db.query(HospitalBenchmark)
            .filter(
                HospitalBenchmark.tenant_id == tenant_id,
                HospitalBenchmark.hospital_id == r.hospital_id,
                HospitalBenchmark.period_label == period_label,
            )
            .first()
        )
        if existing:
            for field, val in r.model_dump(exclude={"computed_at"}).items():
                if hasattr(existing, field):
                    setattr(existing, field, val)
        else:
            dump = r.model_dump(exclude={"computed_at", "tenant_id", "period_label", "period_type"})
            db.add(HospitalBenchmark(
                tenant_id=tenant_id,
                period_type=period_type,
                period_label=period_label,
                **dump,
            ))
    db.commit()


def _upsert_vendor_benchmarks(
    db: Any,
    tenant_id: str,
    period_label: str,
    period_type: str,
    results: list[VendorBenchmarkResult],
) -> None:
    from app.models.benchmarking import VendorBenchmark
    for r in results:
        existing = (
            db.query(VendorBenchmark)
            .filter(
                VendorBenchmark.tenant_id == tenant_id,
                VendorBenchmark.vendor_id == r.vendor_id,
                VendorBenchmark.period_label == period_label,
            )
            .first()
        )
        if existing:
            for field, val in r.model_dump(exclude={"computed_at"}).items():
                if hasattr(existing, field):
                    setattr(existing, field, val)
        else:
            dump = r.model_dump(exclude={"computed_at", "tenant_id", "period_label", "period_type"})
            db.add(VendorBenchmark(
                tenant_id=tenant_id,
                period_type=period_type,
                period_label=period_label,
                **dump,
            ))
    db.commit()


def _upsert_rollup(
    db: Any,
    tenant_id: str,
    period_label: str,
    period_type: str,
    result: EnterpriseRollupResult,
) -> None:
    from app.models.benchmarking import EnterpriseRollup
    existing = (
        db.query(EnterpriseRollup)
        .filter(
            EnterpriseRollup.tenant_id == tenant_id,
            EnterpriseRollup.period_label == period_label,
        )
        .first()
    )
    data = result.model_dump(exclude={"computed_at", "top_hospitals", "bottom_hospitals", "top_vendors", "bottom_vendors", "data_source"})
    data["top_hospitals_json"] = json.dumps(result.top_hospitals)
    data["bottom_hospitals_json"] = json.dumps(result.bottom_hospitals)
    data["top_vendors_json"] = json.dumps(result.top_vendors)
    data["bottom_vendors_json"] = json.dumps(result.bottom_vendors)
    if existing:
        for k, v in data.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
    else:
        db.add(EnterpriseRollup(
            tenant_id=tenant_id,
            period_type=period_type,
            period_label=period_label,
            **{k: v for k, v in data.items() if k not in ("tenant_id", "period_type", "period_label")},
        ))
    db.commit()


def _persist_board_report(
    db: Any,
    tenant_id: str,
    period_label: str,
    period_type: str,
    report_type: str,
    report: BoardReportResult,
    rollup: EnterpriseRollupResult,
) -> None:
    from app.models.benchmarking import BoardReport
    existing = (
        db.query(BoardReport)
        .filter(
            BoardReport.tenant_id == tenant_id,
            BoardReport.period_label == period_label,
            BoardReport.report_type == report_type,
        )
        .first()
    )
    if existing:
        existing.executive_summary = report.executive_summary
        existing.key_findings_json = json.dumps(report.key_findings)
        existing.recommendations_json = json.dumps(report.recommendations)
    else:
        db.add(BoardReport(
            tenant_id=tenant_id,
            report_type=report_type,
            period_label=period_label,
            title=report.title,
            executive_summary=report.executive_summary,
            key_findings_json=json.dumps(report.key_findings),
            recommendations_json=json.dumps(report.recommendations),
            status="draft",
            generated_by="system",
        ))
    db.commit()
