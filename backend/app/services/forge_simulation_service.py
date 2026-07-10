"""v4.1 — Project Forge, Section 8: Simulation Mode.

Replays a workflow against a real, already-recorded `Inspection` (and its
`InspectionFinding`s) rather than synthetic data — "Replay inspections /
AI reasoning / approvals / routing" means running the exact same
execution engine (`forge_execution_service.execute_workflow`) that a
live trigger would use, with `is_simulation=True` so simulated executions
are clearly distinguishable from real ones in `/workflow-history` and
never mistaken for an actual automated action having been taken (e.g. a
simulated "Create CAPA" action still calls the real `capa_service`,
since simulating a decision path without also exercising its actions
would defeat the purpose of testing a workflow before publishing it —
this is why simulations should generally be run against non-production
tenants or already-resolved historical inspections).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import forge_execution_service


def simulate_workflow(
    db: Session, tenant_id: str, workflow_id: int, inspection_id: int, *, triggered_by: str = "simulation",
    expected_outcome: str = "",
) -> dict:
    """Runs one simulation and reports expected vs. actual outcome,
    decision path, and execution time — all drawn from the real
    execution record `forge_execution_service` produces."""
    execution = forge_execution_service.execute_workflow(
        db, tenant_id, workflow_id, inspection_id=inspection_id, triggered_by=triggered_by, is_simulation=True,
    )

    from app.models.workflow_forge import WorkflowExecution
    row = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution["id"]).first()
    if row is not None and expected_outcome:
        row.expected_outcome = expected_outcome
        db.commit()
        db.refresh(row)
        execution["expected_outcome"] = expected_outcome

    return {
        "execution_id": execution["id"],
        "expected_outcome": execution.get("expected_outcome", ""),
        "actual_outcome": execution["actual_outcome"],
        "outcome_matched": (execution.get("expected_outcome", "") == execution["actual_outcome"]) if execution.get("expected_outcome") else None,
        "decision_path": execution["decision_path"],
        "execution_log": execution["execution_log"],
        "execution_time_ms": execution["execution_time_ms"],
        "status": execution["status"],
    }
