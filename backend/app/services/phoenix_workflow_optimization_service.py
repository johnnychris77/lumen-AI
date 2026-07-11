"""v4.9 — Project Phoenix, Section 4: Workflow Optimization Engine.

`WorkflowExecution` (`workflow_forge.py`, v4.1) already records real
`execution_time_ms`/`decision_path_json`/`status`, but no duration/
bottleneck/queue-delay/rule-complexity analytics existed anywhere over
it before Phoenix — a genuine gap this module fills by reading those rows
directly. Any optimization surfaced here is a *recommendation* — nothing
calls `forge_workflow_service.revise_workflow` automatically.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.phoenix_intelligence import DISCLAIMER
from app.models.workflow_forge import (
    APPROVAL_PENDING,
    EXECUTION_FAILED,
    WorkflowApprovalInstance,
    WorkflowExecution,
    WorkflowRule,
)

_BOTTLENECK_THRESHOLD_HOURS = 24.0


def duration_analysis(db: Session, tenant_id: str, *, workflow_id: int | None = None) -> dict:
    q = db.query(WorkflowExecution).filter(
        WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.execution_time_ms.isnot(None),
    )
    if workflow_id is not None:
        q = q.filter(WorkflowExecution.workflow_id == workflow_id)
    rows = q.all()
    if not rows:
        return {"sample_size": 0, "note": "insufficient data — no completed executions with recorded duration yet"}
    durations = sorted(r.execution_time_ms for r in rows)
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        "sample_size": len(durations), "avg_execution_time_ms": round(sum(durations) / len(durations), 1),
        "min_execution_time_ms": round(durations[0], 1), "max_execution_time_ms": round(durations[-1], 1),
        "by_status": by_status,
    }


def approval_bottlenecks(db: Session, tenant_id: str, *, stale_hours: float = _BOTTLENECK_THRESHOLD_HOURS) -> list[dict]:
    """Approval instances still pending after `stale_hours` — a real
    queue-delay signal, not a fabricated SLA breach."""
    now = datetime.now(timezone.utc)
    rows = (
        db.query(WorkflowApprovalInstance)
        .filter(WorkflowApprovalInstance.tenant_id == tenant_id, WorkflowApprovalInstance.status == APPROVAL_PENDING)
        .all()
    )
    bottlenecks = []
    for r in rows:
        age_hours = (now - r.created_at).total_seconds() / 3600
        if age_hours >= stale_hours:
            bottlenecks.append({
                "instance_id": r.id, "chain_id": r.chain_id, "current_step_index": r.current_step_index,
                "age_hours": round(age_hours, 1),
            })
    bottlenecks.sort(key=lambda b: b["age_hours"], reverse=True)
    return bottlenecks


def repeated_exceptions(db: Session, tenant_id: str, *, min_failures: int = 2) -> list[dict]:
    """Workflows with repeated failed executions — a real recurrence
    count, grouped by `workflow_id`."""
    rows = (
        db.query(WorkflowExecution)
        .filter(WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.status == EXECUTION_FAILED)
        .all()
    )
    counts: dict[int, int] = {}
    for r in rows:
        counts[r.workflow_id] = counts.get(r.workflow_id, 0) + 1
    return [
        {"workflow_id": wf_id, "failure_count": count}
        for wf_id, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        if count >= min_failures
    ]


def _condition_complexity(condition: dict) -> int:
    """Recursive node count of a nested AND/OR/NOT condition tree — a
    real structural complexity measure, not a guessed difficulty score."""
    if not isinstance(condition, dict):
        return 0
    if "conditions" in condition:
        return 1 + sum(_condition_complexity(c) for c in condition.get("conditions", []))
    return 1  # a leaf condition


def rule_complexity(db: Session, tenant_id: str) -> list[dict]:
    rows = db.query(WorkflowRule).filter(
        (WorkflowRule.tenant_id == tenant_id) | (WorkflowRule.tenant_id == ""), WorkflowRule.is_current.is_(True),
    ).all()
    results = []
    for r in rows:
        try:
            condition = json.loads(r.condition_json or "{}")
        except (TypeError, ValueError):
            condition = {}
        results.append({"rule_id": r.id, "name": r.name, "complexity_score": _condition_complexity(condition)})
    results.sort(key=lambda x: x["complexity_score"], reverse=True)
    return results


def recommend_workflow_optimization(db: Session, tenant_id: str, workflow_id: int) -> dict:
    """Analyzes one workflow's real duration/failure/bottleneck signals
    and returns an evidence-based optimization recommendation shape —
    never calls `forge_workflow_service.revise_workflow` itself."""
    duration = duration_analysis(db, tenant_id, workflow_id=workflow_id)
    failures = [f for f in repeated_exceptions(db, tenant_id) if f["workflow_id"] == workflow_id]

    evidence = []
    if duration.get("sample_size"):
        evidence.append(f"Average execution time: {duration['avg_execution_time_ms']} ms over {duration['sample_size']} runs.")
    if failures:
        evidence.append(f"{failures[0]['failure_count']} repeated failed executions recorded.")

    return {
        "workflow_id": workflow_id, "duration_analysis": duration, "repeated_failures": failures,
        "evidence": evidence, "recommend_review": bool(failures) or duration.get("max_execution_time_ms", 0) > 0,
        "human_review_required": True, "disclaimer": DISCLAIMER,
    }


def workflow_optimization_summary(db: Session, tenant_id: str) -> dict:
    return {
        "duration_analysis": duration_analysis(db, tenant_id),
        "approval_bottlenecks": approval_bottlenecks(db, tenant_id),
        "repeated_exceptions": repeated_exceptions(db, tenant_id),
        "rule_complexity": rule_complexity(db, tenant_id),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
