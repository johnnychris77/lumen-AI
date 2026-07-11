"""v4.8 — Project Athena, Section 10: Knowledge Preservation.

No exit-interview, video/voice capture, or workflow-recording system
existed anywhere in this codebase before Athena — genuinely new.
`transcript_text` is always human-entered or human-reviewed; this module
never claims to perform real speech-to-text transcription, matching this
codebase's "never fabricate a capability" convention. Promoting a session
into a structured `KnowledgeArticle` reuses `knowledge_repository_service.
create_article` directly rather than a second article-creation path.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.athena_knowledge import (
    ATTACH_TO_PRESERVATION_SESSION,
    DISCLAIMER,
    MEDIA_TYPES,
    SESSION_STRUCTURED,
    SESSION_TRANSCRIBED,
    KnowledgeMediaAttachment,
    KnowledgePreservationSession,
)
from app.services.knowledge_repository_service import article_to_dict, create_article


class PreservationSessionNotFoundError(ValueError):
    pass


class InvalidMediaTypeError(ValueError):
    pass


def _to_dict(row: KnowledgePreservationSession) -> dict:
    return {
        "id": row.id, "created_at": row.created_at.isoformat(), "subject_name": row.subject_name,
        "subject_role": row.subject_role, "session_type": row.session_type, "status": row.status,
        "summary": row.summary, "transcript_text": row.transcript_text,
        "topics": json.loads(row.topics_json or "[]"), "converted_article_id": row.converted_article_id,
        "captured_by": row.captured_by, "human_review_required": True, "disclaimer": DISCLAIMER,
    }


def create_preservation_session(
    db: Session, tenant_id: str, *, subject_name: str, session_type: str, subject_role: str = "",
    summary: str = "", captured_by: str = "",
) -> dict:
    row = KnowledgePreservationSession(
        tenant_id=tenant_id, subject_name=subject_name, subject_role=subject_role, session_type=session_type,
        summary=summary, captured_by=captured_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get(db: Session, tenant_id: str, session_id: int) -> KnowledgePreservationSession:
    row = (
        db.query(KnowledgePreservationSession)
        .filter(KnowledgePreservationSession.id == session_id, KnowledgePreservationSession.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise PreservationSessionNotFoundError(f"Preservation session {session_id} not found for tenant {tenant_id}.")
    return row


def attach_media(
    db: Session, tenant_id: str, session_id: int, *, media_type: str, url_or_ref: str,
    caption: str = "", uploaded_by: str = "",
) -> dict:
    if media_type not in MEDIA_TYPES:
        raise InvalidMediaTypeError(f"media_type must be one of {MEDIA_TYPES}")
    _get(db, tenant_id, session_id)  # existence check
    attachment = KnowledgeMediaAttachment(
        tenant_id=tenant_id, source_type=ATTACH_TO_PRESERVATION_SESSION, source_id=session_id,
        media_type=media_type, url_or_ref=url_or_ref, caption=caption, uploaded_by=uploaded_by,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return {"id": attachment.id, "media_type": attachment.media_type, "url_or_ref": attachment.url_or_ref}


def add_transcript(db: Session, tenant_id: str, session_id: int, *, transcript_text: str, topics: list[str] | None = None) -> dict:
    """Records a human-provided (or human-reviewed) transcript — never a
    fabricated speech-to-text output."""
    row = _get(db, tenant_id, session_id)
    row.transcript_text = transcript_text
    row.topics_json = json.dumps(topics or [])
    row.status = SESSION_TRANSCRIBED
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def convert_to_knowledge_article(
    db: Session, tenant_id: str, session_id: int, *, category: str, title: str, author: str,
) -> dict:
    """Promotes tacit knowledge into a structured, governed
    `KnowledgeArticle` — enters the same draft approval workflow as any
    other article (Section 2)."""
    row = _get(db, tenant_id, session_id)
    body = row.transcript_text or row.summary
    if not body:
        raise ValueError("Session has no transcript or summary to convert into an article.")
    article = create_article(db, tenant_id=tenant_id, category=category, title=title, body=body, author=author)
    db.commit()
    db.refresh(article)
    row.converted_article_id = article.id
    row.status = SESSION_STRUCTURED
    db.commit()
    db.refresh(row)
    return {"session": _to_dict(row), "article": article_to_dict(article)}


def list_sessions(db: Session, tenant_id: str, *, status: str = "") -> list[dict]:
    q = db.query(KnowledgePreservationSession).filter(KnowledgePreservationSession.tenant_id == tenant_id)
    if status:
        q = q.filter(KnowledgePreservationSession.status == status)
    return [_to_dict(r) for r in q.order_by(KnowledgePreservationSession.created_at.desc()).all()]


def get_session(db: Session, tenant_id: str, session_id: int) -> dict:
    return _to_dict(_get(db, tenant_id, session_id))
