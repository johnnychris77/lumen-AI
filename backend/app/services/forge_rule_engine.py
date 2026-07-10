"""v4.1 — Project Forge, Sections 2 & 3: Clinical Rule Engine + No-Code
Rule Builder.

`app/automation_engine.py::_matches` is a flat AND-of-fields matcher
only — confirmed by reading every rule/escalation/validation/
prioritization engine in this codebase, none implement nested boolean
(AND/OR/NOT) conditions. This module is the first one that does, and it
is deliberately separate from `automation_engine.py` (which is left
untouched) rather than retrofitting nesting onto a matcher other call
sites already depend on behaving as flat-AND.

## Condition tree shape

A leaf condition:
    {"field": "finding", "operator": "eq", "value": "blood"}

A boolean node:
    {"op": "and" | "or", "conditions": [<condition>, ...]}
    {"op": "not", "conditions": [<condition>]}

Arbitrarily nested. `evaluate_condition` never fabricates a match for a
field missing from the evaluation context — a missing field is treated
as not satisfying any leaf condition that references it (fails closed).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.workflow_forge import CONDITION_FIELDS, LEAF_OPERATORS, RULE_OPERATORS, WorkflowRule

_MISSING = object()


class UnknownRuleError(Exception):
    pass


class InvalidConditionError(Exception):
    pass


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    result["condition"] = json.loads(result.pop("condition_json"))
    result["actions"] = json.loads(result.pop("actions_json") or "[]")
    return result


def _new_ref() -> str:
    return f"RULE-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:8].upper()}"


def validate_condition(condition: dict) -> None:
    """Recursively validates a condition tree's shape before it is ever
    persisted or evaluated."""
    if not isinstance(condition, dict):
        raise InvalidConditionError("condition must be an object")

    if "op" in condition:
        op = condition["op"]
        if op not in RULE_OPERATORS:
            raise InvalidConditionError(f"op must be one of {RULE_OPERATORS}")
        sub_conditions = condition.get("conditions")
        if not isinstance(sub_conditions, list) or not sub_conditions:
            raise InvalidConditionError(f"'{op}' requires a non-empty 'conditions' list")
        if op == "not" and len(sub_conditions) != 1:
            raise InvalidConditionError("'not' requires exactly one condition")
        for sub in sub_conditions:
            validate_condition(sub)
        return

    field = condition.get("field")
    operator = condition.get("operator")
    if field not in CONDITION_FIELDS:
        raise InvalidConditionError(f"field must be one of {CONDITION_FIELDS}")
    if operator not in LEAF_OPERATORS:
        raise InvalidConditionError(f"operator must be one of {LEAF_OPERATORS}")
    if "value" not in condition:
        raise InvalidConditionError("leaf condition requires a 'value'")


def _leaf_matches(condition: dict, context: dict) -> bool:
    field = condition["field"]
    operator = condition["operator"]
    expected = condition["value"]
    actual = context.get(field, _MISSING)
    if actual is _MISSING:
        return False

    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "gt":
        return actual is not None and actual > expected
    if operator == "gte":
        return actual is not None and actual >= expected
    if operator == "lt":
        return actual is not None and actual < expected
    if operator == "lte":
        return actual is not None and actual <= expected
    if operator == "in":
        return actual in expected
    if operator == "contains":
        return expected in (actual or "")
    return False


def evaluate_condition(condition: dict, context: dict) -> bool:
    if "op" in condition:
        op = condition["op"]
        sub_conditions = condition["conditions"]
        if op == "and":
            return all(evaluate_condition(c, context) for c in sub_conditions)
        if op == "or":
            return any(evaluate_condition(c, context) for c in sub_conditions)
        if op == "not":
            return not evaluate_condition(sub_conditions[0], context)
        raise InvalidConditionError(f"op must be one of {RULE_OPERATORS}")
    return _leaf_matches(condition, context)


def create_rule(
    db: Session, tenant_id: str, *, name: str, description: str = "", condition: dict,
    actions: list[dict], author: str,
) -> dict:
    validate_condition(condition)
    row = WorkflowRule(
        tenant_id=tenant_id, rule_ref=_new_ref(), name=name, description=description,
        condition_json=json.dumps(condition), actions_json=json.dumps(actions), version=1,
        author=author, approval_status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def _get_or_404(db: Session, rule_id: int) -> WorkflowRule:
    row = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()
    if row is None:
        raise UnknownRuleError(f"Rule {rule_id} not found.")
    return row


def approve_rule(db: Session, rule_id: int, *, approved_by: str) -> dict:
    row = _get_or_404(db, rule_id)
    row.approval_status = "approved"
    row.effective_date = row.effective_date or datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_rules(db: Session, tenant_id: str, *, approval_status: str = "", current_only: bool = True) -> list[dict]:
    q = db.query(WorkflowRule).filter((WorkflowRule.tenant_id == tenant_id) | (WorkflowRule.tenant_id == ""))
    if approval_status:
        q = q.filter(WorkflowRule.approval_status == approval_status)
    if current_only:
        q = q.filter(WorkflowRule.is_current.is_(True))
    return [_row_to_dict(r) for r in q.order_by(WorkflowRule.id.desc()).all()]


def get_rule(db: Session, rule_id: int) -> dict | None:
    row = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()
    return _row_to_dict(row) if row else None


def evaluate_rule(db: Session, rule_id: int, context: dict) -> dict:
    """Evaluates one persisted rule's condition tree against a real
    execution context, returning whether it matched and — if so — its
    ordered action list, never a fabricated confidence score."""
    row = _get_or_404(db, rule_id)
    condition = json.loads(row.condition_json)
    matched = evaluate_condition(condition, context)
    return {
        "rule_id": row.id, "rule_ref": row.rule_ref, "matched": matched,
        "actions": json.loads(row.actions_json or "[]") if matched else [],
    }


def evaluate_all_rules(db: Session, tenant_id: str, context: dict) -> list[dict]:
    """Evaluates every approved, current rule for a tenant (plus global
    rules) against one context — used by workflow execution's Conditional
    Branch / Clinical Reasoning nodes."""
    rules = list_rules(db, tenant_id, approval_status="approved", current_only=True)
    results = []
    for r in rules:
        matched = evaluate_condition(r["condition"], context)
        results.append({"rule_id": r["id"], "rule_ref": r["rule_ref"], "name": r["name"], "matched": matched, "actions": r["actions"] if matched else []})
    return results
