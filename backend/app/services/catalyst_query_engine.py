"""v4.4 — Project Catalyst, Section 2: Natural Language Query Engine.

This codebase has zero real LLM/completion-API integration anywhere
(confirmed: no `openai`/`anthropic` dependency, no completion-endpoint
network call in this repository). Consistent with every other "AI"
feature here, the query engine below is a deterministic keyword/intent
classifier — never a simulated or fabricated LLM call — that dispatches
to the real skill functions in `catalyst_skills_service.py`.

Example queries this engine is built to answer (Section 2):
  * "How many instruments are awaiting supervisor review?"
  * "Give me the executive summary for this week."
  * "Which Digital Twins are showing declining health?"
  * "What's our contamination rate by anatomy zone?"
  * "Show me recurring corrosion findings."
  * "Which Kerrisons had blood findings this week?"
  * "What's the workload forecast for next week?"
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.predictive_insight import (
    FORECAST_INSPECTION_WORKLOAD,
    FORECAST_REPAIR_BACKLOG,
    HORIZON_7_DAY,
    HORIZON_30_DAY,
)
from app.services import catalyst_skills_service, pulse_kpi_service
from app.services.catalyst_explainability_service import build_evidence_envelope
from app.services.finding_trend_service import TREND_FINDING_TYPES

INTENT_SUPERVISOR_BACKLOG = "supervisor_backlog"
INTENT_EXECUTIVE_SUMMARY = "executive_summary"
INTENT_DIGITAL_TWIN_HEALTH = "digital_twin_health"
INTENT_ANATOMY_CONTAMINATION = "anatomy_contamination"
INTENT_RECURRING_FINDING_TREND = "recurring_finding_trend"
INTENT_INSTRUMENT_FINDING_SEARCH = "instrument_finding_search"
INTENT_FORECAST = "forecast"
INTENT_KNOWLEDGE_SEARCH = "knowledge_search"
INTENT_UNKNOWN = "unknown"


def _detect_finding_type(text: str) -> str:
    for ft in TREND_FINDING_TYPES:
        if ft.replace("_", " ") in text:
            return ft
    return ""


def _detect_instrument_query(text: str, finding_type: str) -> str:
    stopwords = {
        "which", "what", "show", "me", "the", "with", "had", "have", "has", "findings", "finding",
        "this", "week", "month", "are", "is", "for", "our", "get", "give", "of", "and", "in",
    }
    words = [w.strip("?,.") for w in text.split()]
    if finding_type:
        words = [w for w in words if w not in finding_type.replace("_", " ").split()]
    candidates = [w for w in words if w and w.lower() not in stopwords]
    return candidates[0] if candidates else ""


def classify_intent(query: str) -> str:
    text = (query or "").strip().lower()
    if any(k in text for k in ["supervisor review", "awaiting review", "review backlog", "supervisor backlog"]):
        return INTENT_SUPERVISOR_BACKLOG
    if any(k in text for k in ["executive summary", "executive briefing", "executive report"]):
        return INTENT_EXECUTIVE_SUMMARY
    if "digital twin" in text or "twin health" in text:
        return INTENT_DIGITAL_TWIN_HEALTH
    if "contamination" in text and ("zone" in text or "anatomy" in text):
        return INTENT_ANATOMY_CONTAMINATION
    if "recurring" in text or ("trend" in text and "forecast" not in text):
        return INTENT_RECURRING_FINDING_TREND
    if any(k in text for k in ["forecast", "predict", "projection", "workload next"]):
        return INTENT_FORECAST
    if any(k in text for k in ["knowledge", "article", "best practice"]):
        return INTENT_KNOWLEDGE_SEARCH
    if _detect_finding_type(text):
        return INTENT_INSTRUMENT_FINDING_SEARCH
    return INTENT_UNKNOWN


def answer_query(db: Session, tenant_id: str, query: str) -> dict:
    intent = classify_intent(query)

    if intent == INTENT_SUPERVISOR_BACKLOG:
        kpis = pulse_kpi_service.live_kpis(db, tenant_id)
        backlog = kpis.get("supervisor_backlog", 0)
        answer = f"{backlog} inspection(s) are currently awaiting supervisor review."
        evidence = build_evidence_envelope(
            evidence_used=[f"supervisor_backlog={backlog} (live)"], knowledge_sources=[],
            digital_twin_factors=[], workflow_rules=[], reasoning_path=["pulse_kpi_service.live_kpis"],
            confidence=1.0, references=[{"source": "pulse_kpi_service.live_kpis", "field": "supervisor_backlog"}],
        )
        return {"intent": intent, "skill_used": "reporting", "answer": answer, "data": kpis, "evidence": evidence}

    if intent == INTENT_EXECUTIVE_SUMMARY:
        result = catalyst_skills_service.reporting_skill(db, tenant_id)
        answer = "Here is the current executive summary."
        evidence = build_evidence_envelope(
            evidence_used=[result["source"]], knowledge_sources=[], digital_twin_factors=[], workflow_rules=[],
            reasoning_path=[f"catalyst_skills_service.reporting_skill via {result['source']}"], confidence=0.9,
            references=[{"source": result["source"]}],
        )
        return {"intent": intent, "skill_used": "reporting", "answer": answer, "data": result, "evidence": evidence}

    if intent == INTENT_DIGITAL_TWIN_HEALTH:
        result = catalyst_skills_service.digital_twin_skill(db, tenant_id)
        dashboard = result["dashboard"]
        declining = [rec for rec in dashboard.get("recommendations", []) if "declin" in rec.lower() or "degrad" in rec.lower()]
        answer = (
            f"{len(declining)} Digital Twin recommendation(s) flag declining health."
            if declining else "No Digital Twin recommendations currently flag declining health."
        )
        evidence = build_evidence_envelope(
            evidence_used=["digital_twin_engine.compute_twin_dashboard"], knowledge_sources=[],
            digital_twin_factors=dashboard.get("recommendations", []), workflow_rules=[],
            reasoning_path=["digital_twin_engine.compute_twin_dashboard", "scan recommendations for decline language"],
            confidence=0.7, references=[{"source": "digital_twin_engine.compute_twin_dashboard"}],
        )
        return {"intent": intent, "skill_used": "digital_twin", "answer": answer, "data": dashboard, "evidence": evidence}

    if intent == INTENT_ANATOMY_CONTAMINATION:
        result = catalyst_skills_service.analytics_skill(db, tenant_id)
        answer = "Here is the contamination-by-anatomy-zone breakdown."
        evidence = build_evidence_envelope(
            evidence_used=["anatomy_risk_service.anatomy_risk_dashboard"], knowledge_sources=[],
            digital_twin_factors=[], workflow_rules=[], reasoning_path=["anatomy_risk_service.anatomy_risk_dashboard"],
            confidence=0.85, references=[{"source": "anatomy_risk_service.anatomy_risk_dashboard"}],
        )
        return {"intent": intent, "skill_used": "analytics", "answer": answer, "data": result["anatomy_risk"], "evidence": evidence}

    if intent == INTENT_RECURRING_FINDING_TREND:
        result = catalyst_skills_service.analytics_skill(db, tenant_id)
        answer = "Here are the recurring finding-type trends."
        evidence = build_evidence_envelope(
            evidence_used=["finding_trend_service.finding_trends"], knowledge_sources=[], digital_twin_factors=[],
            workflow_rules=[], reasoning_path=["finding_trend_service.finding_trends"], confidence=0.85,
            references=[{"source": "finding_trend_service.finding_trends"}],
        )
        return {"intent": intent, "skill_used": "analytics", "answer": answer, "data": result["finding_trends"], "evidence": evidence}

    if intent == INTENT_INSTRUMENT_FINDING_SEARCH:
        text = query.lower()
        finding_type = _detect_finding_type(text)
        instrument_query = _detect_instrument_query(text, finding_type)
        result = catalyst_skills_service.inspection_skill(db, tenant_id, instrument_query=instrument_query, finding_type=finding_type)
        answer = f"Found {result['count']} inspection(s) matching instrument '{instrument_query or 'any'}' with finding type '{finding_type or 'any'}'."
        evidence = build_evidence_envelope(
            evidence_used=[f"instrument_query={instrument_query!r}", f"finding_type={finding_type!r}"],
            knowledge_sources=[], digital_twin_factors=[], workflow_rules=[],
            reasoning_path=["Inspection/InspectionFinding filtered query"], confidence=0.75,
            references=[{"source": "catalyst_skills_service.inspection_skill"}],
        )
        return {"intent": intent, "skill_used": "inspection", "answer": answer, "data": result, "evidence": evidence}

    if intent == INTENT_FORECAST:
        forecast_type = FORECAST_REPAIR_BACKLOG if "repair" in query.lower() or "backlog" in query.lower() else FORECAST_INSPECTION_WORKLOAD
        horizon = HORIZON_30_DAY if "month" in query.lower() else HORIZON_7_DAY
        result = catalyst_skills_service.forecast_skill(db, tenant_id, forecast_type=forecast_type, horizon=horizon)
        forecast = result["forecast"]
        answer = f"Forecast for {forecast_type} over {horizon}: {forecast.get('forecast_value')}."
        evidence = build_evidence_envelope(
            evidence_used=[forecast_type], knowledge_sources=[], digital_twin_factors=[], workflow_rules=[],
            reasoning_path=["insight_operational_forecast_service.forecast_operational"],
            confidence=forecast.get("confidence", 0.5), references=[{"source": "insight_operational_forecast_service.forecast_operational"}],
        )
        return {"intent": intent, "skill_used": "forecast", "answer": answer, "data": forecast, "evidence": evidence}

    if intent == INTENT_KNOWLEDGE_SEARCH:
        words = [w for w in query.lower().split() if w not in {"knowledge", "article", "best", "practice", "for", "on", "the", "about"}]
        result = catalyst_skills_service.knowledge_search_skill(db, tenant_id, query=" ".join(words))
        answer = f"Found {len(result['articles'])} knowledge article(s) and {len(result['graph'].get('results', []))} graph match(es)."
        evidence = build_evidence_envelope(
            evidence_used=[], knowledge_sources=["knowledge_repository_service.list_articles", "knowledge_graph_service.explore"],
            digital_twin_factors=[], workflow_rules=[], reasoning_path=["knowledge_search_skill"], confidence=0.7,
            references=[{"source": "knowledge_repository_service.list_articles"}],
        )
        return {"intent": intent, "skill_used": "knowledge_search", "answer": answer, "data": result, "evidence": evidence}

    evidence = build_evidence_envelope(
        evidence_used=[], knowledge_sources=[], digital_twin_factors=[], workflow_rules=[],
        reasoning_path=["no keyword pattern matched"], confidence=0.0, references=[],
    )
    return {
        "intent": INTENT_UNKNOWN, "skill_used": "", "evidence": evidence,
        "answer": "I couldn't match that to a known query type yet. Try asking about supervisor backlog, executive summary, Digital Twin health, contamination by zone, recurring findings, forecasts, or knowledge articles.",
        "data": {},
    }


# ── Section 3 front door: recognizing an action request in free text ────────
#
# Precise entity extraction (which inspection ID, which technician) from
# arbitrary text is not a capability this deterministic engine fabricates.
# Instead, a message that reads as an action request is classified to an
# `action_type` plus whatever text is safely usable as-is (e.g. the
# message itself as a notification body) — the frontend's Suggested
# Actions panel fills in any remaining structured fields before proposing.
_ACTION_KEYWORDS = [
    (["assign", "inspection"], "assign_inspection"),
    (["notify", "supervisor"], "notify_supervisor"),
    (["create", "capa"], "create_capa_draft"),
    (["schedule", "competency"], "schedule_competency_review"),
    (["publish", "workflow"], "publish_workflow"),
    (["export", "dashboard"], "export_dashboard"),
    (["generate", "report"], "generate_report"),
    (["open", "digital twin"], "open_digital_twin"),
    (["open", "knowledge article"], "open_knowledge_article"),
]


def detect_action_suggestion(query: str) -> dict | None:
    text = (query or "").strip().lower()
    for keywords, action_type in _ACTION_KEYWORDS:
        if all(k in text for k in keywords):
            if action_type in ("notify_supervisor",):
                params = {"message": query.strip()}
            elif action_type == "create_capa_draft":
                params = {"title": query.strip()[:120], "description": query.strip()}
            elif action_type == "schedule_competency_review":
                params = {"message": query.strip()}
            else:
                params = {}
            return {"action_type": action_type, "suggested_params": params}
    return None
