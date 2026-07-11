"""v4.8 — Project Athena, Section 9: Athena Assistant.

Extends the existing `ai_knowledge_assistant_service.answer_question()`
(v1.8) rather than building a second assistant — every answer is still
deterministic and source-cited, never a call to an external LLM (this
codebase has zero real LLM integration anywhere, confirmed by research).
Adds three new query shapes named in the brief: recurring-issue
investigation history, cross-time policy/guidance comparison, and
workflow-version comparison — each dispatches to a real, already-built
Athena service rather than fabricating a new answer path.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.athena_knowledge import DISCLAIMER
from app.services import ai_knowledge_assistant_service, forge_workflow_service
from app.services.athena_memory_timeline_service import build_memory_timeline
from app.services.athena_search_service import organizational_search
from app.services.clinical_mentor import FINDING_EDUCATION
from app.services.knowledge_search_service import _matched_findings

_RECURRING_KEYWORDS = ("recurring", "how we handled", "how did we handle")
_LESSONS_KEYWORDS = ("lessons learned", "lesson learned")
_POLICY_CHANGE_KEYWORDS = ("changed", "change", "ifu guidance", "over the past year", "over the last year")
_WORKFLOW_COMPARE_KEYWORDS = ("compare", "last year's", "previous version")


def _classify(q: str) -> str:
    if any(k in q for k in _RECURRING_KEYWORDS):
        return "recurring_investigation"
    if any(k in q for k in _LESSONS_KEYWORDS):
        return "lessons_learned_search"
    if any(k in q for k in _WORKFLOW_COMPARE_KEYWORDS):
        return "workflow_comparison"
    if any(k in q for k in _POLICY_CHANGE_KEYWORDS):
        return "policy_change_history"
    return "general"


def ask_athena(db: Session, tenant_id: str, question: str, *, instrument_type: str = "", workflow_id: int | None = None, actor: str = "") -> dict:
    q = (question or "").strip().lower()
    intent = _classify(q)
    base = ai_knowledge_assistant_service.answer_question(db, tenant_id, question, instrument_type=instrument_type, actor=actor)

    result: dict = {"question": question, "intent": intent, "base_answer": base}

    if intent == "recurring_investigation":
        findings = _matched_findings(q) or list(FINDING_EDUCATION.keys())
        finding_type = findings[0] if findings else ""
        if finding_type:
            result["timeline"] = build_memory_timeline(db, tenant_id, finding_type=finding_type, instrument_type=instrument_type)

    elif intent == "lessons_learned_search":
        search_results = organizational_search(db, tenant_id, question, actor=actor)
        lessons = [a for a in search_results["knowledge_articles"] if a.get("category") == "lesson_learned"]
        result["lessons_learned"] = lessons

    elif intent == "policy_change_history":
        from app.services.apollo_policy_service import list_policies

        result["policy_history"] = list_policies(db, tenant_id)

    elif intent == "workflow_comparison":
        if workflow_id is not None:
            result["version_history"] = forge_workflow_service.version_history(db, workflow_id)
        else:
            result["note"] = "Provide workflow_id to compare a specific playbook's version history."

    result["human_review_required"] = True
    result["disclaimer"] = DISCLAIMER
    return result
