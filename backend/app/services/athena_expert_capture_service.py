"""v4.8 — Project Athena, Section 2: Expert Knowledge Capture.

Wraps the existing `knowledge_repository_service.create_article` (v1.8) —
every submission still enters as `draft` and follows the pre-existing
`knowledge_governance_service` approval workflow unchanged. The only new
capability is attaching photo/video/voice examples via
`KnowledgeMediaAttachment`, since no media field existed on
`KnowledgeArticle` before Athena.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.athena_knowledge import ATTACH_TO_ARTICLE, MEDIA_TYPES, KnowledgeMediaAttachment
from app.services.knowledge_repository_service import article_to_dict, create_article


class InvalidMediaTypeError(ValueError):
    pass


def submit_expert_contribution(
    db: Session, tenant_id: str, *, category: str, title: str, body: str, author: str,
    applicable_instruments: list[str] | None = None, applicable_findings: list[str] | None = None,
    anatomy_zone: str = "", specialty: str = "",
) -> dict:
    """A best practice / inspection tip / cleaning technique / anatomy
    insight / failure mode submission — enters the same draft ->
    pending_review -> approved governance workflow every KnowledgeArticle
    already follows."""
    article = create_article(
        db, tenant_id=tenant_id, category=category, title=title, body=body, author=author,
        applicable_instruments=applicable_instruments, applicable_findings=applicable_findings,
        anatomy_zone=anatomy_zone, specialty=specialty,
    )
    db.commit()
    db.refresh(article)
    return article_to_dict(article)


def attach_media(
    db: Session, tenant_id: str, article_id: int, *, media_type: str, url_or_ref: str,
    caption: str = "", transcript: str = "", uploaded_by: str = "",
) -> dict:
    if media_type not in MEDIA_TYPES:
        raise InvalidMediaTypeError(f"media_type must be one of {MEDIA_TYPES}")
    attachment = KnowledgeMediaAttachment(
        tenant_id=tenant_id, source_type=ATTACH_TO_ARTICLE, source_id=article_id, media_type=media_type,
        url_or_ref=url_or_ref, caption=caption, transcript=transcript, uploaded_by=uploaded_by,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return {
        "id": attachment.id, "source_type": attachment.source_type, "source_id": attachment.source_id,
        "media_type": attachment.media_type, "url_or_ref": attachment.url_or_ref, "caption": attachment.caption,
    }


def list_media(db: Session, tenant_id: str, *, source_type: str, source_id: int) -> list[dict]:
    rows = (
        db.query(KnowledgeMediaAttachment)
        .filter(
            KnowledgeMediaAttachment.tenant_id == tenant_id, KnowledgeMediaAttachment.source_type == source_type,
            KnowledgeMediaAttachment.source_id == source_id,
        )
        .all()
    )
    return [
        {
            "id": r.id, "media_type": r.media_type, "url_or_ref": r.url_or_ref, "caption": r.caption,
            "transcript": r.transcript, "uploaded_by": r.uploaded_by, "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
