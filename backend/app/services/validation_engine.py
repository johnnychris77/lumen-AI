"""P12 Clinical Validation Engine — FP/FN analysis and validation reporting."""
from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime, timezone

CRITICAL_FINDINGS = {"crack", "corrosion", "insulation"}

FINDING_CATEGORIES = [
    "blood",
    "bone",
    "tissue",
    "residue",
    "corrosion",
    "crack",
    "pitting",
    "insulation",
    "barcode",
    "udi",
    "qr",
    "keydot",
]


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]  # noqa: S324
    return random.Random(int(h, 16))


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_confusion(cases: list, reader: str = "ai") -> dict:
    """Compute TP/TN/FP/FN from a list of ValidationCase-like objects."""
    tp = tn = fp = fn = 0
    for c in cases:
        pred = c.ai_prediction if reader == "ai" else c.human_prediction
        gt = c.ground_truth
        if pred is None:
            continue
        if gt and pred:
            tp += 1
        elif not gt and not pred:
            tn += 1
        elif not gt and pred:
            fp += 1
        elif gt and not pred:
            fn += 1
    total = tp + tn + fp + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    accuracy = (tp + tn) / total if total > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    return dict(
        tp=tp,
        tn=tn,
        fp=fp,
        fn=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        specificity=round(specificity, 4),
        f1=round(f1, 4),
        accuracy=round(accuracy, 4),
        false_positive_rate=round(fpr, 4),
        false_negative_rate=round(fnr, 4),
        case_count=total,
    )


def _cohen_kappa(cm_ai: dict, cm_human: dict) -> float:
    """Simplified Cohen's kappa between AI and human on same case set."""
    n = cm_ai["case_count"]
    if n == 0:
        return 0.0
    po = (cm_ai["tp"] + cm_ai["tn"]) / n  # observed agreement
    # Expected agreement (simplified)
    p_pos_ai = (cm_ai["tp"] + cm_ai["fp"]) / n
    p_pos_human = (
        (cm_human["tp"] + cm_human["fp"]) / cm_human["case_count"]
        if cm_human["case_count"] > 0
        else p_pos_ai
    )
    p_neg_ai = 1 - p_pos_ai
    p_neg_human = 1 - p_pos_human
    pe = p_pos_ai * p_pos_human + p_neg_ai * p_neg_human
    if pe == 1.0:
        return 1.0
    return round((po - pe) / (1 - pe), 4)


def _wilson_ci(proportion: float, n: int, z: float = 1.96) -> dict:
    """Wilson score confidence interval."""
    if n == 0:
        return {"lower": 0.0, "upper": 0.0}
    center = (proportion + z**2 / (2 * n)) / (1 + z**2 / n)
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / n + z**2 / (4 * n**2)
        )
        / (1 + z**2 / n)
    )
    return {
        "lower": round(max(0.0, center - margin), 4),
        "upper": round(min(1.0, center + margin), 4),
    }


def _mock_cases(
    tenant_id: str, finding_category: str, rng: random.Random
) -> list:
    """Generate realistic mock validation cases with seeded randomness."""

    class MockCase:
        def __init__(
            self,
            gt: bool,
            ai_pred: bool,
            human_pred: bool,
            is_crit: bool,
        ):
            self.ground_truth = gt
            self.ai_prediction = ai_pred
            self.human_prediction = human_pred
            self.is_critical = is_crit

    cases = []
    n = 100  # 50 pos + 50 neg per category
    is_critical = finding_category in CRITICAL_FINDINGS
    # AI performance: ~92% recall on critical, ~88% on non-critical; ~90% specificity
    ai_recall = 0.92 if is_critical else rng.uniform(0.85, 0.92)
    ai_specificity = rng.uniform(0.88, 0.95)
    # Human performance: slightly lower for technicians
    human_recall = rng.uniform(0.80, 0.90)
    human_specificity = rng.uniform(0.82, 0.92)

    for i in range(n):
        gt = i < 50  # first 50 are positive
        if gt:
            ai_pred = rng.random() < ai_recall
            human_pred = rng.random() < human_recall
        else:
            ai_pred = rng.random() > ai_specificity  # FP with prob (1-specificity)
            human_pred = rng.random() > human_specificity
        cases.append(MockCase(gt, ai_pred, human_pred, is_critical))
    return cases


def compute_validation_report(
    tenant_id: str,
    run_label: str = "mock-run",
    db=None,
) -> dict:
    """Compute full validation report with per-category FP/FN analysis."""
    rng = _seed(f"val:{tenant_id}:{run_label}")
    by_category = []
    all_ai_tp = all_ai_tn = all_ai_fp = all_ai_fn = 0
    critical_fn = critical_tp = 0

    for cat in FINDING_CATEGORIES:
        data_source = "mock"
        cases: list = []

        if db is not None:
            try:
                from app.models.validation import ValidationCase  # noqa: PLC0415

                rows = (
                    db.query(ValidationCase)
                    .filter(
                        ValidationCase.tenant_id == tenant_id,
                        ValidationCase.finding_category == cat,
                    )
                    .all()
                )
                if len(rows) >= 10:
                    cases = rows
                    data_source = "real"
            except Exception:
                pass

        if not cases:
            cases = _mock_cases(tenant_id, cat, rng)

        ai_cm = _compute_confusion(cases, "ai")
        human_cm = _compute_confusion(cases, "human")
        kappa = _cohen_kappa(ai_cm, human_cm)
        ci = _wilson_ci(ai_cm["recall"], ai_cm["case_count"])
        is_critical = cat in CRITICAL_FINDINGS

        # Accumulate totals
        all_ai_tp += ai_cm["tp"]
        all_ai_tn += ai_cm["tn"]
        all_ai_fp += ai_cm["fp"]
        all_ai_fn += ai_cm["fn"]
        if is_critical:
            critical_fn += ai_cm["fn"]
            critical_tp += ai_cm["tp"]

        by_category.append(
            {
                "finding_category": cat,
                "is_critical": is_critical,
                "ai_metrics": ai_cm,
                "human_metrics": human_cm,
                "kappa": kappa,
                "confidence_interval_95": ci,
                "data_source": data_source,
            }
        )

    # Overall metrics
    total = all_ai_tp + all_ai_tn + all_ai_fp + all_ai_fn
    overall_acc = (all_ai_tp + all_ai_tn) / total if total > 0 else 0.0
    overall_prec = (
        all_ai_tp / (all_ai_tp + all_ai_fp) if (all_ai_tp + all_ai_fp) > 0 else 0.0
    )
    overall_rec = (
        all_ai_tp / (all_ai_tp + all_ai_fn) if (all_ai_tp + all_ai_fn) > 0 else 0.0
    )
    overall_f1 = (
        2 * overall_prec * overall_rec / (overall_prec + overall_rec)
        if (overall_prec + overall_rec) > 0
        else 0.0
    )
    avg_kappa = sum(c["kappa"] for c in by_category) / len(by_category)
    critical_fnr = (
        critical_fn / (critical_fn + critical_tp)
        if (critical_fn + critical_tp) > 0
        else 0.0
    )

    meets_primary = avg_kappa >= 0.80
    meets_safety = critical_fnr <= 0.02

    recommendations = []
    if not meets_primary:
        recommendations.append(
            f"Overall kappa {avg_kappa:.3f} is below the 0.80 threshold. "
            "Review finding categories with kappa < 0.75 for model improvement."
        )
    if not meets_safety:
        recommendations.append(
            f"Critical finding FN rate {critical_fnr:.1%} exceeds the 2% safety "
            "threshold. Immediate model review required before deployment."
        )
    low_recall = [
        c["finding_category"]
        for c in by_category
        if c["ai_metrics"]["recall"] < 0.85
    ]
    if low_recall:
        recommendations.append(
            f"Low recall (<85%) in categories: {', '.join(low_recall)}. "
            "Augment training data for these categories."
        )
    high_fp = [
        c["finding_category"]
        for c in by_category
        if c["ai_metrics"]["false_positive_rate"] > 0.15
    ]
    if high_fp:
        recommendations.append(
            f"High FP rate (>15%) in: {', '.join(high_fp)}. "
            "Review confidence thresholds."
        )
    if meets_primary and meets_safety:
        recommendations.append(
            "Model meets primary and safety endpoints. "
            "Proceed to clinical site validation."
        )

    return {
        "tenant_id": tenant_id,
        "run_label": run_label,
        "generated_at": _now_str(),
        "data_source": (
            "mock"
            if all(c["data_source"] == "mock" for c in by_category)
            else "mixed"
        ),
        "overall_accuracy": round(overall_acc, 4),
        "overall_precision": round(overall_prec, 4),
        "overall_recall": round(overall_rec, 4),
        "overall_f1": round(overall_f1, 4),
        "overall_kappa": round(avg_kappa, 4),
        "critical_finding_fn_rate": round(critical_fnr, 4),
        "meets_primary_endpoint": meets_primary,
        "meets_safety_endpoint": meets_safety,
        "by_category": by_category,
        "recommendations": recommendations,
    }


def list_validation_cases(
    tenant_id: str,
    finding_category: str = "",
    limit: int = 100,
    db=None,
) -> list:
    """List validation cases for a tenant from the database."""
    if db is None:
        return []
    try:
        from app.models.validation import ValidationCase  # noqa: PLC0415

        q = db.query(ValidationCase).filter(
            ValidationCase.tenant_id == tenant_id
        )
        if finding_category:
            q = q.filter(ValidationCase.finding_category == finding_category)
        return q.order_by(ValidationCase.created_at.desc()).limit(limit).all()
    except Exception:
        return []
