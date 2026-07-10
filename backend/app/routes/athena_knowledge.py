"""v4.8 — LumenAI OS: Project Athena — Healthcare Knowledge Intelligence &
Institutional Memory routes.

Frontend route: /knowledge-memory.
API prefix: /api/athena — deliberately NOT `/api/knowledge` (v1.8) or
`/api/knowledge-graph` (both taken); see `app/models/athena_knowledge.py`
for the full naming-disambiguation note.

## Tenant authorization — a deliberate departure from prior sprints

Every route in this file uses `tenant_authz.require_tenant_roles`, which
verifies a real `TenantMembership` row for the authenticated user's
token-derived email before granting access — not the `_tenant()`/
`require_roles()` pattern used by every prior sprint's routes (Catalyst
through Apollo), which resolves the acting tenant from a client-supplied
header with no membership check. That pattern is a real cross-tenant
authorization gap; this file does not propagate it into an 18th module.
The other 16 modules still need the same retrofit — tracked separately,
not fixed here.

  * GET   /memory/entries, GET /memory/search, GET /memory/summary     — Section 1
  * POST  /expert-contributions,
    POST/GET /expert-contributions/{id}/media                          — Section 2
  * POST  /experience-graph/chains, GET /experience-graph/person/{p},
    GET   /experience-graph/nodes/{id}/chain, GET /experience-graph/schema — Section 3
  * GET   /timeline                                                     — Section 4
  * POST  /playbooks, GET /playbooks, GET /playbooks/{id},
    POST  /playbooks/{id}/standards, GET /playbooks/{id}/history         — Section 5
  * GET   /curator/summary                                              — Section 6
  * GET   /search                                                       — Section 7
  * GET   /trust/articles, GET /trust/articles/{id}                     — Section 8
  * POST  /assistant/ask                                                 — Section 9
  * POST  /preservation/sessions, POST .../media, POST .../transcript,
    POST  .../convert, GET /preservation/sessions, GET .../{id}          — Section 10
  * GET   /governance/summary                                           — Governance
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.services import (
    athena_assistant_service,
    athena_curator_service,
    athena_expert_capture_service,
    athena_experience_graph_service,
    athena_memory_service,
    athena_memory_timeline_service,
    athena_playbook_service,
    athena_preservation_service,
    athena_search_service,
    athena_trust_service,
    knowledge_governance_service,
)
from app.services.knowledge_repository_service import get_article
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/athena", tags=["athena"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


def _audit(db: Session, tenant_id: str, actor: str, action_type: str, resource_type: str, resource_id: str, details: dict) -> None:
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=actor, actor_role="",
        action_type=action_type, resource_type=resource_type, resource_id=resource_id, details=details, compliance_flag=True,
    )


# ---------------------------------------------------------------------------
# Section 1 — Institutional Memory Engine
# ---------------------------------------------------------------------------


@router.get("/memory/entries")
def get_memory_entries(source_types: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    wanted = [s.strip() for s in source_types.split(",") if s.strip()] or None
    return {"entries": athena_memory_service.list_memory_entries(db, tenant_id, source_types=wanted)}


@router.get("/memory/search")
def get_memory_search(q: str = Query(...), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return athena_memory_service.search_memory(db, tenant_id, q)


@router.get("/memory/summary")
def get_memory_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return athena_memory_service.memory_summary(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 2 — Expert Knowledge Capture
# ---------------------------------------------------------------------------


@router.post("/expert-contributions", status_code=201)
def post_expert_contribution(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    result = athena_expert_capture_service.submit_expert_contribution(
        db, tenant_id, category=payload.get("category", ""), title=payload.get("title", ""),
        body=payload.get("body", ""), author=payload.get("author", actor),
        applicable_instruments=payload.get("applicable_instruments"), applicable_findings=payload.get("applicable_findings"),
        anatomy_zone=payload.get("anatomy_zone", ""), specialty=payload.get("specialty", ""),
    )
    _audit(db, tenant_id, actor, "athena.expert_contribution_submitted", "knowledge_articles", str(result["id"]), {"category": result["category"]})
    return result


@router.post("/expert-contributions/{article_id}/media", status_code=201)
def post_expert_contribution_media(
    article_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = athena_expert_capture_service.attach_media(
            db, tenant_id, article_id, media_type=payload.get("media_type", ""), url_or_ref=payload.get("url_or_ref", ""),
            caption=payload.get("caption", ""), transcript=payload.get("transcript", ""), uploaded_by=payload.get("uploaded_by", actor),
        )
    except athena_expert_capture_service.InvalidMediaTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "athena.media_attached", "knowledge_articles", str(article_id), {"media_type": result["media_type"]})
    return result


@router.get("/expert-contributions/{article_id}/media")
def get_expert_contribution_media(article_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    from app.models.athena_knowledge import ATTACH_TO_ARTICLE

    return {"media": athena_expert_capture_service.list_media(db, tenant_id, source_type=ATTACH_TO_ARTICLE, source_id=article_id)}


# ---------------------------------------------------------------------------
# Section 3 — Experience Graph
# ---------------------------------------------------------------------------


@router.post("/experience-graph/chains", status_code=201)
def post_experience_chain(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    result = athena_experience_graph_service.build_experience_chain(
        db, tenant_id, person=payload.get("person", ""), experience_label=payload.get("experience_label", ""),
        instrument_type=payload.get("instrument_type", ""), finding_type=payload.get("finding_type", ""),
        manufacturer=payload.get("manufacturer", ""), model=payload.get("model", ""),
        outcome_label=payload.get("outcome_label", ""), evidence_label=payload.get("evidence_label", ""),
        organization_label=payload.get("organization_label", ""),
    )
    _audit(db, tenant_id, actor, "athena.experience_chain_recorded", "athena_experience_graph_nodes", str(result["experience_node"]["id"]), {"person": payload.get("person", "")})
    return result


@router.get("/experience-graph/person/{person}")
def get_graph_for_person(person: str, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return athena_experience_graph_service.graph_for_person(db, tenant_id, person)


@router.get("/experience-graph/nodes/{node_id}/chain")
def get_full_chain(node_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return athena_experience_graph_service.full_chain(db, tenant_id, node_id)


@router.get("/experience-graph/schema")
def get_graph_schema(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES))):
    return athena_experience_graph_service.graph_schema()


# ---------------------------------------------------------------------------
# Section 4 — Institutional Memory Timeline
# ---------------------------------------------------------------------------


@router.get("/timeline")
def get_memory_timeline(
    finding_type: str = Query(...), instrument_type: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    tenant_id = _tenant(current_user)
    return athena_memory_timeline_service.build_memory_timeline(db, tenant_id, finding_type=finding_type, instrument_type=instrument_type)


# ---------------------------------------------------------------------------
# Section 5 — Clinical Playbooks
# ---------------------------------------------------------------------------


@router.post("/playbooks", status_code=201)
def post_playbook(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = athena_playbook_service.create_playbook(
            db, tenant_id, name=payload.get("name", ""), category=payload.get("category", ""),
            description=payload.get("description", ""), nodes=payload.get("nodes", []), edges=payload.get("edges", []),
            author=payload.get("author", actor), linked_standards=payload.get("linked_standards"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "athena.playbook_created", "forge_workflow_definitions", str(result["id"]), {"category": result["category"]})
    return result


@router.get("/playbooks")
def get_playbooks(category: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return {"playbooks": athena_playbook_service.list_playbooks(db, tenant_id, category=category)}


@router.get("/playbooks/{workflow_id}")
def get_playbook(workflow_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return athena_playbook_service.get_playbook(db, workflow_id)
    except athena_playbook_service.PlaybookNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/playbooks/{workflow_id}/standards")
def post_playbook_standard(workflow_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    result = athena_playbook_service.attach_standard(db, workflow_id, payload.get("standard_code", ""))
    _audit(db, tenant_id, actor, "athena.playbook_standard_attached", "forge_workflow_definitions", str(workflow_id), {"standard_code": payload.get("standard_code", "")})
    return result


@router.get("/playbooks/{workflow_id}/history")
def get_playbook_history(workflow_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"history": athena_playbook_service.playbook_version_history(db, workflow_id)}


# ---------------------------------------------------------------------------
# Section 6 — AI Knowledge Curator
# ---------------------------------------------------------------------------


@router.get("/curator/summary")
def get_curator_summary(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return athena_curator_service.curator_summary(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 7 — Organizational Search
# ---------------------------------------------------------------------------


@router.get("/search")
def get_organizational_search(q: str = Query(...), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    return athena_search_service.organizational_search(db, tenant_id, q, actor=actor)


# ---------------------------------------------------------------------------
# Section 8 — Knowledge Trust Score
# ---------------------------------------------------------------------------


@router.get("/trust/articles")
def get_trust_articles(min_trust: float = Query(None), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return {"articles": athena_trust_service.list_articles_with_trust(db, tenant_id, min_trust=min_trust)}


@router.get("/trust/articles/{article_id}")
def get_trust_article(article_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    article = get_article(db, tenant_id, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail=f"Article {article_id} not found.")
    return athena_trust_service.compute_trust_score(db, article)


# ---------------------------------------------------------------------------
# Section 9 — Athena Assistant
# ---------------------------------------------------------------------------


@router.post("/assistant/ask")
def post_ask_athena(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    return athena_assistant_service.ask_athena(
        db, tenant_id, payload.get("question", ""), instrument_type=payload.get("instrument_type", ""),
        workflow_id=payload.get("workflow_id"), actor=actor,
    )


# ---------------------------------------------------------------------------
# Section 10 — Knowledge Preservation
# ---------------------------------------------------------------------------


@router.post("/preservation/sessions", status_code=201)
def post_preservation_session(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    result = athena_preservation_service.create_preservation_session(
        db, tenant_id, subject_name=payload.get("subject_name", ""), session_type=payload.get("session_type", ""),
        subject_role=payload.get("subject_role", ""), summary=payload.get("summary", ""),
        captured_by=payload.get("captured_by", actor),
    )
    _audit(db, tenant_id, actor, "athena.preservation_session_created", "athena_knowledge_preservation_sessions", str(result["id"]), {"session_type": result["session_type"]})
    return result


@router.post("/preservation/sessions/{session_id}/media", status_code=201)
def post_preservation_media(session_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = athena_preservation_service.attach_media(
            db, tenant_id, session_id, media_type=payload.get("media_type", ""), url_or_ref=payload.get("url_or_ref", ""),
            caption=payload.get("caption", ""), uploaded_by=payload.get("uploaded_by", actor),
        )
    except athena_preservation_service.PreservationSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except athena_preservation_service.InvalidMediaTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.post("/preservation/sessions/{session_id}/transcript")
def post_preservation_transcript(session_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    try:
        return athena_preservation_service.add_transcript(
            db, tenant_id, session_id, transcript_text=payload.get("transcript_text", ""), topics=payload.get("topics"),
        )
    except athena_preservation_service.PreservationSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/preservation/sessions/{session_id}/convert")
def post_preservation_convert(session_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = athena_preservation_service.convert_to_knowledge_article(
            db, tenant_id, session_id, category=payload.get("category", ""), title=payload.get("title", ""),
            author=payload.get("author", actor),
        )
    except athena_preservation_service.PreservationSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "athena.preservation_session_converted", "knowledge_articles", str(result["article"]["id"]), {"session_id": session_id})
    return result


@router.get("/preservation/sessions")
def get_preservation_sessions(status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return {"sessions": athena_preservation_service.list_sessions(db, tenant_id, status=status)}


@router.get("/preservation/sessions/{session_id}")
def get_preservation_session(session_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return athena_preservation_service.get_session(db, _tenant(current_user), session_id)
    except athena_preservation_service.PreservationSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------


@router.get("/governance/summary")
def get_governance_summary(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return knowledge_governance_service.governance_summary(db, tenant_id)
