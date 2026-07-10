"""v4.4 — LumenAI OS: Project Catalyst — AI Copilot & Natural Language
Operations routes.

Frontend route: /copilot-workspace.
API prefix: /api/catalyst — deliberately NOT /api/copilot, which the
pre-existing P9 "Autonomous Inspection Copilot" system already owns
(`app/routes/copilot.py`). See `app/models/catalyst_copilot.py`'s module
docstring for the full naming-disambiguation note.

  * POST /chat, GET /conversations, GET /conversations/{id}/messages     — Sections 1, 2, 9
  * POST /actions/propose, POST /actions/confirm, POST /actions/cancel   — Section 3
  * GET /persona/executive-briefing, GET /persona/supervisor-coaching,
    POST /persona/supervisor-finding-explanation,
    GET /persona/technician-help                                        — Sections 4, 5, 6
  * GET /skills                                                          — Section 10
  * POST /upload                                                         — Section 8 (multi-modal)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.catalyst_copilot import DISCLAIMER, MESSAGE_ROLE_ASSISTANT, MESSAGE_ROLE_USER, MESSAGE_TYPE_DOCUMENT, MESSAGE_TYPE_IMAGE
from app.services import (
    catalyst_action_engine,
    catalyst_conversation_service,
    catalyst_persona_service,
    catalyst_query_engine,
    catalyst_skills_service,
)
from app.services.catalyst_action_engine import PendingActionExpiredError, PendingActionNotFoundError, UnknownCatalystActionError
from app.services.image_retention_service import retain_image

router = APIRouter(prefix="/api/catalyst", tags=["catalyst"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")
_ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf", "text/plain"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


def _audit(db: Session, tenant_id: str, actor: str, action_type: str, resource_type: str, resource_id: str, details: dict) -> None:
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=actor, actor_role="",
        action_type=action_type, resource_type=resource_type, resource_id=resource_id, details=details, compliance_flag=True,
    )


# ---------------------------------------------------------------------------
# Sections 1, 2, 9 — Conversational interface, NL Query Engine, memory
# ---------------------------------------------------------------------------


@router.post("/chat")
def post_chat(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="message is required")

    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    role = getattr(current_user, "role", "viewer")
    persona = payload.get("persona") or catalyst_persona_service.persona_for_role(role)

    conversation = catalyst_conversation_service.get_or_create_active_conversation(
        db, tenant_id, actor, persona=persona, conversation_id=payload.get("conversation_id"),
    )
    catalyst_conversation_service.append_message(db, conversation, role=MESSAGE_ROLE_USER, content=message)

    result = catalyst_query_engine.answer_query(db, tenant_id, message)
    suggested_action = catalyst_query_engine.detect_action_suggestion(message)

    assistant_message = catalyst_conversation_service.append_message(
        db, conversation, role=MESSAGE_ROLE_ASSISTANT, content=result["answer"], intent=result["intent"],
        skill_used=result["skill_used"], confidence=result["evidence"].get("confidence"), evidence=result["evidence"],
    )

    return {
        "conversation_id": conversation.id,
        "message_id": assistant_message.id,
        "answer": result["answer"],
        "intent": result["intent"],
        "skill_used": result["skill_used"],
        "data": result["data"],
        "evidence": result["evidence"],
        "suggested_action": suggested_action,
        "disclaimer": DISCLAIMER,
    }


@router.get("/conversations")
def get_conversations(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    return {"conversations": catalyst_conversation_service.list_conversations(db, tenant_id, actor)}


@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    return {"messages": catalyst_conversation_service.list_messages(db, tenant_id, actor, conversation_id)}


# ---------------------------------------------------------------------------
# Section 3 — Natural Language Actions
# ---------------------------------------------------------------------------


@router.post("/actions/propose")
def post_propose_action(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = catalyst_action_engine.propose_action(
            db, tenant_id, actor, conversation_id=payload.get("conversation_id", 0),
            action_type=payload.get("action_type", ""), params=payload.get("params", {}), actor=actor,
        )
    except UnknownCatalystActionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "catalyst.action_proposed", "catalyst_pending_action", str(payload.get("action_type", "")), {"requires_confirmation": result["requires_confirmation"]})
    return result


@router.post("/actions/confirm")
def post_confirm_action(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = catalyst_action_engine.confirm_action(db, tenant_id, actor, payload.get("confirm_token", ""), actor=actor)
    except PendingActionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PendingActionExpiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "catalyst.action_confirmed", "catalyst_pending_action", payload.get("confirm_token", ""), {"action_type": result["action_type"]})
    return result


@router.post("/actions/cancel")
def post_cancel_action(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = catalyst_action_engine.cancel_action(db, tenant_id, actor, payload.get("confirm_token", ""))
    except PendingActionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


# ---------------------------------------------------------------------------
# Sections 4, 5, 6 — Executive / Supervisor / Technician Copilot personas
# ---------------------------------------------------------------------------


@router.get("/persona/executive-briefing")
def get_executive_briefing(
    request: Request, cadence: str = Query("weekly"), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return catalyst_persona_service.executive_briefing(db, tenant_id, cadence=cadence)


@router.get("/persona/supervisor-coaching")
def get_supervisor_coaching(
    request: Request, technician: str = Query(...), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return catalyst_persona_service.supervisor_coaching(db, tenant_id, technician=technician)


@router.get("/actions/pending")
def get_pending_actions(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    return {"pending_actions": catalyst_action_engine.list_pending_actions(db, tenant_id, actor)}


@router.post("/persona/supervisor-finding-explanation")
def post_supervisor_finding_explanation(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return catalyst_persona_service.supervisor_finding_explanation(
        db, tenant_id, instrument_type=payload.get("instrument_type", ""),
        finding_type=payload.get("finding_type", ""), manufacturer=payload.get("manufacturer", ""),
    )


@router.get("/persona/technician-help")
def get_technician_help(
    request: Request, instrument_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return catalyst_persona_service.technician_contextual_help(db, tenant_id, instrument_type=instrument_type)


# ---------------------------------------------------------------------------
# Section 10 — AI Skills Framework catalog
# ---------------------------------------------------------------------------


@router.get("/skills")
def get_skills(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"skills": catalyst_skills_service.list_skills(db)}


# ---------------------------------------------------------------------------
# Section 8 — Multi-Modal Copilot (image/document upload)
# ---------------------------------------------------------------------------


@router.post("/upload")
def post_upload(
    request: Request,
    conversation_id: int = Form(...),
    file: UploadFile = File(...),
    consent: bool = Form(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if file.content_type not in _ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {file.content_type}")

    data = file.file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 10MB upload limit")

    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    conversation = catalyst_conversation_service.get_or_create_active_conversation(db, tenant_id, actor, conversation_id=conversation_id)

    is_image = file.content_type.startswith("image/")
    retained = retain_image(
        db, data=data, tenant_id=tenant_id, content_type=file.content_type, source="catalyst_copilot",
        uploaded_by=actor, consent=consent,
    ) if is_image else None

    message = catalyst_conversation_service.append_message(
        db, conversation, role=MESSAGE_ROLE_USER, content=f"[uploaded {file.filename}]",
        message_type=MESSAGE_TYPE_IMAGE if is_image else MESSAGE_TYPE_DOCUMENT,
    )
    _audit(db, tenant_id, actor, "catalyst.file_uploaded", "catalyst_message", str(message.id), {"filename": file.filename, "content_type": file.content_type})
    return {
        "conversation_id": conversation.id, "message_id": message.id,
        "retained_image_id": retained.id if retained is not None else None,
        "note": "Image retained for record-keeping only if org-wide retention is enabled and consent was given; text remains the primary interaction mode." if is_image else "Document accepted; text remains the primary interaction mode.",
    }
