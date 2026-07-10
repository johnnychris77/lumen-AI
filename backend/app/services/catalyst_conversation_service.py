"""v4.4 — Project Catalyst, Section 9: Prompt & Conversation Memory.

Conversation memory is scoped by `(tenant_id, user_email)` — the same
identity pairing `app/enterprise_auth.py` already resolves per request —
so one user's conversation is never visible to another, even within the
same tenant. Retention is a real, honest cutoff
(`CONVERSATION_RETENTION_DAYS`): conversations past the window are
archived and excluded from recall, never silently "forgotten" while
still being used.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.catalyst_copilot import (
    CONVERSATION_ACTIVE,
    CONVERSATION_ARCHIVED,
    CONVERSATION_RETENTION_DAYS,
    MESSAGE_ROLE_USER,
    MESSAGE_TYPE_TEXT,
    CatalystConversation,
    CatalystMessage,
)


def apply_retention(db: Session, tenant_id: str) -> int:
    """Archives conversations whose last activity is past the retention
    window. Returns the number archived. Never deletes history outright —
    archived conversations simply drop out of `list_conversations`/recall."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=CONVERSATION_RETENTION_DAYS)
    stale = db.query(CatalystConversation).filter(
        CatalystConversation.tenant_id == tenant_id,
        CatalystConversation.status == CONVERSATION_ACTIVE,
        CatalystConversation.updated_at < cutoff,
    ).all()
    for row in stale:
        row.status = CONVERSATION_ARCHIVED
    db.commit()
    return len(stale)


def get_or_create_active_conversation(db: Session, tenant_id: str, user_email: str, *, persona: str = "technician", conversation_id: int | None = None) -> CatalystConversation:
    apply_retention(db, tenant_id)
    if conversation_id is not None:
        row = db.query(CatalystConversation).filter(
            CatalystConversation.id == conversation_id, CatalystConversation.tenant_id == tenant_id,
            CatalystConversation.user_email == user_email,
        ).first()
        if row is not None:
            return row
    row = CatalystConversation(tenant_id=tenant_id, user_email=user_email, persona=persona)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_conversations(db: Session, tenant_id: str, user_email: str) -> list[dict]:
    rows = db.query(CatalystConversation).filter(
        CatalystConversation.tenant_id == tenant_id, CatalystConversation.user_email == user_email,
        CatalystConversation.status == CONVERSATION_ACTIVE,
    ).order_by(CatalystConversation.updated_at.desc()).all()
    return [
        {"id": r.id, "title": r.title, "persona": r.persona, "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()}
        for r in rows
    ]


def append_message(
    db: Session, conversation: CatalystConversation, *, role: str, content: str,
    message_type: str = MESSAGE_TYPE_TEXT, intent: str = "", skill_used: str = "",
    confidence: float | None = None, evidence: dict | None = None,
) -> CatalystMessage:
    message = CatalystMessage(
        conversation_id=conversation.id, tenant_id=conversation.tenant_id, role=role, message_type=message_type,
        content=content, intent=intent, skill_used=skill_used, confidence=confidence,
        evidence_json=json.dumps(evidence or {}),
    )
    db.add(message)
    if role == MESSAGE_ROLE_USER and conversation.title == "New conversation":
        conversation.title = content[:80]
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


def list_messages(db: Session, tenant_id: str, user_email: str, conversation_id: int) -> list[dict]:
    conversation = db.query(CatalystConversation).filter(
        CatalystConversation.id == conversation_id, CatalystConversation.tenant_id == tenant_id,
        CatalystConversation.user_email == user_email,
    ).first()
    if conversation is None:
        return []
    rows = db.query(CatalystMessage).filter(
        CatalystMessage.conversation_id == conversation_id, CatalystMessage.tenant_id == tenant_id,
    ).order_by(CatalystMessage.id.asc()).all()
    return [
        {
            "id": m.id, "role": m.role, "message_type": m.message_type, "content": m.content,
            "intent": m.intent, "skill_used": m.skill_used, "confidence": m.confidence,
            "evidence": json.loads(m.evidence_json), "created_at": m.created_at.isoformat(),
        }
        for m in rows
    ]


def recent_context(db: Session, conversation_id: int, tenant_id: str, *, turns: int = 6) -> list[dict]:
    """Follow-up understanding support: the last N turns of this
    conversation only — never another user's or another tenant's."""
    rows = db.query(CatalystMessage).filter(
        CatalystMessage.conversation_id == conversation_id, CatalystMessage.tenant_id == tenant_id,
    ).order_by(CatalystMessage.id.desc()).limit(turns).all()
    return [{"role": m.role, "content": m.content, "intent": m.intent} for m in reversed(rows)]
